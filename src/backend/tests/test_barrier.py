def test_auto_open_no_reason_ok(client, staff_headers):
    r = client.post("/barrier/open", json={"mode": "auto"}, headers=staff_headers)
    assert r.status_code == 201
    assert r.json()["mode"] == "auto"


def test_manual_open_requires_reason(client, staff_headers):
    assert client.post("/barrier/open", json={"mode": "manual"}, headers=staff_headers).status_code == 422
    ok = client.post("/barrier/open", json={"mode": "manual", "reason": "khách quên vé"}, headers=staff_headers)
    assert ok.status_code == 201


def test_manual_open_writes_audit(client, staff_headers, db_session):
    from app.models import AuditLog
    client.post("/barrier/open", json={"mode": "emergency", "reason": "PCCC"}, headers=staff_headers)
    audits = db_session.query(AuditLog).filter(AuditLog.action == "barrier_open").all()
    assert len(audits) >= 1
    assert "PCCC" in (audits[-1].detail or "")


def test_list_barrier_events(client, staff_headers):
    client.post("/barrier/open", json={"mode": "auto"}, headers=staff_headers)
    events = client.get("/barrier/events?limit=10", headers=staff_headers).json()
    assert len(events) >= 1
