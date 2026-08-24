def test_default_config_does_not_select_ml():
    from app.config import settings
    from app.services.inference import FakeInferenceEngine, get_inference_engine
    assert settings.inference_engine == "fake"
    assert isinstance(get_inference_engine(), FakeInferenceEngine)


def test_map_result_dict_to_payload():
    # ánh xạ thuần, không cần model: dict kết quả pipeline hợp lệ thành PipelinePayload
    from app.services.ml_inference import result_to_payload
    result = {
        "file": "x.jpg", "vehicle_type": "car", "vehicle_box": [1, 2, 3, 4],
        "vehicle_style": "sedan", "vehicle_style_conf": 0.8,
        "plates": [{"bbox": [0, 0, 5, 5], "layout": "1", "det_conf": 0.7,
                    "plate_text": "51F999", "plate_valid": True, "ocr_conf": 0.85,
                    "color": "white", "color_conf": 0.9}],
    }
    payload = result_to_payload(result)
    assert payload.vehicle_type == "car"
    assert payload.vehicle_style == "sedan"
    assert payload.plates[0].plate_text == "51F999"
    assert payload.plates[0].color == "white"
