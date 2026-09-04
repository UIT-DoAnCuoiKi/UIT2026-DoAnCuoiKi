def test_create_and_list_incident(client, staff_headers):
    r = client.post("/incidents", json={"kind": "collision", "description": "va chạm nhẹ"}, headers=staff_headers)
    assert r.status_code == 201
    assert r.json()["kind"] == "collision"
    listed = client.get("/incidents", headers=staff_headers).json()
    assert len(listed) >= 1


def test_filter_incident_by_session(client, staff_headers):
    client.post("/incidents", json={"kind": "damage", "session_id": 7}, headers=staff_headers)
    listed = client.get("/incidents?session_id=7", headers=staff_headers).json()
    assert all(i["session_id"] == 7 for i in listed)
    assert len(listed) >= 1
