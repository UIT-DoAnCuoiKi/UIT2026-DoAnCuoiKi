from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from app.clock import now_utc
from app.models import AuditLog, ParkingSession, PlateReading
from app.security import crypto, plate
from app.services.image_store import store_encrypted_image
from app.services.retention import purge_expired


def test_dashboard_and_retention(client, db_session, staff_headers, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "retention_days", 30)

    asset = store_encrypted_image(db_session, b"\xff\xd8\xff raw", "in")
    db_session.commit()
    reading = PlateReading(capture_id="acc-in", direction="in", image_asset_id=asset.id, review_state="confident")
    db_session.add(reading); db_session.commit(); db_session.refresh(reading)

    old = now_utc() - timedelta(days=40)
    s = ParkingSession(plate_hash=plate.plate_hash("51F-123.45"), plate_ciphertext=crypto.encrypt_text("51F-123.45"),
                       vehicle_group="o_to_con", status="completed", entry_time=old, exit_time=old,
                       fee_amount=5000, entry_reading_id=reading.id)
    db_session.add(s); db_session.commit()

    # tra cứu theo biển
    r = client.get("/sessions", params={"plate": "51F-123.45"}, headers=staff_headers)
    assert r.json()["total"] == 1

    # xem ảnh ghi audit
    assert client.get(f"/images/{asset.id}", headers=staff_headers).content == b"\xff\xd8\xff raw"
    assert db_session.scalars(select(AuditLog).where(AuditLog.action == "view_image")).all()

    # thống kê doanh thu toàn thời gian
    stats = client.get("/stats", headers=staff_headers).json()
    assert stats["revenue"] == 5000

    # job xóa dữ liệu quá hạn
    path = asset.path
    assert purge_expired(db_session) == 1
    assert not Path(path).exists()
    assert db_session.get(ParkingSession, s.id) is None
