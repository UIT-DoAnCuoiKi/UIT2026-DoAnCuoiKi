"""E2E qua API cho luồng trạm cổng: chụp/nhận dạng -> sửa tay (loại xe, màu
biển) -> xác nhận VÀO -> chụp RA -> khớp phiên + tính phí -> thu tiền -> chi
tiết phiên phản ánh đúng dữ liệu đã sửa tay.

FakeInferenceEngine (mặc định khi settings.inference_engine != "ml") trả cố định
vehicle_type=car, color=white, plate=51F12345, nên test không phụ thuộc mô hình.
"""
from app.models import PriceRule

IMG = ("frame.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")


def test_gate_full_flow_edit_then_exit_and_pay(client, db_session, staff_headers):
    # Bảng giá cho nhóm xe tải (nhóm suy ra sau khi nhân viên sửa loại xe = truck).
    db_session.add(PriceRule(vehicle_group="xe_tai", mode="flat", unit_price=5000, grace_minutes=0, active=True))
    db_session.commit()

    # 1. VÀO: chụp khung hình + nhận dạng.
    r_in = client.post(
        "/captures/infer",
        data={"capture_id": "e2e-in", "direction": "in"},
        files={"image": IMG},
        headers=staff_headers,
    )
    assert r_in.status_code == 200, r_in.text
    cap_in = r_in.json()
    in_reading = cap_in["reading_id"]
    assert cap_in["vehicle_type"] == "car"
    assert cap_in["color"] == "white"

    # 2. Nhân viên sửa tay loại xe + màu biển (không đổi biển số).
    patch = client.patch(
        f"/readings/{in_reading}/plate",
        json={"vehicle_type": "truck", "color": "yellow"},
        headers=staff_headers,
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["review_state"] == "manual"
    assert patch.json()["vehicle_type"] == "truck"
    assert patch.json()["color"] == "yellow"

    # 3. Xác nhận VÀO: nhóm phí suy từ truck = xe_tai, mang theo màu vàng.
    entry = client.post("/sessions/entry", json={"reading_id": in_reading}, headers=staff_headers)
    assert entry.status_code == 200, entry.text
    sid = entry.json()["id"]
    assert entry.json()["status"] == "in_lot"
    assert entry.json()["vehicle_group"] == "xe_tai"
    assert entry.json()["color"] == "yellow"

    # 4. RA: chụp cùng biển -> khớp phiên theo plate_hash, tính phí flat.
    r_out = client.post(
        "/captures/infer",
        data={"capture_id": "e2e-out", "direction": "out"},
        files={"image": IMG},
        headers=staff_headers,
    )
    assert r_out.status_code == 200, r_out.text
    out_reading = r_out.json()["reading_id"]

    exit_ = client.post("/sessions/exit", json={"reading_id": out_reading}, headers=staff_headers)
    assert exit_.status_code == 200, exit_.text
    xb = exit_.json()
    assert xb["outcome"] == "completed"
    assert xb["session"]["id"] == sid
    assert xb["session"]["fee_amount"] == 5000

    # 5. Thu tiền.
    pay = client.post(
        "/payments",
        json={"session_id": sid, "amount": 5000, "method": "cash", "kind": "payment"},
        headers=staff_headers,
    )
    assert pay.status_code == 201, pay.text

    # 6. Chi tiết phiên: phản ánh sửa tay + phí + thanh toán.
    detail = client.get(f"/sessions/{sid}", headers=staff_headers)
    assert detail.status_code == 200, detail.text
    d = detail.json()
    assert d["status"] == "completed"
    assert d["vehicle_type"] == "truck"
    assert d["color"] == "yellow"
    assert d["vehicle_group"] == "xe_tai"
    assert d["fee_amount"] == 5000
    assert len(d["payments"]) == 1
    assert d["payments"][0]["method"] == "cash"


def test_patch_session_updates_type_and_color(client, staff_headers):
    r_in = client.post(
        "/captures/infer",
        data={"capture_id": "e2e-patch", "direction": "in"},
        files={"image": IMG},
        headers=staff_headers,
    )
    assert r_in.status_code == 200, r_in.text
    entry = client.post("/sessions/entry", json={"reading_id": r_in.json()["reading_id"]}, headers=staff_headers)
    assert entry.status_code == 200, entry.text
    sid = entry.json()["id"]

    patch = client.patch(f"/sessions/{sid}", json={"vehicle_type": "bus", "color": "blue"}, headers=staff_headers)
    assert patch.status_code == 200, patch.text
    assert patch.json()["color"] == "blue"

    d = client.get(f"/sessions/{sid}", headers=staff_headers).json()
    assert d["vehicle_type"] == "bus"
    assert d["color"] == "blue"


def test_patch_session_not_found(client, staff_headers):
    r = client.patch("/sessions/999999", json={"color": "blue"}, headers=staff_headers)
    assert r.status_code == 404


def test_gate_entry_manual_group_override_via_api(client, db_session, staff_headers):
    # Sửa tay nhóm phí ở màn VÀO: ghi đè suy luận từ loại xe.
    r_in = client.post(
        "/captures/infer",
        data={"capture_id": "e2e-ovr", "direction": "in"},
        files={"image": IMG},
        headers=staff_headers,
    )
    assert r_in.status_code == 200, r_in.text
    in_reading = r_in.json()["reading_id"]  # car -> suy luận o_to_con

    entry = client.post(
        "/sessions/entry",
        json={"reading_id": in_reading, "vehicle_group": "xe_may"},
        headers=staff_headers,
    )
    assert entry.status_code == 200, entry.text
    assert entry.json()["vehicle_group"] == "xe_may"
