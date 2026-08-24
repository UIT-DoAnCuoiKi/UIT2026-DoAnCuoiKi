def test_fake_engine_default_payload_is_valid():
    from app.services.inference import FakeInferenceEngine
    payload = FakeInferenceEngine().infer(b"anything")
    assert payload.vehicle_type == "car"
    assert payload.plates[0].plate_text == "51F12345"
    assert payload.plates[0].plate_valid is True


def test_fake_engine_returns_injected_payload():
    from app.schemas.capture import PipelinePayload, PlateItem
    from app.services.inference import FakeInferenceEngine
    custom = PipelinePayload(vehicle_type="motorbike", plates=[PlateItem(plate_text="59X1", plate_valid=False)])
    payload = FakeInferenceEngine(custom).infer(b"x")
    assert payload.vehicle_type == "motorbike"
    assert payload.plates[0].plate_text == "59X1"


def test_provider_defaults_to_fake():
    from app.services.inference import FakeInferenceEngine, get_inference_engine
    assert isinstance(get_inference_engine(), FakeInferenceEngine)
