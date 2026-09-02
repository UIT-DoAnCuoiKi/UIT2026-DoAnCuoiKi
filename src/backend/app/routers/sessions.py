from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import now_utc
from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import ImageAsset, ParkingLot, ParkingSession, Payment, PlateReading, User, Zone
from app.schemas.session import (
    EntryRequest, ExitRequest, ExitResult, LostTicketRequest, ManualRequest, PaymentBrief, ReadingBrief, ResolveRequest,
    SessionBrief, SessionDetail, SessionListItem, SessionListResponse, SessionOut,
)
from app.security import crypto
from app.security.plate import normalize_plate, plate_hash
from app.services.fee import compute_fee, get_active_rule
from app.services.audit import write_audit
from app.services.matching import Candidate, find_match
from app.services.occupancy import lot_is_full
from app.services.registry import is_blacklisted, is_exempt
from app.services.sync import enqueue_session
from app.services.vehicle_groups import group_for

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _session_out(s: ParkingSession, warning: str | None = None) -> SessionOut:
    text = crypto.decrypt_text(s.plate_ciphertext) if s.plate_ciphertext else None
    return SessionOut(
        id=s.id,
        status=s.status,
        vehicle_group=s.vehicle_group or None,
        color=s.color,
        plate_text=text,
        entry_time=s.entry_time,
        exit_time=s.exit_time,
        fee_amount=s.fee_amount,
        match_flag=s.match_flag,
        warning=warning,
    )


@router.post("/entry", response_model=SessionOut)
def confirm_entry(body: EntryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    reading = db.get(PlateReading, body.reading_id)
    if reading is None or reading.direction != "in":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading vào hợp lệ")

    lot_id = None
    if body.zone_id is not None:
        zone = db.get(Zone, body.zone_id)
        if zone is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy khu")
        lot_id = zone.lot_id
        if lot_is_full(db, lot_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "bãi đã đầy")

    group = body.vehicle_group or group_for(reading.vehicle_type) or "unknown"
    has_plate = bool(reading.plate_hash)
    warnings: list[str] = []
    if has_plate:
        dup = db.scalars(
            select(ParkingSession).where(
                ParkingSession.plate_hash == reading.plate_hash,
                ParkingSession.status == "in_lot",
            )
        ).first()
        if dup is not None:
            if not body.override_duplicate:
                raise HTTPException(status.HTTP_409_CONFLICT, "biển đang trong bãi (xác nhận để ghi đè)")
            warnings.append("biển trùng một xe đang trong bãi")
        if is_blacklisted(db, reading.plate_hash):
            warnings.append("biển trong danh sách đen")
    warning = "; ".join(warnings) or None

    session = ParkingSession(
        plate_hash=reading.plate_hash or "",
        plate_ciphertext=reading.plate_text_ciphertext or "",
        vehicle_group=group,
        vehicle_type=reading.vehicle_type,
        color=reading.color,
        status="in_lot" if has_plate else "pending_manual",
        entry_time=now_utc(),
        entry_reading_id=reading.id,
        lot_id=lot_id,
        zone_id=body.zone_id,
        match_flag="exact" if has_plate else None,
        created_by=user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    enqueue_session(db, session)
    return _session_out(session, warning=warning)


def _set_retention(db: Session, session: ParkingSession) -> None:
    if session.exit_time is None:
        return
    delete_after = session.exit_time + timedelta(days=settings.retention_days)
    for rid in (session.entry_reading_id, session.exit_reading_id):
        if not rid:
            continue
        reading = db.get(PlateReading, rid)
        if not reading:
            continue
        for aid in (reading.image_asset_id, reading.plate_crop_asset_id):
            if not aid:
                continue
            asset = db.get(ImageAsset, aid)
            if asset:
                asset.retention_delete_after = delete_after


def _complete_session(db: Session, session: ParkingSession, exit_reading_id: int | None, match_flag: str, user: User) -> None:
    session.exit_reading_id = exit_reading_id
    session.exit_time = now_utc()
    session.match_flag = match_flag
    if is_exempt(db, session.plate_hash):
        session.fee_amount = 0
        session.fee_rule_snapshot = {"exempt": True}
    else:
        rule = get_active_rule(db, session.vehicle_group)
        if rule is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "chưa có bảng giá cho nhóm xe này")
        fee, snapshot = compute_fee(rule, session.entry_time, session.exit_time)
        session.fee_amount = fee
        session.fee_rule_snapshot = snapshot
    session.status = "completed"
    session.closed_by = user.id
    _set_retention(db, session)
    enqueue_session(db, session)


@router.post("/exit", response_model=ExitResult)
def confirm_exit(body: ExitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ExitResult:
    reading = db.get(PlateReading, body.reading_id)
    if reading is None or reading.direction != "out":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading ra hợp lệ")

    in_lot = list(db.scalars(select(ParkingSession).where(ParkingSession.status == "in_lot")).all())

    if body.session_id is not None:
        chosen = next((s for s in in_lot if s.id == body.session_id), None)
        if chosen is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session được chọn không còn trong bãi")
        _complete_session(db, chosen, reading.id, match_flag="manual", user=user)
        db.commit()
        db.refresh(chosen)
        return ExitResult(outcome="completed", session=_session_out(chosen), match_flag="manual")

    target_norm = normalize_plate(crypto.decrypt_text(reading.plate_text_ciphertext)) if reading.plate_text_ciphertext else ""
    group = group_for(reading.vehicle_type) or "unknown"
    candidates = [
        Candidate(
            session_id=s.id,
            plate_hash=s.plate_hash,
            plate_norm=normalize_plate(crypto.decrypt_text(s.plate_ciphertext)) if s.plate_ciphertext else "",
            vehicle_group=s.vehicle_group,
        )
        for s in in_lot
    ]
    result = find_match(reading.plate_hash or "", target_norm, group, candidates)

    if result.kind in ("exact", "auto"):
        matched = next(s for s in in_lot if s.id == result.session_id)
        _complete_session(db, matched, reading.id, match_flag=result.match_flag, user=user)
        db.commit()
        db.refresh(matched)
        return ExitResult(outcome="completed", session=_session_out(matched), match_flag=result.match_flag)

    if result.kind == "suggest":
        briefs = [
            SessionBrief(
                id=s.id,
                plate_text=crypto.decrypt_text(s.plate_ciphertext) if s.plate_ciphertext else None,
                vehicle_group=s.vehicle_group,
                entry_time=s.entry_time,
            )
            for s in in_lot if s.id in result.candidate_ids
        ]
        return ExitResult(outcome="suggest", candidates=briefs)

    disputed = ParkingSession(
        plate_hash=reading.plate_hash or "",
        plate_ciphertext=reading.plate_text_ciphertext or "",
        vehicle_group=group,
        vehicle_type=reading.vehicle_type,
        color=reading.color,
        status="disputed",
        exit_time=now_utc(),
        exit_reading_id=reading.id,
        closed_by=user.id,
    )
    db.add(disputed)
    db.commit()
    db.refresh(disputed)
    return ExitResult(outcome="disputed", session=_session_out(disputed))


@router.post("/manual", response_model=SessionOut)
def manual_session(body: ManualRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    if body.action == "entry":
        if not body.plate_text or not body.vehicle_group:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nhập tay cần plate_text và vehicle_group")
        # Bắt buộc phải có ảnh đã nhận dạng biển số mới cho vào bãi: entry nhập tay
        # phải gắn với một reading có plate_hash (biển detect được từ ảnh).
        if body.reading_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nhập tay VÀO cần ảnh đã nhận dạng biển số")
        reading = db.get(PlateReading, body.reading_id)
        if reading is None or not reading.plate_hash:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nhập tay VÀO cần ảnh đã nhận dạng biển số")
        session = ParkingSession(
            plate_hash=plate_hash(body.plate_text),
            plate_ciphertext=crypto.encrypt_text(body.plate_text),
            vehicle_group=body.vehicle_group,
            vehicle_type=reading.vehicle_type,
            color=reading.color,
            status="in_lot",
            entry_time=now_utc(),
            entry_reading_id=reading.id,
            match_flag="manual",
            created_by=user.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return _session_out(session)

    if body.action == "exit":
        if body.session_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nhập tay ra cần session_id")
        session = db.get(ParkingSession, body.session_id)
        if session is None or session.status != "in_lot":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session không ở trạng thái in_lot")
        _complete_session(db, session, exit_reading_id=None, match_flag="manual", user=user)
        db.commit()
        db.refresh(session)
        return _session_out(session)

    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "action phải là entry hoặc exit")


@router.post("/{session_id}/dispute", response_model=SessionOut)
def dispute_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    session = db.get(ParkingSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    session.status = "disputed"
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.post("/{session_id}/resolve", response_model=SessionOut)
def resolve_session(session_id: int, body: ResolveRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    session = db.get(ParkingSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    session.fee_amount = body.fee_amount
    session.status = "completed"
    session.closed_by = user.id
    if session.exit_time is None:
        session.exit_time = now_utc()
    _set_retention(db, session)
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.post("/lost-ticket", response_model=SessionOut)
def lost_ticket(body: LostTicketRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    reading = db.get(PlateReading, body.reading_id)
    if reading is None or reading.direction != "out":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading ra hợp lệ")
    group = body.vehicle_group or group_for(reading.vehicle_type) or "unknown"
    session = ParkingSession(
        plate_hash=reading.plate_hash or "",
        plate_ciphertext=reading.plate_text_ciphertext or "",
        vehicle_group=group,
        vehicle_type=reading.vehicle_type,
        color=reading.color,
        status="completed",
        exit_time=now_utc(),
        exit_reading_id=reading.id,
        fee_amount=body.penalty_amount,
        match_flag="lost_ticket",
        closed_by=user.id,
    )
    db.add(session)
    _set_retention(db, session)
    write_audit(db, user_id=user.id, action="lost_ticket", entity_type="session",
                entity_id=None, detail=f"penalty={body.penalty_amount} group={group}")
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.get("/overstay", response_model=list[SessionOut])
def overstay(hours: int = Query(24, ge=1), db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SessionOut]:
    cutoff = now_utc() - timedelta(hours=hours)
    rows = db.scalars(
        select(ParkingSession).where(
            ParkingSession.status == "in_lot",
            ParkingSession.entry_time.is_not(None),
            ParkingSession.entry_time < cutoff,
        ).order_by(ParkingSession.entry_time)
    ).all()
    return [_session_out(s) for s in rows]


def _list_items(db: Session, rows: list[ParkingSession]) -> list[SessionListItem]:
    staff_ids = {s.closed_by for s in rows if s.closed_by}
    names: dict[int, str] = {}
    if staff_ids:
        names = dict(db.execute(select(User.id, User.username).where(User.id.in_(staff_ids))).all())
    session_ids = [s.id for s in rows]
    methods: dict[int, str] = {}
    if session_ids:
        pay_rows = db.execute(
            select(Payment.session_id, Payment.method)
            .where(Payment.session_id.in_(session_ids), Payment.kind == "payment")
            .order_by(Payment.paid_at)
        ).all()
        for sid, method in pay_rows:
            methods[sid] = method  # order_by paid_at asc: bản ghi cuối = mới nhất
    items: list[SessionListItem] = []
    for s in rows:
        base = _session_out(s)
        items.append(SessionListItem(
            **base.model_dump(),
            vehicle_type=s.vehicle_type,
            closed_by_name=names.get(s.closed_by),
            payment_method=methods.get(s.id),
        ))
    return items


@router.get("", response_model=SessionListResponse)
def list_sessions(
    plate: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    vehicle_group: str | None = Query(None),
    entry_from: datetime | None = Query(None),
    entry_to: datetime | None = Query(None),
    match_flag: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionListResponse:
    stmt = select(ParkingSession)
    if plate:
        stmt = stmt.where(ParkingSession.plate_hash == plate_hash(plate))
    if status_filter:
        stmt = stmt.where(ParkingSession.status == status_filter)
    if vehicle_group:
        stmt = stmt.where(ParkingSession.vehicle_group == vehicle_group)
    if entry_from is not None:
        stmt = stmt.where(ParkingSession.entry_time >= entry_from)
    if entry_to is not None:
        stmt = stmt.where(ParkingSession.entry_time < entry_to)
    if match_flag:
        stmt = stmt.where(ParkingSession.match_flag == match_flag)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(db.scalars(stmt.order_by(ParkingSession.id.desc()).limit(limit).offset(offset)).all())
    return SessionListResponse(total=total, items=_list_items(db, rows))


def _reading_brief(db: Session, reading_id: int | None) -> ReadingBrief | None:
    if not reading_id:
        return None
    reading = db.get(PlateReading, reading_id)
    if reading is None:
        return None
    text = crypto.decrypt_text(reading.plate_text_ciphertext) if reading.plate_text_ciphertext else None
    return ReadingBrief(
        id=reading.id, direction=reading.direction, plate_text=text,
        review_state=reading.review_state, image_asset_id=reading.image_asset_id,
        plate_crop_asset_id=reading.plate_crop_asset_id,
    )


@router.get("/{session_id}", response_model=SessionDetail)
def session_detail(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionDetail:
    s = db.get(ParkingSession, session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    base = _session_out(s)
    pay_rows = list(db.scalars(
        select(Payment).where(Payment.session_id == s.id).order_by(Payment.paid_at)
    ).all())
    staff_ids = {p.staff_id for p in pay_rows}
    for uid in (s.created_by, s.closed_by):
        if uid:
            staff_ids.add(uid)
    names: dict[int, str] = {}
    if staff_ids:
        names = dict(db.execute(select(User.id, User.username).where(User.id.in_(staff_ids))).all())
    payments = [
        PaymentBrief(
            id=p.id, amount=p.amount, method=p.method, kind=p.kind, note=p.note,
            staff_name=names.get(p.staff_id), paid_at=p.paid_at,
        )
        for p in pay_rows
    ]
    lot_name = None
    if s.lot_id:
        lot = db.get(ParkingLot, s.lot_id)
        lot_name = lot.name if lot else None
    zone_name = None
    if s.zone_id:
        zone = db.get(Zone, s.zone_id)
        zone_name = zone.name if zone else None
    return SessionDetail(
        **base.model_dump(),
        vehicle_type=s.vehicle_type,
        entry_reading=_reading_brief(db, s.entry_reading_id),
        exit_reading=_reading_brief(db, s.exit_reading_id),
        created_by_name=names.get(s.created_by),
        closed_by_name=names.get(s.closed_by),
        lot_name=lot_name,
        zone_name=zone_name,
        fee_rule_snapshot=s.fee_rule_snapshot,
        payments=payments,
    )
