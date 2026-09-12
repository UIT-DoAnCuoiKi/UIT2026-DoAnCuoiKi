"""recognition_mode="best_of": làn 2 camera, chạy nhận dạng cả 2, lấy ảnh có
ocr_conf cao hơn làm ảnh chính — vì 1 camera có thể bị khuất/lóa mà camera còn
lại vẫn đọc được. Trước đây chỉ 1 ảnh/lượt, không có gì để so sánh.
"""
from app.schemas.capture import PipelinePayload, PlateItem
from app.services.inference import get_inference_engine


class _ByBytesEngine:
    """Fake engine trả payload khác nhau tuỳ nội dung ảnh — để mô phỏng 1 camera
    đọc tốt hơn camera kia, khác `FakeInferenceEngine` (luôn trả 1 payload cố định)."""

    def __init__(self, mapping: dict[bytes, PipelinePayload]) -> None:
        self._mapping = mapping

    def infer(self, image_bytes: bytes, options=None) -> PipelinePayload:
        return self._mapping[image_bytes]


def _payload(plate: str, conf: float) -> PipelinePayload:
    return PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(bbox=[0, 0, 10, 10], layout="1", det_conf=0.9,
                          plate_text=plate, plate_valid=True, ocr_conf=conf,
                          color="white", color_conf=0.9)],
    )


def _make_lane(client, headers, mode: str) -> str:
    r = client.post("/lanes", json={"name": "lane-bestof", "recognition_mode": mode}, headers=headers)
    assert r.status_code == 201, r.text
    return "lane-bestof"


def test_best_of_picks_the_more_confident_image(client, db_session, staff_headers, admin_headers):
    lane = _make_lane(client, admin_headers, "best_of")
    front, rear = b"front-bytes", b"rear-bytes"
    engine = _ByBytesEngine({
        front: _payload("51F00001", 0.60),  # ảnh chính đọc kém
        rear: _payload("51F00002", 0.95),   # ảnh phụ đọc tốt hơn hẳn
    })
    client.app.dependency_overrides[get_inference_engine] = lambda: engine

    resp = client.post(
        "/captures/infer",
        data={"capture_id": "bestof-1", "direction": "in", "lane": lane,
              "primary_role": "front", "extra_roles": ["rear"]},
        files={
            "image": ("front.jpg", front, "image/jpeg"),
            "extra_images": ("rear.jpg", rear, "image/jpeg"),
        },
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Ảnh phụ (rear) thắng nên biển đọc được phải là của rear, không phải front.
    assert body["plate_text"] == "51F00002"
    # Nhưng cả 2 ảnh vẫn phải được lưu lại đầy đủ, chỉ đổi vai trò ai là chính.
    assert len(body["images"]) == 2
    roles = {img["role"]: img["is_primary"] for img in body["images"]}
    assert roles == {"rear": True, "front": False}


def test_best_of_keeps_primary_when_it_is_already_better(client, staff_headers, admin_headers):
    lane = _make_lane(client, admin_headers, "best_of")
    front, rear = b"front-bytes-2", b"rear-bytes-2"
    engine = _ByBytesEngine({
        front: _payload("51F00003", 0.95),
        rear: _payload("51F00004", 0.50),
    })
    client.app.dependency_overrides[get_inference_engine] = lambda: engine

    resp = client.post(
        "/captures/infer",
        data={"capture_id": "bestof-2", "direction": "in", "lane": lane,
              "primary_role": "front", "extra_roles": ["rear"]},
        files={
            "image": ("front.jpg", front, "image/jpeg"),
            "extra_images": ("rear.jpg", rear, "image/jpeg"),
        },
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["plate_text"] == "51F00003"


def test_primary_mode_only_recognizes_the_main_image(client, staff_headers, admin_headers):
    """Mặc định (primary): ảnh phụ chỉ lưu bằng chứng, không chạy nhận dạng lại —
    dù ảnh phụ có "đọc được" tốt hơn cũng không được dùng, đúng ý đồ cấu hình."""
    lane_r = client.post("/lanes", json={"name": "lane-primary"}, headers=admin_headers)
    lane = lane_r.json()["name"]
    front, rear = b"front-bytes-3", b"rear-bytes-3"
    engine = _ByBytesEngine({
        front: _payload("51F00005", 0.50),
        rear: _payload("51F00006", 0.99),
    })
    client.app.dependency_overrides[get_inference_engine] = lambda: engine

    resp = client.post(
        "/captures/infer",
        data={"capture_id": "primary-1", "direction": "in", "lane": lane,
              "primary_role": "front", "extra_roles": ["rear"]},
        files={
            "image": ("front.jpg", front, "image/jpeg"),
            "extra_images": ("rear.jpg", rear, "image/jpeg"),
        },
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["plate_text"] == "51F00005"
