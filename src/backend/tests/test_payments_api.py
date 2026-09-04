def _completed_session(db):
    from app.clock import now_utc
    from app.models import ParkingSession
    s = ParkingSession(plate_hash="h", plate_ciphertext="x", vehicle_group="o_to_con",
                       status="completed", exit_time=now_utc(), fee_amount=20000)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_record_payment_links_open_shift(client, staff_headers, db_session):
    client.post("/shifts/open", json={"opening_cash": 0}, headers=staff_headers)
    s = _completed_session(db_session)
    r = client.post("/payments", json={"session_id": s.id, "amount": 20000, "method": "cash"}, headers=staff_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["amount"] == 20000 and body["shift_id"] is not None
    listed = client.get(f"/payments?session_id={s.id}", headers=staff_headers).json()
    assert len(listed) == 1


def test_payment_for_missing_session_404(client, staff_headers):
    assert client.post("/payments", json={"session_id": 9999, "amount": 1, "method": "cash"}, headers=staff_headers).status_code == 404


def test_payment_without_open_shift_has_null_shift(client, staff_headers, db_session):
    s = _completed_session(db_session)
    body = client.post("/payments", json={"session_id": s.id, "amount": 20000, "method": "qr"}, headers=staff_headers).json()
    assert body["shift_id"] is None
