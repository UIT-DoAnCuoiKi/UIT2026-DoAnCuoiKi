def test_open_current_close_flow(client, staff_headers):
    o = client.post("/shifts/open", json={"opening_cash": 100000}, headers=staff_headers)
    assert o.status_code == 201
    cur = client.get("/shifts/current", headers=staff_headers).json()
    assert cur["status"] == "open" and cur["opening_cash"] == 100000
    # mở lần hai bị chặn
    assert client.post("/shifts/open", json={"opening_cash": 1}, headers=staff_headers).status_code == 409
    c = client.post("/shifts/close", json={"closing_cash": 100000}, headers=staff_headers)
    assert c.status_code == 200
    body = c.json()
    assert body["system_total"] == 0 and body["counted"] == 0 and body["difference"] == 0
    # không còn ca mở
    assert client.get("/shifts/current", headers=staff_headers).status_code == 404


def test_close_without_open_returns_404(client, staff_headers):
    assert client.post("/shifts/close", json={"closing_cash": 0}, headers=staff_headers).status_code == 404
