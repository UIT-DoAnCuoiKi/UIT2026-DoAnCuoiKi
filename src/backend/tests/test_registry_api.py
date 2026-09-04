def test_monthly_pass_crud_and_plaintext_roundtrip(client, admin_headers, staff_headers):
    body = {"plate_text": "51F12345", "vehicle_group": "o_to_con",
            "start_date": "2026-08-01", "end_date": "2026-08-31"}
    r = client.post("/monthly-passes", json=body, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["plate_text"] == "51F12345"
    listed = client.get("/monthly-passes", headers=staff_headers).json()
    assert any(p["plate_text"] == "51F12345" for p in listed)


def test_whitelist_and_blacklist_admin_only(client, admin_headers, staff_headers):
    assert client.post("/whitelist", json={"plate_text": "51F1"}, headers=staff_headers).status_code == 403
    assert client.post("/whitelist", json={"plate_text": "51F1"}, headers=admin_headers).status_code == 201
    assert client.post("/blacklist", json={"plate_text": "99Z9", "reason": "mất cắp"}, headers=admin_headers).status_code == 201
    bl = client.get("/blacklist", headers=staff_headers).json()
    assert any(x["plate_text"] == "99Z9" for x in bl)
