"""Adapter suy luận thật cho runtime edge. Bọc pipeline src/ml.

Phụ thuộc torch, opencv, và cây src/ml; các import nặng nằm trong hàm để
suite test backend (không có model) vẫn import được module cho phần ánh xạ
thuần. Chọn adapter bằng biến môi trường INFERENCE_ENGINE=ml cộng các đường
dẫn model dưới đây.
"""
import os
import tempfile

from app.schemas.capture import PipelinePayload


def result_to_payload(result: dict) -> PipelinePayload:
    """Ánh xạ dict kết quả run_pipeline_on_image thành PipelinePayload.

    Dict đã trùng field với PipelinePayload và PlateItem; khóa thừa (file)
    được pydantic bỏ qua.
    """
    return PipelinePayload.model_validate(result)


class MlInferenceEngine:
    def __init__(self, plate_detector, ocr_recognizer, style_model, style_classes, style_transform, device: str):
        self._plate_detector = plate_detector
        self._ocr = ocr_recognizer
        self._style_model = style_model
        self._style_classes = style_classes
        self._style_transform = style_transform
        self._device = device

    def infer(self, image_bytes: bytes) -> PipelinePayload:
        from pathlib import Path

        from e2e_pipeline_test import run_pipeline_on_image  # cây src/ml trên PYTHONPATH

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
            tmp.write(image_bytes)
            tmp.flush()
            result, _img = run_pipeline_on_image(
                Path(tmp.name), self._plate_detector, self._ocr,
                self._style_model, self._style_classes, self._style_transform, self._device,
            )
        return result_to_payload(result)


_engine: "MlInferenceEngine | None" = None


def get_ml_engine() -> "MlInferenceEngine":
    """Nạp model một lần. Đường dẫn model lấy từ biến môi trường:
    ML_STYLE_MODEL, ML_STYLE_CLASSES, ML_PLATE_WEIGHTS, ML_OCR_WEIGHTS, ML_DEVICE.
    """
    global _engine
    if _engine is not None:
        return _engine

    import json

    import torch  # noqa: F401  xác nhận runtime có torch

    from classifier import build_transforms
    from pipeline.ocr import CRNNRecognizer
    from plate_detect.inference.plate_detector import PlateDetector
    from predict_vehicle import load_style_model

    device = os.environ.get("ML_DEVICE", "cpu")
    style_classes = json.loads(os.environ["ML_STYLE_CLASSES"]) if os.environ.get("ML_STYLE_CLASSES") else []
    if os.environ.get("ML_STYLE_CLASSES", "").endswith(".json"):
        with open(os.environ["ML_STYLE_CLASSES"], encoding="utf-8") as fh:
            style_classes = json.load(fh)
    style_model = load_style_model(os.environ["ML_STYLE_MODEL"], device)
    style_transform = build_transforms(train=False)
    plate_detector = PlateDetector(os.environ["ML_PLATE_WEIGHTS"])
    ocr = CRNNRecognizer(os.environ["ML_OCR_WEIGHTS"], device=device)

    _engine = MlInferenceEngine(plate_detector, ocr, style_model, style_classes, style_transform, device)
    return _engine
