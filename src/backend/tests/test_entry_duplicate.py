def test_entry_duplicate_plate_blocked(client, staff_headers, make_reading):
    r1 = make_reading(plate="51F00001", direction="in", capture_id="cap-dup-1")
    r2 = make_reading(plate="51F00001", direction="in", capture_id="cap-dup-2")
    assert client.post("/sessions/entry", json={"reading_id": r1.id}, headers=staff_headers).status_code == 200
    resp = client.post("/sessions/entry", json={"reading_id": r2.id}, headers=staff_headers)
    assert resp.status_code == 409
    assert "trong bãi" in resp.json()["detail"]


def test_entry_duplicate_override_allows(client, staff_headers, make_reading):
    r1 = make_reading(plate="51F00002", direction="in", capture_id="cap-dup-3")
    r2 = make_reading(plate="51F00002", direction="in", capture_id="cap-dup-4")
    assert client.post("/sessions/entry", json={"reading_id": r1.id}, headers=staff_headers).status_code == 200
    resp = client.post(
        "/sessions/entry",
        json={"reading_id": r2.id, "override_duplicate": True},
        headers=staff_headers,
    )
    assert resp.status_code == 200
    assert "trùng" in (resp.json()["warning"] or "")
