import json


def test_publish_noop_without_loop():
    from app.services.gate_hub import GateHub
    GateHub().publish({"a": 1})  # không lỗi khi chưa bind loop


def test_captures_latest_returns_recent(client, db_session, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    payload = {"vehicle_type": "car", "plates": [{"plate_text": "51F-123.45", "det_conf": 0.9, "ocr_conf": 0.9, "plate_valid": True}]}
    files = {"image": ("f.jpg", b"x", "image/jpeg")}
    data = {"capture_id": "L1", "direction": "in", "lane": "lane1", "payload": json.dumps(payload)}
    client.post("/captures", data=data, files=files, headers={"X-Edge-Key": "edge-dev-key"})

    r = client.get("/captures/latest")
    assert r.status_code == 200
    assert r.json()["capture_id"] == "L1"
    assert r.json()["review_state"] == "confident"


def test_ws_gate_receives_event(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    payload = {"vehicle_type": "car", "plates": [{"plate_text": "30A-1", "det_conf": 0.9, "ocr_conf": 0.9, "plate_valid": True}]}
    with client.websocket_connect("/ws/gate") as ws:
        files = {"image": ("f.jpg", b"x", "image/jpeg")}
        data = {"capture_id": "WS1", "direction": "in", "lane": "lane1", "payload": json.dumps(payload)}
        client.post("/captures", data=data, files=files, headers={"X-Edge-Key": "edge-dev-key"})
        event = ws.receive_json()
    assert event["capture_id"] == "WS1"
    assert event["direction"] == "in"
