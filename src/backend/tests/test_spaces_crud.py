def test_lot_crud_and_rbac(client, admin_headers, staff_headers):
    # staff không được tạo
    assert client.post("/lots", json={"name": "A", "capacity": 10}, headers=staff_headers).status_code == 403
    # admin tạo được
    r = client.post("/lots", json={"name": "A", "capacity": 10}, headers=admin_headers)
    assert r.status_code == 201
    lot_id = r.json()["id"]
    # staff đọc được
    assert client.get("/lots", headers=staff_headers).status_code == 200
    # admin sửa được
    p = client.patch(f"/lots/{lot_id}", json={"capacity": 20}, headers=admin_headers)
    assert p.status_code == 200 and p.json()["capacity"] == 20


def test_floor_and_zone_under_lot(client, admin_headers, staff_headers):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 100}, headers=admin_headers).json()["id"]
    f = client.post("/floors", json={"lot_id": lot_id, "name": "Tang 1", "capacity": 50}, headers=admin_headers)
    assert f.status_code == 201
    floor_id = f.json()["id"]
    z = client.post("/zones", json={"lot_id": lot_id, "floor_id": floor_id, "name": "Khu A", "capacity": 20}, headers=admin_headers)
    assert z.status_code == 201
    # lọc theo lot_id
    floors = client.get(f"/floors?lot_id={lot_id}", headers=staff_headers).json()
    assert len(floors) == 1 and floors[0]["name"] == "Tang 1"
    zones = client.get(f"/zones?lot_id={lot_id}", headers=staff_headers).json()
    assert len(zones) == 1 and zones[0]["floor_id"] == floor_id


def test_floor_requires_existing_lot(client, admin_headers):
    r = client.post("/floors", json={"lot_id": 9999, "name": "x", "capacity": 1}, headers=admin_headers)
    assert r.status_code == 404
