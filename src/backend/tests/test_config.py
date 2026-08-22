def _token(client, make_user, role):
    make_user(username=role, password="pw", role=role)
    return client.post("/auth/login", json={"username": role, "password": "pw"}).json()["access_token"]


def test_price_rule_crud_admin(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'admin')}"}
    r = client.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=h)
    assert r.status_code == 201
    rid = r.json()["id"]
    assert client.get("/price-rules", headers=h).status_code == 200
    r2 = client.patch(f"/price-rules/{rid}", json={"unit_price": 4000}, headers=h)
    assert r2.json()["unit_price"] == 4000


def test_price_rule_create_forbidden_for_staff(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=h)
    assert r.status_code == 403


def test_feature_toggle_get_default_and_update(client, make_user):
    staff_h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.get("/feature-toggles", headers=staff_h)
    assert r.status_code == 200
    assert r.json()["read_plate"] is True

    admin_h = {"Authorization": f"Bearer {_token(client, make_user, 'admin')}"}
    r2 = client.patch("/feature-toggles", json={"read_plate": False}, headers=admin_h)
    assert r2.json()["read_plate"] is False
    assert client.patch("/feature-toggles", json={"read_plate": True}, headers=staff_h).status_code == 403


def test_lane_crud_admin(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'admin')}"}
    r = client.post("/lanes", json={"name": "lane1", "rtsp_url": "rtsp://x"}, headers=h)
    assert r.status_code == 201
    assert client.get("/lanes", headers=h).json()[0]["name"] == "lane1"
