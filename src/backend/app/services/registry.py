from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_utc
from app.models import MonthlyPass, PlateBlacklist, PlateWhitelist


def has_valid_pass(db: Session, plate_hash: str, on: date | None = None) -> bool:
    if not plate_hash:
        return False
    today = on or now_utc().date()
    passes = db.scalars(
        select(MonthlyPass).where(MonthlyPass.plate_hash == plate_hash, MonthlyPass.active.is_(True))
    ).all()
    return any(p.start_date <= today <= p.end_date for p in passes)


def is_whitelisted(db: Session, plate_hash: str) -> bool:
    if not plate_hash:
        return False
    return db.scalars(
        select(PlateWhitelist).where(PlateWhitelist.plate_hash == plate_hash, PlateWhitelist.active.is_(True))
    ).first() is not None


def is_blacklisted(db: Session, plate_hash: str) -> bool:
    if not plate_hash:
        return False
    return db.scalars(
        select(PlateBlacklist).where(PlateBlacklist.plate_hash == plate_hash, PlateBlacklist.active.is_(True))
    ).first() is not None


def is_exempt(db: Session, plate_hash: str) -> bool:
    return has_valid_pass(db, plate_hash) or is_whitelisted(db, plate_hash)
