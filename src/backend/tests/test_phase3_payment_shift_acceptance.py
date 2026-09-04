def test_shift_with_payments_reconciles_end_to_end(client, staff_headers, db_session):
    from app.clock import now_utc
    from app.models import ParkingSession

    client.post("/shifts/open", json={"opening_cash": 100000}, headers=staff_headers)

    # hai phiên hoàn tất, thu tiền mặt
    total = 0
    for fee in (20000, 15000):
        s = ParkingSession(plate_hash=f"h{fee}", plate_ciphertext="x", vehicle_group="o_to_con",
                           status="completed", exit_time=now_utc(), fee_amount=fee)
        db_session.add(s); db_session.commit(); db_session.refresh(s)
        client.post("/payments", json={"session_id": s.id, "amount": fee, "method": "cash"}, headers=staff_headers)
        total += fee

    # đếm khớp đúng: đầu 100000 cộng 35000
    recon = client.post("/shifts/close", json={"closing_cash": 100000 + total}, headers=staff_headers).json()
    assert recon["system_total"] == total
    assert recon["counted"] == total
    assert recon["difference"] == 0
