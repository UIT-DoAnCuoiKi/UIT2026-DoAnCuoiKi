def test_occupancy_endpoint_reports_lots_and_zones(client, admin_headers, staff_headers):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 4}, headers=admin_headers).json()["id"]
    client.post("/zones", json={"lot_id": lot_id, "name": "Z1", "capacity": 2}, headers=admin_headers)

    data = client.get("/occupancy", headers=staff_headers).json()
    row = next(r for r in data["lots"] if r["lot_id"] == lot_id)
    assert row["capacity"] == 4
    assert row["occupancy"] == 0
    assert row["available"] == 4
    assert len(row["zones"]) == 1


def test_occupancy_endpoint_requires_auth(client):
    assert client.get("/occupancy").status_code in (401, 403)
