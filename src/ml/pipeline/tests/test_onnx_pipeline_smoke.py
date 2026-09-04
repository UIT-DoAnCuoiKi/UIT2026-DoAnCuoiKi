"""Smoke test cho OnnxAlprPipeline: chạy model thật trên một ảnh mẫu đã có trong
repo, kiểm tra `run` trả dict đúng cấu trúc PipelinePayload và đọc được ít nhất
một biển đúng định dạng VN.

Ảnh mẫu `10_duydieu_CLOSE_singlevehicle.png` là ảnh ghép nhiều xe/biển (đã nằm
trong repo, không thêm dữ liệu cá nhân mới). Pipeline đã kiểm cho ra nhiều biển,
trong đó có biển hợp lệ định dạng (vd. 54Z1-3195, 59M1-902.08).

Đánh dấu `slow`: cần weights thật (YOLO .pt + ONNX). Chạy:
  python3 -m pytest src/ml/pipeline/tests -m slow
"""
from pathlib import Path

import cv2
import pytest

from pipeline.onnx_pipeline import OnnxAlprPipeline

REPO_ROOT = Path(__file__).resolve().parents[4]  # tests -> pipeline -> ml -> src -> repo
SAMPLE = REPO_ROOT / "docs" / "research" / "assets" / "dataset-samples" / "10_duydieu_CLOSE_singlevehicle.png"

TOP_KEYS = {"vehicle_type", "vehicle_box", "vehicle_style", "vehicle_style_conf", "plates"}
PLATE_KEYS = {"bbox", "layout", "det_conf", "plate_text", "plate_valid", "ocr_conf", "color", "color_conf"}


@pytest.mark.slow
def test_run_returns_wellformed_dict_with_valid_plate():
    img_bgr = cv2.imread(str(SAMPLE))
    assert img_bgr is not None, f"không đọc được ảnh mẫu: {SAMPLE}"

    pipeline = OnnxAlprPipeline()
    result = pipeline.run(img_bgr)

    assert set(result.keys()) == TOP_KEYS
    assert isinstance(result["plates"], list)
    assert result["plates"], "không phát hiện được biển nào trên ảnh mẫu"
    for plate in result["plates"]:
        assert set(plate.keys()) == PLATE_KEYS
        assert isinstance(plate["plate_text"], str)
        assert isinstance(plate["plate_valid"], bool)
    assert any(p["plate_valid"] for p in result["plates"]), "không có biển nào đúng định dạng VN"
