from dataclasses import dataclass
from typing import Protocol

from app.config import settings
from app.schemas.capture import PipelinePayload, PlateItem


@dataclass(frozen=True)
class InferenceOptions:
    """Cờ bật/tắt từng bước, lấy từ bảng feature_toggle.

    Tắt công tắc ở màn Cấu hình phải THỰC SỰ bỏ bước tính chứ không chỉ ẩn kết
    quả: trên thiết bị biên đây là đòn bẩy hiệu năng (đo trên Raspberry Pi 5,
    tắt vehicle_class bỏ được ~260ms trong tổng ~490ms mỗi lượt).
    """

    read_plate: bool = True
    plate_color: bool = True
    vehicle_class: bool = True
    collect_timings: bool = False


class InferenceEngine(Protocol):
    def infer(self, image_bytes: bytes, options: InferenceOptions | None = None) -> PipelinePayload: ...


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

    def infer(self, image_bytes: bytes, options: InferenceOptions | None = None) -> PipelinePayload:
        opts = options or InferenceOptions()
        p = self._payload.model_copy(deep=True)
        # Tôn trọng công tắc y như engine thật, để test và demo bằng engine giả
        # vẫn thấy đúng hành vi người dùng sẽ gặp.
        if not opts.read_plate:
            for plate in p.plates:
                plate.plate_text, plate.plate_valid, plate.ocr_conf = "", False, 0.0
        if not opts.plate_color:
            for plate in p.plates:
                plate.color, plate.color_conf = None, None
        if not opts.vehicle_class:
            p.vehicle_type = p.vehicle_style = p.vehicle_style_conf = p.vehicle_box = None
        if opts.collect_timings:
            p.timings_ms = {"tong": 0.0}
            p.resources = {"so_loi_dung": 0.0, "cpu_time_ms": 0.0}
        return p


def get_inference_engine() -> InferenceEngine:
    # Chỉ chấp nhận đúng hai engine. Giá trị lạ (gõ nhầm, hoa/thường, dư khoảng
    # trắng) phải báo lỗi rõ, KHÔNG âm thầm rơi về biển giả 51F12345.
    engine = (settings.inference_engine or "").strip().lower()
    if engine == "ml":
        from app.services.ml_inference import get_ml_engine
        return get_ml_engine()
    if engine == "fake":
        return FakeInferenceEngine()
    raise RuntimeError(
        f"INFERENCE_ENGINE không hợp lệ: {settings.inference_engine!r}. "
        "Chỉ chấp nhận 'ml' (model thật) hoặc 'fake' (biển giả cho test)."
    )
