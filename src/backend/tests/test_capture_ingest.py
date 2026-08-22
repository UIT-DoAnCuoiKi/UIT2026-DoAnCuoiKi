import json

GOOD_PAYLOAD = {
    "vehicle_type": "car",
    "vehicle_style": "sedan",
    "vehicle_style_conf": 0.8,
    "plates": [{
        "plate_text": "51F-123.45", "det_conf": 0.98, "ocr_conf": 0.9,
        "plate_valid": True, "layout": "1 hàng", "color": "trắng", "color_conf": 0.9,
    }],
}


def _post(client, tmp_path, monkeypatch, capture_id="c1", direction="in", payload=None):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    files = {"image": ("f.jpg", b"\xff\xd8\xff fake", "image/jpeg")}
    data = {"capture_id": capture_id, "direction": direction, "lane": "lane1",
            "payload": json.dumps(payload or GOOD_PAYLOAD)}
    return client.post("/captures", data=data, files=files, headers={"X-Edge-Key": "edge-dev-key"})


def test_ingest_confident_and_encrypted(client, tmp_path, monkeypatch, db_session):
    r = _post(client, tmp_path, monkeypatch)
    assert r.status_code == 200
    body = r.json()
    assert body["review_state"] == "confident"
    assert body["vehicle_group"] == "o_to_con"
    assert body["plate_text"] == "51F-123.45"

    from sqlalchemy import select
    from app.models import PlateReading
    from app.security import crypto, plate
    reading = db_session.scalars(select(PlateReading)).one()
    assert crypto.decrypt_text(reading.plate_text_ciphertext) == "51F-123.45"
    assert reading.plate_hash == plate.plate_hash("51F12345")


def test_idempotent_capture_id(client, tmp_path, monkeypatch, db_session):
    _post(client, tmp_path, monkeypatch, capture_id="dup")
    r2 = _post(client, tmp_path, monkeypatch, capture_id="dup")
    assert r2.json()["duplicate"] is True
    from sqlalchemy import func, select
    from app.models import PlateReading
    count = db_session.scalar(select(func.count()).select_from(PlateReading).where(PlateReading.capture_id == "dup"))
    assert count == 1


def test_needs_review_low_ocr(client, tmp_path, monkeypatch):
    payload = {"vehicle_type": "motorbike", "plates": [
        {"plate_text": "59X1", "det_conf": 0.9, "ocr_conf": 0.4, "plate_valid": True}]}
    r = _post(client, tmp_path, monkeypatch, payload=payload)
    assert r.json()["review_state"] == "needs_review"
    assert r.json()["vehicle_group"] == "xe_may"


def test_needs_review_no_plate(client, tmp_path, monkeypatch):
    payload = {"vehicle_type": "car", "plates": []}
    r = _post(client, tmp_path, monkeypatch, payload=payload)
    assert r.json()["review_state"] == "needs_review"
    assert r.json()["plate_text"] is None


def test_edge_key_required(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    files = {"image": ("f.jpg", b"x", "image/jpeg")}
    data = {"capture_id": "nokey", "direction": "in", "payload": json.dumps(GOOD_PAYLOAD)}
    r = client.post("/captures", data=data, files=files)  # thiếu X-Edge-Key
    assert r.status_code in (401, 422)
