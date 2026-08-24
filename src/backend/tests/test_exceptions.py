def test_lost_ticket_creates_penalty_session(client, staff_headers, make_reading, db_session):
    reading = make_reading(plate="51F55555", direction="out")
    r = client.post("/sessions/lost-ticket",
                    json={"reading_id": reading.id, "penalty_amount": 50000, "vehicle_group": "o_to_con"},
                    headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["fee_amount"] == 50000
    assert body["match_flag"] == "lost_ticket"
    from app.models import AuditLog
    assert db_session.query(AuditLog).filter(AuditLog.action == "lost_ticket").count() >= 1


def test_lost_ticket_requires_out_reading(client, staff_headers, make_reading):
    reading = make_reading(plate="51F66666", direction="in")
    r = client.post("/sessions/lost-ticket", json={"reading_id": reading.id, "penalty_amount": 1}, headers=staff_headers)
    assert r.status_code == 404


def test_overstay_lists_old_in_lot(client, staff_headers, db_session):
    from datetime import timedelta
    from app.clock import now_utc
    from app.models import ParkingSession
    from app.security import crypto
    # ciphertext hợp lệ như luồng thật: phiên luôn lưu Fernet token hoặc chuỗi rỗng
    old = ParkingSession(plate_hash="h1", plate_ciphertext=crypto.encrypt_text("51F00001"), vehicle_group="o_to_con",
                         status="in_lot", entry_time=now_utc() - timedelta(hours=30))
    fresh = ParkingSession(plate_hash="h2", plate_ciphertext=crypto.encrypt_text("51F00002"), vehicle_group="o_to_con",
                           status="in_lot", entry_time=now_utc())
    db_session.add_all([old, fresh]); db_session.commit()
    rows = client.get("/sessions/overstay?hours=24", headers=staff_headers).json()
    ids = {r["id"] for r in rows}
    assert old.id in ids and fresh.id not in ids
