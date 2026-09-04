from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import to_naive
from app.models import Outbox, ParkingSession

_FIELDS = (
    "uuid", "lot_id", "zone_id", "plate_hash", "plate_ciphertext",
    "vehicle_group", "vehicle_type", "status", "fee_amount", "match_flag",
)
_TIME_FIELDS = ("entry_time", "exit_time")


def _iso(dt: datetime | None) -> str | None:
    d = to_naive(dt)
    return d.isoformat() if d is not None else None


def serialize_session(session: ParkingSession) -> dict:
    data = {f: getattr(session, f) for f in _FIELDS}
    for f in _TIME_FIELDS:
        data[f] = _iso(getattr(session, f))
    return data


def enqueue_session(db: Session, session: ParkingSession) -> None:
    db.add(Outbox(
        entity_type="session", entity_uuid=session.uuid,
        lot_id=session.lot_id, payload=serialize_session(session),
    ))
    db.commit()


def unsynced_batch(db: Session, limit: int = 100) -> list[Outbox]:
    return list(db.scalars(
        select(Outbox).where(Outbox.synced.is_(False)).order_by(Outbox.id).limit(limit)
    ).all())


def mark_synced(db: Session, outbox_ids: list[int]) -> None:
    for oid in outbox_ids:
        row = db.get(Outbox, oid)
        if row is not None:
            row.synced = True
    db.commit()


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def upsert_session_from_sync(db: Session, payload: dict) -> ParkingSession:
    existing = db.scalars(select(ParkingSession).where(ParkingSession.uuid == payload["uuid"])).first()
    target = existing or ParkingSession(uuid=payload["uuid"])
    for f in _FIELDS:
        if f == "uuid":
            continue
        setattr(target, f, payload.get(f))
    target.entry_time = _parse_time(payload.get("entry_time"))
    target.exit_time = _parse_time(payload.get("exit_time"))
    if existing is None:
        db.add(target)
    db.commit(); db.refresh(target)
    return target
