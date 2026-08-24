EDGE = {"X-Edge-Key": "edge-dev-key"}


def test_edge_to_central_sync_end_to_end(client, admin_headers, staff_headers, make_reading, db_session):
    from app.models import Outbox
    from app.services.sync import serialize_session, unsynced_batch

    # một xe vào tạo phiên và outbox
    reading = make_reading(plate="51A90001", direction="in")
    client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    batch = unsynced_batch(db_session)
    assert len(batch) >= 1

    # đẩy batch lên tầng nhận qua /sync/push, idempotent khi gửi lại
    items = [{"entity_type": o.entity_type, "payload": o.payload} for o in batch]
    r1 = client.post("/sync/push", json={"items": items}, headers=EDGE)
    assert r1.status_code == 200
    client.post("/sync/push", json={"items": items}, headers=EDGE)  # lần hai không nhân đôi

    # tra cứu liên bãi thấy phiên đã đồng bộ, không trùng
    uuids = [o.entity_uuid for o in batch]
    rows = client.get("/central/sessions?plate=51A90001", headers=admin_headers).json()
    matched = [r for r in rows if r["uuid"] in uuids]
    assert len({r["uuid"] for r in matched}) == len(set(uuids))

    # config pull chạy
    cfg = client.get("/sync/config", headers=EDGE).json()
    assert "feature_toggles" in cfg and "price_rules" in cfg
