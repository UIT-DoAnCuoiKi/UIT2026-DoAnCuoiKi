from app.schemas.capture import CaptureResponse, PipelinePayload


def test_plate_item_accepts_crop_b64():
    p = PipelinePayload.model_validate(
        {"vehicle_type": "car",
         "plates": [{"det_conf": 0.9, "plate_text": "51F1", "crop_proc_b64": "QUJD"}]}
    )
    assert p.plates[0].crop_proc_b64 == "QUJD"


def test_capture_response_has_plate_crop_asset_id():
    r = CaptureResponse(reading_id=1, capture_id="c", direction="in",
                        review_state="confident", plate_crop_asset_id=7)
    assert r.plate_crop_asset_id == 7
