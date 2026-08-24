def test_heartbeat_marks_online(client, admin_headers, staff_headers):
    dev = client.post("/devices", json={"kind": "camera", "name": "cam-1"}, headers=admin_headers).json()
    hb = client.post(f"/devices/{dev['id']}/heartbeat", headers=staff_headers)
    assert hb.status_code == 200
    health = client.get("/devices/health", headers=staff_headers).json()
    row = next(r for r in health if r["device_id"] == dev["id"])
    assert row["online"] is True


def test_device_without_heartbeat_is_offline(client, admin_headers, staff_headers):
    dev = client.post("/devices", json={"kind": "barrier", "name": "bar-1"}, headers=admin_headers).json()
    health = client.get("/devices/health", headers=staff_headers).json()
    row = next(r for r in health if r["device_id"] == dev["id"])
    assert row["online"] is False


def test_create_device_admin_only(client, staff_headers):
    assert client.post("/devices", json={"kind": "camera", "name": "x"}, headers=staff_headers).status_code == 403
