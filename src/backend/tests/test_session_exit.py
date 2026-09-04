from app.models import PlateReading, PriceRule
from app.security import crypto, plate


def _seed_price(db):
    db.add(PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True))
    db.commit()


def _reading(db, *, direction, plate_text, vehicle_type="car", cid):
    r = PlateReading(
        capture_id=cid, direction=direction,
        plate_text_ciphertext=crypto.encrypt_text(plate_text) if plate_text else None,
        plate_hash=plate.plate_hash(plate_text) if plate_text else None,
        plate_valid=True, vehicle_type=vehicle_type, review_state="confident",
    )
    db.add(r); db.commit(); db.refresh(r); return r


def _enter(client, db, headers, plate_text, cid):
    reading = _reading(db, direction="in", plate_text=plate_text, cid=cid)
    return client.post("/sessions/entry", json={"reading_id": reading.id}, headers=headers).json()


def test_exit_exact_completes_with_fee(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.45", "in1")
    out = _reading(db_session, direction="out", plate_text="51F-123.45", cid="out1")
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    body = r.json()
    assert body["outcome"] == "completed"
    assert body["match_flag"] == "exact"
    assert body["session"]["status"] == "completed"
    assert body["session"]["fee_amount"] == 5000


def test_exit_fuzzy_k1_auto(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.45", "in2")
    out = _reading(db_session, direction="out", plate_text="51F-123.46", cid="out2")  # sai 1 ký tự
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    assert r.json()["outcome"] == "completed"
    assert r.json()["match_flag"] == "auto_corrected"


def test_exit_two_candidates_suggests(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.46", "in3a")
    _enter(client, db_session, staff_headers, "51F-123.44", "in3b")  # cả hai cách biển ra 1 ký tự
    out = _reading(db_session, direction="out", plate_text="51F-123.45", cid="out3")
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    body = r.json()
    assert body["outcome"] == "suggest"
    assert len(body["candidates"]) == 2


def test_exit_choose_candidate_completes(client, db_session, staff_headers):
    _seed_price(db_session)
    s = _enter(client, db_session, staff_headers, "51F-123.46", "in4")
    out = _reading(db_session, direction="out", plate_text="51F-999.99", cid="out4")
    r = client.post("/sessions/exit", json={"reading_id": out.id, "session_id": s["id"]}, headers=staff_headers)
    assert r.json()["outcome"] == "completed"
    assert r.json()["match_flag"] == "manual"


def test_exit_no_candidate_disputed(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.45", "in5")
    out = _reading(db_session, direction="out", plate_text="99Z-999.99", cid="out5")
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    body = r.json()
    assert body["outcome"] == "disputed"
    assert body["session"]["fee_amount"] is None
