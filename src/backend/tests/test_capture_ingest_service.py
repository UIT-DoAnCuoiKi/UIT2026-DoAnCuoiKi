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
