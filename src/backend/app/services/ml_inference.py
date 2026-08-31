"""Adapter suy luận thật (ONNX) cho backend. Bọc `OnnxAlprPipeline` ở
`src/ml/pipeline/onnx_pipeline.py` (nguồn sự thật dùng chung với edge worker):
giải mã ảnh thô upload từ màn Trạm cổng, chạy pipeline, ánh xạ dict kết quả sang
`PipelinePayload`.

Runner chạy 3 model đã huấn luyện ở src/ml: detector YOLO (.pt) qua ultralytics,
OCR CRNN (.onnx) và classifier kiểu dáng (.onnx) qua onnxruntime. Logic suy luận
nằm trong `onnx_pipeline`; adapter này chỉ lo phần backend (bytes -> BGR -> dict
-> PipelinePayload) và cache engine theo tiến trình.

Các import nặng (cv2, cây src/ml, runner) nằm trong hàm để suite test backend
(không có model, không có torch) vẫn import được module. Chọn adapter bằng
INFERENCE_ENGINE=ml. Đường dẫn model mặc định trỏ vào repo (giải trong
onnx_pipeline), ghi đè bằng biến môi trường ML_PLATE_WEIGHTS, ML_OCR_ONNX,
ML_STYLE_ONNX, ML_STYLE_CLASSES.
"""
import os
import sys
from pathlib import Path

from app.schemas.capture import PipelinePayload

# Cây src/ml suy từ vị trí file: .../src/backend/app/services/ml_inference.py
_ML_DIR = Path(__file__).resolve().parents[3] / "ml"


def result_to_payload(result: dict) -> PipelinePayload:
    """Ánh xạ dict kết quả `OnnxAlprPipeline.run` thành PipelinePayload. Dict đã
    trùng field với PipelinePayload/PlateItem; khóa thừa (vd. `file`) được pydantic
    bỏ qua."""
    return PipelinePayload.model_validate(result)


class MlInferenceEngine:
    """Bọc runner: bytes ảnh -> BGR -> `pipeline.run(dict)` -> PipelinePayload."""

    def __init__(self, pipeline) -> None:
        self._pipeline = pipeline

    def infer(self, image_bytes: bytes) -> PipelinePayload:
        import cv2
        import numpy as np

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return PipelinePayload(vehicle_type=None, plates=[])
        return result_to_payload(self._pipeline.run(img_bgr))


_engine: "MlInferenceEngine | None" = None


def get_ml_engine() -> "MlInferenceEngine":
    """Nạp runner một lần (cache tiến trình). Đường dẫn mặc định trỏ vào repo,
    ghi đè bằng ML_PLATE_WEIGHTS, ML_OCR_ONNX, ML_STYLE_ONNX, ML_STYLE_CLASSES."""
    global _engine
    if _engine is not None:
        return _engine

    # src/ml lên sys.path để import runner; runner tự thêm các gói con khi khởi tạo.
    if str(_ML_DIR) not in sys.path:
        sys.path.insert(0, str(_ML_DIR))

    from pipeline.onnx_pipeline import OnnxAlprPipeline

    pipeline = OnnxAlprPipeline(
        plate_weights=os.environ.get("ML_PLATE_WEIGHTS"),
        ocr_onnx=os.environ.get("ML_OCR_ONNX"),
        style_onnx=os.environ.get("ML_STYLE_ONNX"),
        style_classes_path=os.environ.get("ML_STYLE_CLASSES"),
    )
    _engine = MlInferenceEngine(pipeline)
    return _engine
