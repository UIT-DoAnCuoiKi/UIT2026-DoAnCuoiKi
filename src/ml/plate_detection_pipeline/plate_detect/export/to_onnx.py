from __future__ import annotations
import numpy as np


def _center(d):
    x1, y1, x2, y2 = d.bbox_xyxy
    return np.array([(x1 + x2) / 2, (y1 + y2) / 2], float)


def detection_delta(a, b) -> float:
    delta = float(abs(len(a) - len(b)))
    n = min(len(a), len(b))
    if n:
        a_s = sorted(a, key=lambda d: d.conf, reverse=True)
        b_s = sorted(b, key=lambda d: d.conf, reverse=True)
        dists = [np.linalg.norm(_center(a_s[i]) - _center(b_s[i])) for i in range(n)]
        delta += float(np.mean(dists)) / 1000.0
    return delta


def parity_ok(a, b, tol: float = 0.02) -> bool:
    return detection_delta(a, b) <= tol


def export(weights_pt: str, out_onnx: str, imgsz: int = 640) -> str:
    from ultralytics import YOLO
    import shutil
    model = YOLO(weights_pt)
    produced = model.export(format="onnx", imgsz=imgsz, opset=12)
    if produced is None:
        raise RuntimeError("Ultralytics export returned None; check weights path / format")
    if str(produced) != out_onnx:
        shutil.copy(str(produced), out_onnx)
    return out_onnx
