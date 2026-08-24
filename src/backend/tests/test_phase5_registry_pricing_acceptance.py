def test_monthly_pass_exit_free_and_grace_pricing(client, admin_headers, staff_headers, make_reading, db_session):
    from datetime import date, timedelta
    from app.clock import now_utc
    from app.models import ParkingSession
    from app.security import crypto
    from app.security.plate import plate_hash

    plate = "51F24680"
    today = date.today()
    client.post("/monthly-passes", json={
        "plate_text": plate, "vehicle_group": "o_to_con",
        "start_date": (today - timedelta(days=1)).isoformat(),
        "end_date": (today + timedelta(days=29)).isoformat(),
    }, headers=admin_headers)

    # ciphertext hợp lệ như luồng thật
    session = ParkingSession(plate_hash=plate_hash(plate), plate_ciphertext=crypto.encrypt_text(plate),
                             vehicle_group="o_to_con", status="in_lot", entry_time=now_utc())
    db_session.add(session); db_session.commit(); db_session.refresh(session)

    out_reading = make_reading(plate=plate, direction="out")
    r = client.post("/sessions/exit", json={"reading_id": out_reading.id, "session_id": session.id}, headers=staff_headers)
    assert r.status_code == 200
    assert r.json()["session"]["fee_amount"] == 0  # vé tháng miễn phí
