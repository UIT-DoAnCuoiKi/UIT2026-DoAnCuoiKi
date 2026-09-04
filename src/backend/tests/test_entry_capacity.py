def test_entry_assigns_lot_and_zone_and_counts(client, admin_headers, staff_headers, make_reading):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 10}, headers=admin_headers).json()["id"]
    zone_id = client.post("/zones", json={"lot_id": lot_id, "name": "Z1", "capacity": 5}, headers=admin_headers).json()["id"]

    reading = make_reading(plate="51F00001", direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id, "zone_id": zone_id}, headers=staff_headers)
    assert r.status_code == 200

    row = next(x for x in client.get("/occupancy", headers=staff_headers).json()["lots"] if x["lot_id"] == lot_id)
    assert row["occupancy"] == 1
    assert row["zones"][0]["occupancy"] == 1


def test_entry_rejected_when_lot_full(client, admin_headers, staff_headers, make_reading):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 1}, headers=admin_headers).json()["id"]
    zone_id = client.post("/zones", json={"lot_id": lot_id, "name": "Z", "capacity": 1}, headers=admin_headers).json()["id"]

    r1 = make_reading(plate="51F11111", direction="in")
    assert client.post("/sessions/entry", json={"reading_id": r1.id, "zone_id": zone_id}, headers=staff_headers).status_code == 200

    r2 = make_reading(plate="51F22222", direction="in")
    resp = client.post("/sessions/entry", json={"reading_id": r2.id, "zone_id": zone_id}, headers=staff_headers)
    assert resp.status_code == 409


def test_entry_without_zone_still_works(client, staff_headers, make_reading):
    reading = make_reading(plate="51F33333", direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.status_code == 200


def test_entry_unknown_zone_returns_404(client, staff_headers, make_reading):
    reading = make_reading(plate="51F44444", direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id, "zone_id": 9999}, headers=staff_headers)
    assert r.status_code == 404
