def _token(client, make_user, role):
    make_user(username=role, password="pw", role=role)
    return client.post("/auth/login", json={"username": role, "password": "pw"}).json()["access_token"]


def test_price_rule_crud_root(client, make_user):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    from app.deps import get_db
    seed_default_vehicle_groups(next(client.app.dependency_overrides[get_db]()))
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
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

    admin_h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    r2 = client.patch("/feature-toggles", json={"read_plate": False}, headers=admin_h)
    assert r2.json()["read_plate"] is False
    assert client.patch("/feature-toggles", json={"read_plate": True}, headers=staff_h).status_code == 403


def test_lane_crud_root(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    r = client.post("/lanes", json={"name": "lane1", "rtsp_url": "rtsp://x"}, headers=h)
    assert r.status_code == 201
    assert r.json()["recognition_mode"] == "primary"
    assert r.json()["cameras"] == []
    assert client.get("/lanes", headers=h).json()[0]["name"] == "lane1"


def test_lane_camera_crud_root(client, make_user):
    """Làn 2 camera (trước + sau): mỗi camera 1 dòng riêng, vai trò riêng, biết
    cái nào là camera chính. Trước đây Lane chỉ có đúng 1 ô rtsp_url tự do."""
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    lane_id = client.post("/lanes", json={"name": "lane2"}, headers=h).json()["id"]

    front = client.post(
        f"/lanes/{lane_id}/cameras",
        json={"role": "front", "source_kind": "browser", "device_id": "webcam-1", "is_primary": True},
        headers=h,
    )
    assert front.status_code == 201
    rear = client.post(
        f"/lanes/{lane_id}/cameras",
        json={"role": "rear", "source_kind": "rtsp", "rtsp_url": "rtsp://cam-rear"},
        headers=h,
    )
    assert rear.status_code == 201

    cams = client.get(f"/lanes/{lane_id}/cameras", headers=h).json()
    assert {c["role"] for c in cams} == {"front", "rear"}
    # /lanes phải trả kèm danh sách camera — màn cấu hình cần thấy cả 2 camera
    # ngay ở màn lane, không phải gọi thêm 1 request riêng cho mỗi lane.
    lane_out = client.get("/lanes", headers=h).json()
    lane2 = next(l for l in lane_out if l["id"] == lane_id)
    assert len(lane2["cameras"]) == 2

    cam_id = rear.json()["id"]
    upd = client.patch(f"/lane-cameras/{cam_id}", json={"active": False}, headers=h)
    assert upd.json()["active"] is False

    assert client.delete(f"/lane-cameras/{cam_id}", headers=h).status_code == 204
    assert len(client.get(f"/lanes/{lane_id}/cameras", headers=h).json()) == 1


def test_lane_camera_rtsp_requires_url(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    lane_id = client.post("/lanes", json={"name": "lane3"}, headers=h).json()["id"]
    r = client.post(
        f"/lanes/{lane_id}/cameras", json={"role": "front", "source_kind": "rtsp"}, headers=h
    )
    assert r.status_code == 422


def test_lane_camera_create_forbidden_for_staff(client, make_user):
    root_h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    lane_id = client.post("/lanes", json={"name": "lane4"}, headers=root_h).json()["id"]
    staff_h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.post(
        f"/lanes/{lane_id}/cameras",
        json={"role": "front", "source_kind": "browser"},
        headers=staff_h,
    )
    assert r.status_code == 403
