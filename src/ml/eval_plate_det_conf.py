"""Đo độ tin (conf) của detector biển trên val A1 để chọn ngưỡng loại hộp "không phải biển".

Hộp có IoU >= 0,5 với biển thật trong nhãn là đúng, còn lại là nhầm. Detector chạy ở
conf 0,05 để thấy hết hộp, rồi mỗi ngưỡng báo tỉ lệ biển thật còn giữ và số hộp nhầm còn lọt.

Chạy: .venv/Scripts/python.exe src/ml/eval_plate_det_conf.py [weights]
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "plate_detection_pipeline"))

from plate_detect.inference.plate_detector import PlateDetector  # noqa: E402

A1_DIR = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment"
DEFAULT_WEIGHTS = REPO_ROOT / "src" / "ml" / "plate_detection_pipeline" / "weights" / "yolov8n_a1_640.onnx"
THRESHOLDS = (0.25, 0.4, 0.5, 0.6, 0.7, 0.8)


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def gt_boxes(label_path: Path, w: int, h: int) -> list[tuple[float, float, float, float]]:
    boxes = []
    for line in label_path.read_text(encoding="utf-8").strip().splitlines():
        parts = line.split()
        if len(parts) < 9:
            continue
        pts = np.array([float(v) for v in parts[1:]], dtype=float).reshape(-1, 2)
        xs, ys = pts[:, 0] * w, pts[:, 1] * h
        boxes.append((xs.min(), ys.min(), xs.max(), ys.max()))
    return boxes


def main() -> None:
    weights = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_WEIGHTS
    backend = "onnx" if weights.suffix == ".onnx" else "pt"
    det = PlateDetector(str(weights), backend=backend, conf=0.05)

    tp_conf, fp_conf, n_gt = [], [], 0
    img_dir, lbl_dir = A1_DIR / "images" / "val", A1_DIR / "labels" / "val"
    for lp in sorted(lbl_dir.glob("*.txt")):
        ip = next((img_dir / (lp.stem + e) for e in (".jpg", ".jpeg", ".png") if (img_dir / (lp.stem + e)).exists()), None)
        img = cv2.imread(str(ip)) if ip else None
        if img is None:
            continue
        gts = gt_boxes(lp, img.shape[1], img.shape[0])
        n_gt += len(gts)
        matched: set[int] = set()
        for d in det.detect(img):  # conf giảm dần, hộp tốt nhất ghép trước
            best = max(range(len(gts)), key=lambda i: iou(d.bbox_xyxy, gts[i]), default=None)
            if best is not None and best not in matched and iou(d.bbox_xyxy, gts[best]) >= 0.5:
                matched.add(best)
                tp_conf.append(d.conf)
            else:
                fp_conf.append(d.conf)

    tp, fp = np.array(tp_conf), np.array(fp_conf)
    print(f"weights: {weights.name} | biển thật: {n_gt} | hộp đúng: {len(tp)} | hộp nhầm (conf>=0,05): {len(fp)}")
    print("conf của biển thật: phân vị 1/5/10/50 = " + " / ".join(f"{np.percentile(tp, q):.2f}" for q in (1, 5, 10, 50)))
    print(f"\n{'ngưỡng':>7} | {'giữ biển thật':>14} | {'hộp nhầm còn lọt':>17}")
    for t in THRESHOLDS:
        print(f"{t:>7.2f} | {100 * (tp >= t).sum() / n_gt:>13.1f}% | {(fp >= t).sum():>17d}")


if __name__ == "__main__":
    main()
