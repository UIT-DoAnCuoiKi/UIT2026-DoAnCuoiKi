from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from app.clock import now_utc
from app.models import AuditLog, ParkingSession, PlateReading
from app.services.image_store import store_encrypted_image
from app.services.retention import purge_expired


def _expired_session(db, tmp_path, monkeypatch, days_ago):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "retention_days", 30)
    asset = store_encrypted_image(db, b"img-bytes", "in")
    db.commit()
    reading = PlateReading(capture_id=f"r-{days_ago}", direction="in", image_asset_id=asset.id, review_state="manual")
    db.add(reading); db.commit(); db.refresh(reading)
    when = now_utc() - timedelta(days=days_ago)
    s = ParkingSession(plate_hash="h", plate_ciphertext="", vehicle_group="o_to_con",
                       status="completed", entry_time=when, exit_time=when, entry_reading_id=reading.id)
    db.add(s); db.commit(); db.refresh(s)
    return s, reading, asset.path


def test_purge_removes_expired(db_session, tmp_path, monkeypatch):
    s, reading, path = _expired_session(db_session, tmp_path, monkeypatch, days_ago=40)
    assert Path(path).exists()

    n = purge_expired(db_session)
    assert n == 1
    assert not Path(path).exists()
    assert db_session.get(ParkingSession, s.id) is None
    assert db_session.get(PlateReading, reading.id) is None
    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "delete")).all()
    assert len(logs) == 1


def test_purge_keeps_recent(db_session, tmp_path, monkeypatch):
    s, reading, path = _expired_session(db_session, tmp_path, monkeypatch, days_ago=5)
    assert purge_expired(db_session) == 0
    assert db_session.get(ParkingSession, s.id) is not None
    assert Path(path).exists()
