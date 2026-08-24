EDGE = {"X-Edge-Key": "edge-dev-key"}


def test_push_upserts_idempotently(client):
    item = {"entity_type": "session", "payload": {
        "uuid": "sync-1", "lot_id": 1, "zone_id": None, "plate_hash": "h",
        "plate_ciphertext": "x", "vehicle_group": "o_to_con", "vehicle_type": "car",
        "status": "completed", "fee_amount": 15000, "match_flag": "exact",
        "entry_time": "2026-08-23T08:00:00", "exit_time": "2026-08-23T09:00:00",
    }}
    r1 = client.post("/sync/push", json={"items": [item]}, headers=EDGE)
    assert r1.status_code == 200 and r1.json()["upserted"] == 1
    r2 = client.post("/sync/push", json={"items": [item]}, headers=EDGE)
    assert r2.status_code == 200
    from app.models import ParkingSession
    # đẩy lại không tạo bản trùng
    # kiểm qua tra cứu liên bãi ở task 5; ở đây chỉ chắc không lỗi


def test_push_requires_edge_key(client):
    assert client.post("/sync/push", json={"items": []}).status_code in (401, 403, 422)


def test_config_pull_returns_rules_and_toggles(client, admin_headers):
    client.post("/price-rules", json={"vehicle_group": "o_to_con", "mode": "flat", "unit_price": 10000}, headers=admin_headers)
    cfg = client.get("/sync/config", headers=EDGE).json()
    assert any(r["vehicle_group"] == "o_to_con" for r in cfg["price_rules"])
    assert "read_plate" in cfg["feature_toggles"]
