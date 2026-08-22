from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import to_naive
from app.models import ParkingSession

_MIN = datetime(1970, 1, 1)
_MAX = datetime(2999, 1, 1)


def _bounds(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    return (start or _MIN, end or _MAX)


def summary(db: Session, start: datetime | None, end: datetime | None) -> dict:
    lo, hi = _bounds(start, end)
    in_lot = db.scalar(select(func.count()).select_from(ParkingSession).where(ParkingSession.status == "in_lot"))
    entries = db.scalar(select(func.count()).select_from(ParkingSession).where(
        ParkingSession.entry_time.is_not(None), ParkingSession.entry_time >= lo, ParkingSession.entry_time <= hi))
    exits = db.scalar(select(func.count()).select_from(ParkingSession).where(
        ParkingSession.status == "completed", ParkingSession.exit_time.is_not(None),
        ParkingSession.exit_time >= lo, ParkingSession.exit_time <= hi))
    revenue = db.scalar(select(func.coalesce(func.sum(ParkingSession.fee_amount), 0)).where(
        ParkingSession.status == "completed", ParkingSession.exit_time.is_not(None),
        ParkingSession.exit_time >= lo, ParkingSession.exit_time <= hi))
    return {"in_lot": int(in_lot or 0), "entries": int(entries or 0), "exits": int(exits or 0), "revenue": int(revenue or 0)}


def daily_rows(db: Session, start: datetime | None, end: datetime | None) -> list[dict]:
    lo, hi = _bounds(start, end)
    sessions = db.scalars(select(ParkingSession)).all()
    buckets: dict[str, dict] = {}

    def _bucket(day: str) -> dict:
        return buckets.setdefault(day, {"date": day, "entries": 0, "exits": 0, "revenue": 0})

    for s in sessions:
        entry_t = to_naive(s.entry_time)
        exit_t = to_naive(s.exit_time)
        if entry_t and lo <= entry_t <= hi:
            _bucket(entry_t.date().isoformat())["entries"] += 1
        if s.status == "completed" and exit_t and lo <= exit_t <= hi:
            b = _bucket(exit_t.date().isoformat())
            b["exits"] += 1
            b["revenue"] += s.fee_amount or 0
    return [buckets[k] for k in sorted(buckets)]
