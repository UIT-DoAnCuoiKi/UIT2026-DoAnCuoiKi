from app.models import ParkingSession, PlateReading
from app.security import crypto, plate


def _insert_reading(db, *, direction="in", plate_text="51F-123.45", vehicle_type="car", cid=None):
    r = PlateReading(
        capture_id=cid or f"cap-{plate_text}-{direction}",
        direction=direction,
        plate_text_ciphertext=crypto.encrypt_text(plate_text) if plate_text else None,
        plate_hash=plate.plate_hash(plate_text) if plate_text else None,
        plate_valid=True,
        vehicle_type=vehicle_type,
        review_state="confident" if plate_text else "needs_review",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_entry_creates_in_lot(client, db_session, staff_headers):
    reading = _insert_reading(db_session)
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "in_lot"
    assert body["vehicle_group"] == "o_to_con"
    assert body["plate_text"] == "51F-123.45"


def test_entry_no_plate_pending_manual(client, db_session, staff_headers):
    reading = _insert_reading(db_session, plate_text=None)
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.json()["status"] == "pending_manual"


def test_entry_duplicate_plate_warns_not_blocks(client, db_session, staff_headers):
    r1 = _insert_reading(db_session, cid="c1")
    client.post("/sessions/entry", json={"reading_id": r1.id}, headers=staff_headers)
    r2 = _insert_reading(db_session, cid="c2")
    resp = client.post("/sessions/entry", json={"reading_id": r2.id}, headers=staff_headers)
    assert resp.status_code == 200
    assert resp.json()["warning"] is not None
    assert db_session.query(ParkingSession).count() == 2


def test_entry_requires_auth(client, db_session):
    reading = _insert_reading(db_session)
    assert client.post("/sessions/entry", json={"reading_id": reading.id}).status_code in (401, 403)
