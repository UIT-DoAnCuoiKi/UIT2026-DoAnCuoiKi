"""Đưa các gói con của src/ml lên sys.path để test import được
`pipeline.onnx_pipeline` và các phụ thuộc (plate_detect, plate_color, training)."""
import sys
from pathlib import Path

ML_DIR = Path(__file__).resolve().parents[2]  # src/ml/pipeline/tests -> src/ml

for _p in (
    ML_DIR,                                 # pipeline/, predict_vehicle.py
    ML_DIR / "training",                    # ocr_model.py, classifier.py
    ML_DIR / "plate_detection_pipeline",    # gói plate_detect
    ML_DIR / "plate_color_pipeline",        # gói plate_color
):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
