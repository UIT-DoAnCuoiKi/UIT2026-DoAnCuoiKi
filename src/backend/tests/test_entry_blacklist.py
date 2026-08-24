def test_blacklisted_plate_entry_warns(client, admin_headers, staff_headers, make_reading):
    plate = "99Z99999"
    client.post("/blacklist", json={"plate_text": plate, "reason": "mất cắp"}, headers=admin_headers)
    reading = make_reading(plate=plate, direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.status_code == 200
    assert "đen" in (r.json()["warning"] or "")
