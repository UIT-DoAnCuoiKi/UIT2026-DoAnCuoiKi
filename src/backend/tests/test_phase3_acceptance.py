import json
from pathlib import Path

from sqlalchemy import func, select

from app.models import ImageAsset, PlateReading
from app.security import crypto, plate


def test_capture_pipeline_end_to_end(client, tmp_path, monkeypatch, db_session):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))

    payload = {
        "vehicle_type": "car", "vehicle_style": "SUV", "vehicle_style_conf": 0.7,
        "plates": [{"plate_text": "30A-678.90", "det_conf": 0.97, "ocr_conf": 0.88, "plate_valid": True, "color": "trắng"}],
    }
    files = {"image": ("in.jpg", b"\xff\xd8\xff raw", "image/jpeg")}
    data = {"capture_id": "e2e-1", "direction": "in", "lane": "lane1", "payload": json.dumps(payload)}
    h = {"X-Edge-Key": "edge-dev-key"}

    r = client.post("/captures", data=data, files=files, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["review_state"] == "confident"
    assert body["vehicle_group"] == "o_to_con"

    reading = db_session.scalars(select(PlateReading).where(PlateReading.capture_id == "e2e-1")).one()
    assert reading.plate_hash == plate.plate_hash("30A67890")

    asset = db_session.get(ImageAsset, reading.image_asset_id)
    stored = Path(asset.path).read_bytes()
    assert crypto.decrypt_bytes(stored) == b"\xff\xd8\xff raw"

    files2 = {"image": ("in.jpg", b"\xff\xd8\xff raw", "image/jpeg")}
    r2 = client.post("/captures", data=data, files=files2, headers=h)
    assert r2.json()["duplicate"] is True
    assert db_session.scalar(select(func.count()).select_from(PlateReading)) == 1
