"""Công tắc ở màn Cấu hình phải THỰC SỰ tắt bước tính, không chỉ ẩn kết quả.

Lỗi đã gặp thật: `read_plate`, `plate_color`, `vehicle_class` được lưu vào DB và
hiện ra ở màn Cấu hình, nhưng không có chỗ nào trong đường suy luận hỏi tới, nên
tắt đi rồi chụp vẫn thấy màu biển và loại xe như thường. Trên thiết bị biên đây
còn là đòn bẩy hiệu năng (đo trên Raspberry Pi 5: tắt vehicle_class bỏ được
khoảng 260ms trong tổng 490ms mỗi lượt), nên để nó trang trí là mất thật.
"""
import io

import pytest

from app.services.inference import InferenceOptions


def _toggle(client, headers, **flags):
    r = client.patch("/feature-toggles", json=flags, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _capture(client, headers, capture_id: str):
    return client.post(
        "/captures/infer",
        data={"capture_id": capture_id, "direction": "in"},
        files={"image": ("x.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        headers=headers,
    )


def test_tat_plate_color_thi_khong_tra_ve_mau(client, admin_headers):
    _toggle(client, admin_headers, plate_color=False)
    r = _capture(client, admin_headers, "cap-no-color")
    assert r.status_code == 200, r.text
    assert r.json()["color"] is None


def test_tat_vehicle_class_thi_khong_tra_ve_loai_xe(client, admin_headers):
    _toggle(client, admin_headers, vehicle_class=False)
    r = _capture(client, admin_headers, "cap-no-class")
    assert r.status_code == 200, r.text
    assert r.json()["vehicle_type"] is None


def test_tat_read_plate_thi_khong_doc_bien(client, admin_headers):
    _toggle(client, admin_headers, read_plate=False)
    r = _capture(client, admin_headers, "cap-no-ocr")
    assert r.status_code == 200, r.text
    body = r.json()
    assert not body["plate_text"]
    assert body["plate_valid"] is not True


def test_bat_lai_thi_co_du_ket_qua(client, admin_headers):
    _toggle(client, admin_headers, read_plate=True, plate_color=True, vehicle_class=True)
    r = _capture(client, admin_headers, "cap-all-on")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plate_text"]
    assert body["color"] is not None
    assert body["vehicle_type"] is not None


def test_dev_mode_bat_thi_tra_ve_thoi_gian_tung_giai_doan(client, admin_headers):
    _toggle(client, admin_headers, dev_mode=True)
    r = _capture(client, admin_headers, "cap-timings-on")
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["timings_ms"], dict)


def test_dev_mode_tat_thi_khong_tra_thoi_gian(client, admin_headers):
    _toggle(client, admin_headers, dev_mode=False)
    r = _capture(client, admin_headers, "cap-timings-off")
    assert r.status_code == 200, r.text
    assert r.json()["timings_ms"] is None


def test_su_kien_websocket_mang_theo_thoi_gian_va_tai_nguyen(client, admin_headers, monkeypatch):
    """Lỗi đã gặp thật: màn Trạm cổng nhận kết quả của CÙNG một lượt chụp qua hai
    đường (phản hồi HTTP và sự kiện WebSocket), đường nào tới sau thì ghi đè state.
    Payload WS thiếu timings nên nó xoá mất số đo mà HTTP vừa trả, người dùng thấy
    bảng thời gian không bao giờ hiện dù đã bật dev_mode và chụp lại."""
    from app.services import capture_ingest

    published: list[dict] = []
    monkeypatch.setattr(capture_ingest.gate_hub, "publish", published.append)

    _toggle(client, admin_headers, dev_mode=True)
    assert _capture(client, admin_headers, "cap-ws-timings").status_code == 200

    assert published, "không có sự kiện WS nào được phát"
    evt = published[-1]
    assert "timings_ms" in evt and evt["timings_ms"] is not None
    assert "resources" in evt


@pytest.mark.parametrize(
    "flag,field",
    [("read_plate", "plate_text"), ("plate_color", "color"), ("vehicle_class", "vehicle_type")],
)
def test_engine_gia_cung_ton_trong_cong_tac(flag, field):
    """Engine giả phải hành xử giống engine thật, nếu không thì test và demo
    bằng engine giả sẽ không phản ánh đúng cái người dùng gặp."""
    from app.services.inference import FakeInferenceEngine

    payload = FakeInferenceEngine().infer(b"x", InferenceOptions(**{flag: False}))
    if field == "vehicle_type":
        assert payload.vehicle_type is None
    elif field == "color":
        assert all(p.color is None for p in payload.plates)
    else:
        assert all(not p.plate_text for p in payload.plates)
