import os
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_utc
from app.config import settings
from app.models import ImageAsset, ParkingSession, PlateReading
from app.services.audit import write_audit


def purge_expired(db: Session, now: datetime | None = None) -> int:
    now = now or now_utc()
    cutoff = now - timedelta(days=settings.retention_days)
    sessions = db.scalars(
        select(ParkingSession).where(
            ParkingSession.status.in_(["completed", "disputed"]),
            ParkingSession.exit_time.is_not(None),
            ParkingSession.exit_time <= cutoff,
        )
    ).all()

    count = 0
    for s in sessions:
        reading_ids = [rid for rid in (s.entry_reading_id, s.exit_reading_id) if rid]
        write_audit(db, user_id=None, action="delete", entity_type="session", entity_id=str(s.id))
        db.delete(s)
        db.flush()
        for rid in reading_ids:
            reading = db.get(PlateReading, rid)
            if reading is None:
                continue
            asset_id = reading.image_asset_id
            db.delete(reading)
            db.flush()
            if asset_id:
                asset = db.get(ImageAsset, asset_id)
                if asset:
                    try:
                        os.remove(asset.path)
                    except FileNotFoundError:
                        pass
                    db.delete(asset)
        count += 1

    db.commit()
    return count
