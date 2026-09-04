def test_multilot_capacity_end_to_end(client, admin_headers, staff_headers, make_reading):
    # admin dựng một bãi hai tầng, mỗi tầng một khu, sức chứa bãi 2
    lot_id = client.post("/lots", json={"name": "Bai Trung Tam", "capacity": 2}, headers=admin_headers).json()["id"]
    f1 = client.post("/floors", json={"lot_id": lot_id, "name": "Tang 1", "capacity": 1}, headers=admin_headers).json()["id"]
    f2 = client.post("/floors", json={"lot_id": lot_id, "name": "Tang 2", "capacity": 1}, headers=admin_headers).json()["id"]
    z1 = client.post("/zones", json={"lot_id": lot_id, "floor_id": f1, "name": "Khu A", "capacity": 1}, headers=admin_headers).json()["id"]
    z2 = client.post("/zones", json={"lot_id": lot_id, "floor_id": f2, "name": "Khu B", "capacity": 1}, headers=admin_headers).json()["id"]

    # hai xe vào hai khu khác nhau, lấp đầy bãi
    a = make_reading(plate="51F00001", direction="in")
    b = make_reading(plate="51F00002", direction="in")
    assert client.post("/sessions/entry", json={"reading_id": a.id, "zone_id": z1}, headers=staff_headers).status_code == 200
    assert client.post("/sessions/entry", json={"reading_id": b.id, "zone_id": z2}, headers=staff_headers).status_code == 200

    # báo cáo sức chứa: bãi đầy, mỗi khu 1 xe
    report = client.get("/occupancy", headers=staff_headers).json()["lots"]
    row = next(r for r in report if r["lot_id"] == lot_id)
    assert row["occupancy"] == 2
    assert row["available"] == 0
    assert row["full"] is True
    assert {z["zone_id"]: z["occupancy"] for z in row["zones"]} == {z1: 1, z2: 1}

    # xe thứ ba bị chặn vì bãi đầy
    c = make_reading(plate="51F00003", direction="in")
    assert client.post("/sessions/entry", json={"reading_id": c.id, "zone_id": z1}, headers=staff_headers).status_code == 409
