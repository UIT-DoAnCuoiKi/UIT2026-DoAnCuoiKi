"""Smoke + fidelity test cho pipeline ONNX thật (OnnxAlprPipeline).

Chốt rằng runner đóng gói trong backend đọc ĐÚNG biển thật (không phải stub
`51F12345`), khớp đường e2e của notebook `src/ml/notebooks/e2e-pipeline-test.ipynb`.
Cần weights + torch/onnxruntime nên đánh dấu `slow` và `importorskip`, KHÔNG chạy
trong suite mặc định (venv backend không có torch -> tự SKIP). Chạy thật trong
image backend hoặc venv có ML:  pytest -m slow
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_ML_DIR = _REPO / "src" / "ml"
_SAMPLE = _REPO / "docs" / "research" / "assets" / "dataset-samples" / "1_bomaich_detect.png"


@pytest.mark.slow
def test_onnx_pipeline_reads_real_plate():
    cv2 = pytest.importorskip("cv2")
    pytest.importorskip("ultralytics")
    pytest.importorskip("onnxruntime")
    if str(_ML_DIR) not in sys.path:
        sys.path.insert(0, str(_ML_DIR))
    from pipeline.onnx_pipeline import OnnxAlprPipeline

    assert _SAMPLE.exists(), f"thiếu ảnh mẫu commit sẵn: {_SAMPLE}"
    img = cv2.imread(str(_SAMPLE))
    assert img is not None

    w = _ML_DIR / "weights"
    pipe = OnnxAlprPipeline(
        plate_weights=str(w / "plate-detector.pt"),
        ocr_onnx=str(w / "plate-ocr-crnn.onnx"),
        style_onnx=str(w / "vehicle-style-resnet18.onnx"),
        style_classes_path=str(_ML_DIR / "data" / "vehicle-style-classes.json"),
    )
    result = pipe.run(img)

    assert isinstance(result, dict)
    plates = result["plates"]
    assert plates, "detector không đọc được biển nào trên ảnh mẫu"
    texts = [p["plate_text"] for p in plates]
    # Biển ground truth ổn định của model thật trên ảnh này (khớp edge spec 08-31).
    assert "81AA-048.92" in texts, f"đọc sai biển thật, got={texts}"
    assert any(p["plate_valid"] for p in plates)
