from app.schemas.capture import PipelinePayload, PlateItem
from app.services.inference import FakeInferenceEngine, get_inference_engine


def test_kiosk_photo_to_reading_end_to_end(client, staff_headers):
    # engine giả trả một xe máy biển hợp lệ màu trắng
    payload = PipelinePayload(
        vehicle_type="motorbike",
        plates=[PlateItem(bbox=[0, 0, 8, 8], layout="2", det_conf=0.8,
                          plate_text="59X12345", plate_valid=True, ocr_conf=0.9,
                          color="white", color_conf=0.88)],
    )
    client.app.dependency_overrides[get_inference_engine] = lambda: FakeInferenceEngine(payload)

    resp = client.post(
        "/captures/infer",
        data={"capture_id": "acc-1", "direction": "in", "lane": "cong-1"},
        files={"image": ("shot.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate_text"] == "59X12345"
    assert body["vehicle_type"] == "motorbike"
    assert body["vehicle_group"] == "xe_may"
    assert body["color"] == "white"
    assert body["review_state"] == "confident"
    assert body["reading_id"] is not None

    # lượt đọc xuất hiện ở /captures/latest cho lane đó
    latest = client.get("/captures/latest?lane=cong-1").json()
    assert latest["plate_text"] == "59X12345"
    assert latest["vehicle_group"] == "xe_may"
