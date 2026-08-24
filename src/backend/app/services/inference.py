from typing import Protocol

from app.config import settings
from app.schemas.capture import PipelinePayload, PlateItem


class InferenceEngine(Protocol):
    def infer(self, image_bytes: bytes) -> PipelinePayload: ...


def _default_payload() -> PipelinePayload:
    return PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(
            bbox=[0, 0, 10, 10], layout="1", det_conf=0.9,
            plate_text="51F12345", plate_valid=True, ocr_conf=0.95,
            color="white", color_conf=0.9,
        )],
    )


class FakeInferenceEngine:
    def __init__(self, payload: PipelinePayload | None = None) -> None:
        self._payload = payload or _default_payload()

    def infer(self, image_bytes: bytes) -> PipelinePayload:
        return self._payload


def get_inference_engine() -> InferenceEngine:
    if settings.inference_engine == "ml":
        from app.services.ml_inference import get_ml_engine
        return get_ml_engine()
    return FakeInferenceEngine()
