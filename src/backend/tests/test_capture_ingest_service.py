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

    resp = build_capture_response(db_session, reading, plate_text, duplicate)
    assert resp.plate_text == "51F12345"
    assert resp.vehicle_group == "o_to_con"
    assert resp.duplicate is False
    assert resp.ocr_conf == 0.95
    assert resp.color_conf == 0.9
    # Ảnh chính luôn có 1 dòng ReadingImage tương ứng (is_primary), kể cả khi
    # làn chỉ có 1 camera — để truy vấn danh sách ảnh của 1 reading luôn nhất quán.
    assert len(resp.images) == 1
    assert resp.images[0].is_primary is True
    assert resp.images[0].image_asset_id == resp.image_asset_id


def test_ingest_stores_extra_camera_images(db_session):
    """Làn 2 camera (trước + sau xe): ảnh cam phụ phải lưu thật, không bị vứt."""
    from app.models import ImageAsset, ReadingImage
    from app.services.capture_ingest import build_capture_response, ingest_reading

    reading, _, _ = ingest_reading(
        db_session, capture_id="cap-multi-1", direction="in", lane="lane1",
        payload=_payload(), image_bytes=b"front-frame",
        primary_role="front", extra_images=[(b"rear-frame", "rear")],
    )

    rows = db_session.query(ReadingImage).filter_by(reading_id=reading.id).order_by(ReadingImage.id).all()
    assert [(r.role, r.is_primary) for r in rows] == [("front", True), ("rear", False)]
    # Ảnh phụ phải là 1 ImageAsset THẬT KHÁC với ảnh chính, không phải trỏ lại
    # cùng 1 bản ghi — nếu không sẽ không lưu được đủ 2 ảnh như yêu cầu.
    assert rows[1].image_asset_id != rows[0].image_asset_id
    assert db_session.get(ImageAsset, rows[1].image_asset_id) is not None

    resp = build_capture_response(db_session, reading, "51F12345", False)
    assert len(resp.images) == 2
    assert resp.image_asset_id == rows[0].image_asset_id  # ảnh chính không đổi vị trí cũ


def test_ingest_rejects_mismatched_extra_roles(client, staff_headers):
    """API phải từ chối rõ ràng khi số ảnh phụ và số vai trò lệch nhau, không đoán."""
    r = client.post(
        "/captures/infer",
        data={"capture_id": "cap-multi-2", "direction": "in", "extra_roles": []},
        files={
            "image": ("front.jpg", b"front", "image/jpeg"),
            "extra_images": ("rear.jpg", b"rear", "image/jpeg"),
        },
        headers=staff_headers,
    )
    assert r.status_code == 422


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
    resp = build_capture_response(db_session, reading, "51F12345", False)
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
