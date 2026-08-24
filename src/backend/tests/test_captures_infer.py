from app.schemas.capture import PipelinePayload, PlateItem
from app.services.inference import FakeInferenceEngine, get_inference_engine


def _override_engine(client, payload=None):
    client.app.dependency_overrides[get_inference_engine] = lambda: FakeInferenceEngine(payload)


def test_infer_creates_reading_from_image(client, staff_headers):
    _override_engine(client)
    resp = client.post(
        "/captures/infer",
        data={"capture_id": "infer-1", "direction": "in", "lane": "lane1"},
        files={"image": ("frame.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate_text"] == "51F12345"
    assert body["color"] == "white"
    assert body["vehicle_type"] == "car"
    assert body["vehicle_group"] == "o_to_con"
    assert body["review_state"] == "confident"
    assert body["duplicate"] is False


def test_infer_is_idempotent(client, staff_headers):
    _override_engine(client)
    args = dict(
        data={"capture_id": "infer-2", "direction": "in"},
        files={"image": ("f.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    first = client.post("/captures/infer", **args).json()
    second = client.post("/captures/infer", **args).json()
    assert first["reading_id"] == second["reading_id"]
    assert second["duplicate"] is True


def test_infer_requires_auth(client):
    _override_engine(client)
    resp = client.post(
        "/captures/infer",
        data={"capture_id": "infer-3", "direction": "in"},
        files={"image": ("f.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
    )
    assert resp.status_code in (401, 403)


def test_infer_rejects_bad_direction(client, staff_headers):
    _override_engine(client)
    resp = client.post(
        "/captures/infer",
        data={"capture_id": "infer-4", "direction": "sideways"},
        files={"image": ("f.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    assert resp.status_code == 422
