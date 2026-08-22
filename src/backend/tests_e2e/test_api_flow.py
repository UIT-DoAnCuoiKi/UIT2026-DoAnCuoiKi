import json
import uuid

from tests_e2e.conftest import EDGE_KEY

_IMG = b"\xff\xd8\xff e2e-image-bytes"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _capture(api, capture_id, direction, plate_text, *, edge_key=EDGE_KEY, vehicle_type="car"):
    payload = {
        "vehicle_type": vehicle_type,
        "plates": [{"plate_text": plate_text, "det_conf": 0.97, "ocr_conf": 0.9, "plate_valid": True, "color": "trắng"}],
    }
    files = {"image": (f"{capture_id}.jpg", _IMG, "image/jpeg")}
    data = {"capture_id": capture_id, "direction": direction, "lane": "lane1", "payload": json.dumps(payload)}
    return api.post("/captures", data=data, files=files, headers={"X-Edge-Key": edge_key})


def test_health(api):
    assert api.get("/health").json() == {"status": "ok"}


def test_full_gate_flow(api, admin_h, staff_h):
    uid = _uid()
    plate = f"51F-{uid[:3]}.{uid[3:5]}"

    # admin đặt bảng giá o_to_con
    r = api.post("/price-rules", json={"vehicle_group": "o_to_con", "mode": "block", "unit_price": 5000, "block_minutes": 60}, headers=admin_h)
    assert r.status_code == 201, r.text

    # xe vào: capture -> confirm entry
    r = _capture(api, f"e2e-in-{uid}", "in", plate)
    assert r.status_code == 200, r.text
    assert r.json()["review_state"] == "confident"
    assert r.json()["vehicle_group"] == "o_to_con"
    reading_in = r.json()["reading_id"]

    r = api.post("/sessions/entry", json={"reading_id": reading_in}, headers=staff_h)
    assert r.status_code == 200 and r.json()["status"] == "in_lot", r.text
    session_id = r.json()["id"]

    # xe ra: capture -> confirm exit (khớp exact, tính phí)
    r = _capture(api, f"e2e-out-{uid}", "out", plate)
    reading_out = r.json()["reading_id"]
    r = api.post("/sessions/exit", json={"reading_id": reading_out}, headers=staff_h)
    body = r.json()
    assert body["outcome"] == "completed", body
    assert body["match_flag"] == "exact"
    assert body["session"]["fee_amount"] == 5000

    # tra cứu theo biển
    r = api.get("/sessions", params={"plate": plate}, headers=staff_h)
    assert r.json()["total"] >= 1

    # chi tiết + xem ảnh vào (giải mã đúng bytes đã gửi)
    d = api.get(f"/sessions/{session_id}", headers=staff_h).json()
    img_id = d["entry_reading"]["image_asset_id"]
    assert img_id
    r = api.get(f"/images/{img_id}", headers=staff_h)
    assert r.status_code == 200 and r.content == _IMG

    # thống kê doanh thu + xuất CSV (admin)
    assert api.get("/stats", headers=staff_h).json()["revenue"] >= 5000
    r = api.get("/stats/export", headers=admin_h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "date,entries,exits,revenue" in r.text


def test_exit_without_entry_is_disputed(api, staff_h):
    uid = _uid()
    plate = f"99Z-{uid[:3]}.{uid[3:5]}"
    r = _capture(api, f"e2e-lost-{uid}", "out", plate)
    reading_out = r.json()["reading_id"]
    r = api.post("/sessions/exit", json={"reading_id": reading_out}, headers=staff_h)
    assert r.json()["outcome"] == "disputed"


def test_manual_flow(api, admin_h, staff_h):
    uid = _uid()
    api.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=admin_h)
    r = api.post("/sessions/manual", json={"action": "entry", "plate_text": f"59X1-{uid[:3]}.{uid[3:5]}", "vehicle_group": "xe_may"}, headers=staff_h)
    assert r.status_code == 200 and r.json()["match_flag"] == "manual"
    sid = r.json()["id"]
    r = api.post("/sessions/manual", json={"action": "exit", "session_id": sid}, headers=staff_h)
    assert r.json()["status"] == "completed" and r.json()["fee_amount"] == 3000


def test_rbac_and_edge_key(api, staff_h):
    # staff không được vào /users
    assert api.get("/users", headers=staff_h).status_code == 403

    # capture thiếu edge key bị chặn
    uid = _uid()
    files = {"image": ("x.jpg", b"x", "image/jpeg")}
    data = {"capture_id": f"e2e-nokey-{uid}", "direction": "in", "payload": json.dumps({"vehicle_type": "car", "plates": []})}
    assert api.post("/captures", data=data, files=files).status_code in (401, 422)

    # capture sai edge key bị chặn 401
    uid = _uid()
    r = _capture(api, f"e2e-badkey-{uid}", "in", "51F-000.01", edge_key="wrong-key")
    assert r.status_code == 401
