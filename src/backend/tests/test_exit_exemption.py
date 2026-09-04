def test_whitelisted_plate_exits_free(client, admin_headers, staff_headers, make_reading, db_session):
    from app.models import ParkingSession
    from app.clock import now_utc
    from app.security import crypto
    from app.security.plate import plate_hash

    plate = "51F88888"
    client.post("/whitelist", json={"plate_text": plate}, headers=admin_headers)
    # ciphertext hợp lệ như luồng thật
    session = ParkingSession(plate_hash=plate_hash(plate), plate_ciphertext=crypto.encrypt_text(plate),
                             vehicle_group="o_to_con", status="in_lot", entry_time=now_utc())
    db_session.add(session); db_session.commit(); db_session.refresh(session)

    out_reading = make_reading(plate=plate, direction="out")
    r = client.post("/sessions/exit", json={"reading_id": out_reading.id, "session_id": session.id}, headers=staff_headers)
    assert r.status_code == 200
    assert r.json()["session"]["fee_amount"] == 0
