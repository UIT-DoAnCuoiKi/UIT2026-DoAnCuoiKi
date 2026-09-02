from app.schemas.capture import PipelinePayload, PlateItem


def _payload():
    return PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(bbox=[0, 0, 10, 10], layout="1", det_conf=0.9,
                          plate_text="51F12345", plate_valid=True, ocr_conf=0.95,
                          color="white", color_conf=0.9)],
    )


def test_ingest_creates_reading_and_response(db_session):
    from app.services.capture_ingest import build_capture_response, ingest_reading
    reading, plate_text, duplicate = ingest_reading(
        db_session, capture_id="cap-1", direction="in", lane="lane1",
        payload=_payload(), image_bytes=b"jpegbytes",
    )
    assert duplicate is False
    assert plate_text == "51F12345"
    assert reading.review_state == "confident"
    assert reading.color == "white"
    assert reading.vehicle_type == "car"

    resp = build_capture_response(reading, plate_text, duplicate)
    assert resp.plate_text == "51F12345"
    assert resp.vehicle_group == "o_to_con"
    assert resp.duplicate is False
    assert resp.ocr_conf == 0.95
    assert resp.color_conf == 0.9


def test_ingest_is_idempotent_on_capture_id(db_session):
    from app.services.capture_ingest import ingest_reading
    first, _, dup1 = ingest_reading(
        db_session, capture_id="cap-2", direction="in", lane=None,
        payload=_payload(), image_bytes=b"x")
    second, text2, dup2 = ingest_reading(
        db_session, capture_id="cap-2", direction="in", lane=None,
        payload=_payload(), image_bytes=b"x")
    assert dup1 is False and dup2 is True
    assert second.id == first.id
    assert text2 == "51F12345"


# Valid 1x1 PNG (bytes content is irrelevant to storage; must be valid base64).
_CROP_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _payload_with_crop():
    return PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(bbox=[0, 0, 10, 10], layout="1", det_conf=0.9,
                          plate_text="51F12345", plate_valid=True, ocr_conf=0.95,
                          color="white", color_conf=0.9, crop_proc_b64=_CROP_B64)],
    )


def test_ingest_persists_plate_crop_asset(db_session):
    from app.models import ImageAsset
    from app.services.capture_ingest import build_capture_response, ingest_reading
    reading, _, _ = ingest_reading(
        db_session, capture_id="cap-crop-1", direction="in", lane=None,
        payload=_payload_with_crop(), image_bytes=b"frame",
    )
    assert reading.plate_crop_asset_id is not None
    assert reading.plate_crop_asset_id != reading.image_asset_id
    assert db_session.get(ImageAsset, reading.plate_crop_asset_id) is not None
    # crop bytes must not be duplicated into the JSON column
    for p in reading.raw_pipeline_json["plates"]:
        assert "crop_proc_b64" not in p
    resp = build_capture_response(reading, "51F12345", False)
    assert resp.plate_crop_asset_id == reading.plate_crop_asset_id


def test_ingest_without_crop_leaves_asset_null(db_session):
    from app.services.capture_ingest import ingest_reading
    reading, _, _ = ingest_reading(
        db_session, capture_id="cap-crop-2", direction="in", lane=None,
        payload=_payload(), image_bytes=b"frame",
    )
    assert reading.plate_crop_asset_id is None


def test_ingest_publishes_plate_crop_asset_id(db_session, monkeypatch):
    from app.services import capture_ingest
    published = {}
    monkeypatch.setattr(capture_ingest.gate_hub, "publish", lambda evt: published.update(evt))
    reading, _, _ = capture_ingest.ingest_reading(
        db_session, capture_id="cap-crop-3", direction="in", lane=None,
        payload=_payload_with_crop(), image_bytes=b"frame",
    )
    assert published["plate_crop_asset_id"] == reading.plate_crop_asset_id


def test_ingest_tolerates_malformed_crop_b64(db_session):
    from app.services.capture_ingest import ingest_reading
    payload = PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(det_conf=0.9, plate_text="51F1", plate_valid=True,
                          crop_proc_b64="!!!not base64!!!")],
    )
    reading, _, _ = ingest_reading(
        db_session, capture_id="cap-crop-bad", direction="in", lane=None,
        payload=payload, image_bytes=b"frame",
    )
    assert reading.id is not None
    assert reading.plate_crop_asset_id is None
