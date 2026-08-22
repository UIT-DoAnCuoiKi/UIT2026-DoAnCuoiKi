from app.models import PlateReading, PriceRule
from app.security import crypto, plate


def _reading(db, *, direction, plate_text, cid, vehicle_type="car"):
    r = PlateReading(capture_id=cid, direction=direction,
                     plate_text_ciphertext=crypto.encrypt_text(plate_text),
                     plate_hash=plate.plate_hash(plate_text), plate_valid=True,
                     vehicle_type=vehicle_type, review_state="confident")
    db.add(r); db.commit(); db.refresh(r); return r


def test_full_lifecycle(client, db_session, staff_headers):
    db_session.add(PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True))
    db_session.commit()

    # xe A vào rồi ra khớp exact
    ra = _reading(db_session, direction="in", plate_text="51F-123.45", cid="a-in")
    client.post("/sessions/entry", json={"reading_id": ra.id}, headers=staff_headers)
    ao = _reading(db_session, direction="out", plate_text="51F-123.45", cid="a-out")
    resp = client.post("/sessions/exit", json={"reading_id": ao.id}, headers=staff_headers)
    assert resp.json()["outcome"] == "completed"
    assert resp.json()["match_flag"] == "exact"
    assert resp.json()["session"]["fee_amount"] == 5000

    # xe B vào rồi ra OCR sai 1 ký tự tự nối
    rb = _reading(db_session, direction="in", plate_text="30A-678.90", cid="b-in")
    client.post("/sessions/entry", json={"reading_id": rb.id}, headers=staff_headers)
    bo = _reading(db_session, direction="out", plate_text="30A-678.91", cid="b-out")
    resp = client.post("/sessions/exit", json={"reading_id": bo.id}, headers=staff_headers)
    assert resp.json()["outcome"] == "completed"
    assert resp.json()["match_flag"] == "auto_corrected"

    # xe lạ ra không có phiên vào chuyển disputed
    co = _reading(db_session, direction="out", plate_text="99Z-999.99", cid="c-out")
    resp = client.post("/sessions/exit", json={"reading_id": co.id}, headers=staff_headers)
    assert resp.json()["outcome"] == "disputed"
    assert resp.json()["session"]["fee_amount"] is None
