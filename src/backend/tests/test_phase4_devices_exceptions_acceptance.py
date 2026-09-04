def test_barrier_device_and_exception_flow(client, admin_headers, staff_headers, make_reading, db_session):
    # thiết bị barie có nhịp sống thì online
    dev = client.post("/devices", json={"kind": "barrier", "name": "cong-1"}, headers=admin_headers).json()
    client.post(f"/devices/{dev['id']}/heartbeat", headers=staff_headers)
    health = {r["device_id"]: r for r in client.get("/devices/health", headers=staff_headers).json()}
    assert health[dev["id"]]["online"] is True

    # mở barie tay có lý do, ghi audit
    ev = client.post("/barrier/open", json={"mode": "manual", "reason": "khách quên vé", "device_id": dev["id"]}, headers=staff_headers)
    assert ev.status_code == 201

    # xe ra không có phiên vào: mất vé, phí phạt
    reading = make_reading(plate="51F77777", direction="out")
    lt = client.post("/sessions/lost-ticket", json={"reading_id": reading.id, "penalty_amount": 60000}, headers=staff_headers).json()
    assert lt["match_flag"] == "lost_ticket" and lt["fee_amount"] == 60000

    # sự cố ghi lại
    inc = client.post("/incidents", json={"kind": "other", "description": "kiểm tra"}, headers=staff_headers)
    assert inc.status_code == 201

    from app.models import AuditLog
    actions = {a.action for a in db_session.query(AuditLog).all()}
    assert "barrier_open" in actions and "lost_ticket" in actions
