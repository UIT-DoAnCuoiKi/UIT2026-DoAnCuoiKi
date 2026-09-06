from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import now_utc, to_naive
from app.config import settings
from app.db import get_db
from app.deps import admin_only, get_current_user
from app.models import ImageAsset, ParkingLot, ParkingSession, Payment, PlateReading, ReadingImage, User, Zone
from app.schemas.capture import ReadingImageOut
from app.schemas.session import (
    EntryRequest, ExitPreview, ExitRequest, ExitResult, LostTicketRequest, ManualRequest, PaymentBrief, ReadingBrief,
    ResolveRequest, SessionBrief, SessionDetail, SessionListItem, SessionListResponse, SessionOut, SessionPatch,
)
from app.security import crypto
from app.security.plate import normalize_plate, plate_hash
from app.services.fee import compute_fee, get_active_rule
from app.services.audit import write_audit
from app.services.matching import Candidate, find_match
from app.services.occupancy import lot_is_full, resolve_default_lot
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


def _resolve_lot_id(db: Session, zone_id: int | None) -> int | None:
    """Bãi của phiên sắp tạo. Không có zone_id thì suy ra bãi mặc định, vì màn
    cổng không có ô chọn khu (xem resolve_default_lot)."""
    if zone_id is None:
        return resolve_default_lot(db)
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy khu")
    return zone.lot_id


def _create_entry_session(
    db: Session,
    *,
    plate_hash_value: str | None,
    plate_ciphertext: str | None,
    vehicle_group: str,
    vehicle_type: str | None,
    color: str | None,
    entry_reading_id: int | None,
    zone_id: int | None,
    override_duplicate: bool,
    match_flag: str,
    user: User,
) -> tuple[ParkingSession, str | None]:
    """Tạo phiên VÀO kèm đủ guard: sức chứa, biển trùng, danh sách đen.

    Dùng chung cho cả xác nhận VÀO tự động lẫn nhập tay, để nhập tay không lách
    được các guard này (nhập tay là đường dùng khi nhận dạng lỗi, càng cần chặt).
    Trả về (phiên, cảnh báo gộp).
    """
    lot_id = _resolve_lot_id(db, zone_id)
    if lot_id is not None and lot_is_full(db, lot_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"error_code": "lot_full", "message": "bãi đã đầy"},
        )

    has_plate = bool(plate_hash_value)
    warnings: list[str] = []
    if has_plate:
        dup = db.scalars(
            select(ParkingSession).where(
                ParkingSession.plate_hash == plate_hash_value,
                ParkingSession.status == "in_lot",
            )
        ).first()
        if dup is not None:
            if not override_duplicate:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    {"error_code": "duplicate_plate", "message": "biển đang trong bãi (xác nhận để ghi đè)"},
                )
            warnings.append("biển trùng một xe đang trong bãi")
        if is_blacklisted(db, plate_hash_value):
            warnings.append("biển trong danh sách đen")

    session = ParkingSession(
        plate_hash=plate_hash_value or "",
        plate_ciphertext=plate_ciphertext or "",
        vehicle_group=vehicle_group,
        vehicle_type=vehicle_type,
        color=color,
        status="in_lot" if has_plate else "pending_manual",
        entry_time=now_utc(),
        entry_reading_id=entry_reading_id,
        lot_id=lot_id,
        zone_id=zone_id,
        match_flag=match_flag if has_plate else None,
        created_by=user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    enqueue_session(db, session)
    return session, ("; ".join(warnings) or None)


@router.post("/entry", response_model=SessionOut)
def confirm_entry(body: EntryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    reading = db.get(PlateReading, body.reading_id)
    if reading is None or reading.direction != "in":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading vào hợp lệ")

    session, warning = _create_entry_session(
        db,
        plate_hash_value=reading.plate_hash,
        plate_ciphertext=reading.plate_text_ciphertext,
        vehicle_group=body.vehicle_group or group_for(reading.vehicle_type) or "unknown",
        vehicle_type=reading.vehicle_type,
        color=reading.color,
        entry_reading_id=reading.id,
        zone_id=body.zone_id,
        override_duplicate=body.override_duplicate,
        match_flag="exact",
        user=user,
    )
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


def _exit_reading_or_404(db: Session, reading_id: int) -> PlateReading:
    reading = db.get(PlateReading, reading_id)
    if reading is None or reading.direction != "out":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading ra hợp lệ")
    return reading


def _match_exit(db: Session, reading: PlateReading, in_lot: list[ParkingSession]):
    """Khớp reading RA với các phiên đang trong bãi. Chỉ đọc, không ghi gì.

    Tách riêng để `confirm_exit` (chốt phiên) và `preview_exit` (xem trước) dùng
    đúng một logic khớp — nếu để hai bản sao thì màn đối chiếu có thể hiện một
    phiên còn lúc xác nhận lại chốt sang phiên khác.
    """
    target_norm = (
        normalize_plate(crypto.decrypt_text(reading.plate_text_ciphertext))
        if reading.plate_text_ciphertext else ""
    )
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
    return find_match(reading.plate_hash or "", target_norm, group, candidates), group


def _session_briefs(in_lot: list[ParkingSession], ids) -> list[SessionBrief]:
    return [
        SessionBrief(
            id=s.id,
            plate_text=crypto.decrypt_text(s.plate_ciphertext) if s.plate_ciphertext else None,
            vehicle_group=s.vehicle_group,
            entry_time=s.entry_time,
        )
        for s in in_lot if s.id in ids
    ]


@router.post("/exit/preview", response_model=ExitPreview)
def preview_exit(body: ExitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ExitPreview:
    """Tính thử lượt RA để nhân viên đối chiếu trước khi thu tiền. KHÔNG ghi DB.

    Cần thiết vì `compute_fee` trước đây chỉ chạy bên trong `_complete_session`,
    tức muốn biết phí bao nhiêu thì phiên đã bị đóng mất rồi — nhân viên không có
    cơ hội đối chiếu ảnh vào/ra rồi mới quyết định.
    """
    reading = _exit_reading_or_404(db, body.reading_id)
    in_lot = list(db.scalars(select(ParkingSession).where(ParkingSession.status == "in_lot")).all())
    exit_brief = _reading_brief(db, reading.id)

    if body.session_id is not None:
        chosen = next((s for s in in_lot if s.id == body.session_id), None)
        if chosen is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session được chọn không còn trong bãi")
        return _build_preview(db, chosen, exit_brief, match_flag="manual")

    result, _group = _match_exit(db, reading, in_lot)

    if result.kind in ("exact", "auto"):
        matched = next(s for s in in_lot if s.id == result.session_id)
        return _build_preview(db, matched, exit_brief, match_flag=result.match_flag)

    if result.kind == "suggest":
        return ExitPreview(
            outcome="suggest",
            candidates=_session_briefs(in_lot, result.candidate_ids),
            exit_reading=exit_brief,
        )

    return ExitPreview(outcome="no_match", exit_reading=exit_brief)


def _build_preview(db: Session, session: ParkingSession, exit_brief, match_flag: str | None) -> ExitPreview:
    """Dựng kết quả xem trước cho một phiên đã khớp: bằng chứng 2 đầu + phí dự tính."""
    exit_at = now_utc()
    minutes = None
    if session.entry_time is not None:
        minutes = round(
            max(0.0, (to_naive(exit_at) - to_naive(session.entry_time)).total_seconds() / 60.0), 2
        )

    fee_amount: int | None = None
    snapshot: dict | None = None
    fee_error: str | None = None
    if is_exempt(db, session.plate_hash):
        fee_amount, snapshot = 0, {"exempt": True, "minutes": minutes}
    else:
        rule = get_active_rule(db, session.vehicle_group)
        if rule is None:
            fee_error = "chưa có bảng giá cho nhóm xe này"
        elif session.entry_time is None:
            fee_error = "phiên không có giờ vào, không tính được phí"
        else:
            fee_amount, snapshot = compute_fee(rule, session.entry_time, exit_at)

    return ExitPreview(
        outcome="match",
        session=_session_out(session),
        match_flag=match_flag,
        entry_reading=_reading_brief(db, session.entry_reading_id),
        exit_reading=exit_brief,
        minutes=minutes,
        fee_amount=fee_amount,
        fee_rule_snapshot=snapshot,
        fee_error=fee_error,
    )


@router.post("/exit", response_model=ExitResult)
def confirm_exit(body: ExitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ExitResult:
    reading = _exit_reading_or_404(db, body.reading_id)

    in_lot = list(db.scalars(select(ParkingSession).where(ParkingSession.status == "in_lot")).all())

    if body.session_id is not None:
        chosen = next((s for s in in_lot if s.id == body.session_id), None)
        if chosen is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session được chọn không còn trong bãi")
        _complete_session(db, chosen, reading.id, match_flag="manual", user=user)
        db.commit()
        db.refresh(chosen)
        return ExitResult(outcome="completed", session=_session_out(chosen), match_flag="manual")

    result, group = _match_exit(db, reading, in_lot)

    if result.kind in ("exact", "auto"):
        matched = next(s for s in in_lot if s.id == result.session_id)
        _complete_session(db, matched, reading.id, match_flag=result.match_flag, user=user)
        db.commit()
        db.refresh(matched)
        return ExitResult(outcome="completed", session=_session_out(matched), match_flag=result.match_flag)

    if result.kind == "suggest":
        return ExitResult(outcome="suggest", candidates=_session_briefs(in_lot, result.candidate_ids))

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
    enqueue_session(db, disputed)
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
        # Dùng chung _create_entry_session để nhập tay chịu đúng các guard như
        # xác nhận VÀO tự động: sức chứa, biển trùng, danh sách đen.
        session, warning = _create_entry_session(
            db,
            plate_hash_value=plate_hash(body.plate_text),
            plate_ciphertext=crypto.encrypt_text(body.plate_text),
            vehicle_group=body.vehicle_group,
            vehicle_type=reading.vehicle_type,
            color=reading.color,
            entry_reading_id=reading.id,
            zone_id=None,
            override_duplicate=False,
            match_flag="manual",
            user=user,
        )
        return _session_out(session, warning=warning)

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


DISPUTABLE_STATUSES = ("in_lot", "completed")


@router.post("/{session_id}/dispute", response_model=SessionOut)
def dispute_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
) -> SessionOut:
    session = db.get(ParkingSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    # Chặn chuyển trạng thái bừa: phiên đã disputed hoặc pending_manual mà bị
    # đẩy về disputed sẽ rơi khỏi báo cáo doanh thu (stats chỉ đếm completed)
    # trong khi bản ghi thanh toán vẫn còn, làm lệch đối soát.
    if session.status not in DISPUTABLE_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"chỉ tranh chấp được phiên đang {' hoặc '.join(DISPUTABLE_STATUSES)}, phiên này đang {session.status}",
        )
    previous = session.status
    session.status = "disputed"
    write_audit(db, user_id=user.id, action="dispute_session", entity_type="session",
                entity_id=str(session.id), detail=f"{previous} -> disputed")
    db.commit()
    db.refresh(session)
    enqueue_session(db, session)
    return _session_out(session)


@router.post("/{session_id}/resolve", response_model=SessionOut)
def resolve_session(
    session_id: int,
    body: ResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
) -> SessionOut:
    session = db.get(ParkingSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    if session.status != "disputed":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"chỉ giải quyết được phiên đang tranh chấp, phiên này đang {session.status}",
        )
    if body.fee_amount < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "phí không được âm")
    previous_fee = session.fee_amount
    session.fee_amount = body.fee_amount
    session.status = "completed"
    session.closed_by = user.id
    if session.exit_time is None:
        session.exit_time = now_utc()
    _set_retention(db, session)
    # Phí ở đây do người dùng nhập tay, không qua bảng giá, nên phải có vết audit
    # để đối soát về sau biết ai chốt phí và chốt bao nhiêu.
    write_audit(db, user_id=user.id, action="resolve_session", entity_type="session",
                entity_id=str(session.id), detail=f"fee {previous_fee} -> {body.fee_amount}")
    db.commit()
    db.refresh(session)
    enqueue_session(db, session)
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
    # flush trước để phiên có id, nếu không audit log ghi entity_id rỗng và mất
    # đường truy ngược từ vết audit về đúng phiên bị phạt mất vé.
    db.flush()
    write_audit(db, user_id=user.id, action="lost_ticket", entity_type="session",
                entity_id=str(session.id), detail=f"penalty={body.penalty_amount} group={group}")
    db.commit()
    db.refresh(session)
    enqueue_session(db, session)
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
    images = [
        ReadingImageOut(role=ri.role, image_asset_id=ri.image_asset_id, is_primary=ri.is_primary)
        for ri in db.scalars(
            select(ReadingImage).where(ReadingImage.reading_id == reading.id).order_by(ReadingImage.id)
        ).all()
    ]
    return ReadingBrief(
        id=reading.id, direction=reading.direction, plate_text=text,
        review_state=reading.review_state, image_asset_id=reading.image_asset_id,
        plate_crop_asset_id=reading.plate_crop_asset_id,
        created_at=reading.created_at, lane=reading.lane, images=images,
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


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: int,
    body: SessionPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionOut:
    """Chỉnh loại xe / màu biển của phiên. Không tính lại phí."""
    s = db.get(ParkingSession, session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy phiên")
    changed: list[str] = []
    if body.vehicle_type is not None:
        s.vehicle_type = body.vehicle_type or None
        changed.append("vehicle_type")
    if body.color is not None:
        s.color = body.color or None
        changed.append("color")
    if changed:
        write_audit(
            db, user_id=user.id, action="edit_session", entity_type="session",
            entity_id=str(s.id), detail=",".join(changed),
        )
        db.commit()
        db.refresh(s)
    return _session_out(s)
