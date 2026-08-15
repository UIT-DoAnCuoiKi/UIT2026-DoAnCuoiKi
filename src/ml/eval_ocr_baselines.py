"""Đánh giá 2 engine OCR pretrained (RapidOCR, EasyOCR) trên tập test biển số
đã chuẩn bị ở `src/ml/data_prep/prepare_ocr_data.py`, làm baseline so sánh với
model CRNN tự huấn luyện (`train_ocr_crnn.py`).

Đánh giá trên test.csv (topkek, crop thật, chưa từng dùng để train) - đã có cả
biển 1 dòng (188 ảnh) và 2 dòng (478 ảnh) nên đủ để so sánh cả 2 layout.

test_motorbike_2row.csv (dtkngan) KHÔNG dùng ở bước này: ảnh gốc là ảnh toàn
cảnh xe máy tại cổng (472x303, biển chỉ chiếm 1 vùng nhỏ giữa khung hình),
cần qua bước crop bằng PlateDetector (module plate_detection_pipeline của
Đức) trước mới OCR được. Weight detect chưa có sẵn trên máy lúc viết module
này, nên tập này để dành đánh giá end-to-end lúc tích hợp pipeline (Tuần 6).

Chỉ số: accuracy khớp toàn biển (exact match), CER (character error rate)
trung bình, thời gian suy luận CPU trung bình mỗi biển, và kích thước model
trên đĩa (đại diện cho khả năng chạy trên thiết bị biên cấu hình thấp).

Chạy: .venv/Scripts/python.exe src/ml/eval_ocr_baselines.py
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import cv2
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "plate-ocr"
EXPERIMENTS_CSV = REPO_ROOT / "src" / "ml" / "experiments.csv"
RESULTS_DIR = REPO_ROOT / "src" / "ml" / "experiments"

import sys
sys.path.insert(0, str(REPO_ROOT / "src" / "ml"))
from pipeline.ocr import char_error_rate, read_plate  # noqa: E402


def evaluate(recognizer, df: pd.DataFrame, name: str) -> dict:
    n = len(df)
    exact = 0
    cer_sum = 0.0
    per_layout: dict[str, list[int]] = {"bien_1hang": [0, 0], "bien_2hang": [0, 0]}
    t0 = time.perf_counter()
    rows = []
    for _, r in df.iterrows():
        img = cv2.imread(r.image_path)
        if img is None:
            continue
        result = read_plate(img, recognizer, layout=r.layout)
        ok = int(result.text_normalized == r.label_clean)
        exact += ok
        cer_sum += char_error_rate(result.text_normalized, r.label_clean)
        per_layout[r.layout][0] += ok
        per_layout[r.layout][1] += 1
        rows.append({
            "image_path": r.image_path, "label_clean": r.label_clean,
            "pred": result.text_normalized, "confidence": result.confidence, "exact": ok,
        })
    elapsed = time.perf_counter() - t0

    print(f"\n=== {name} ===")
    print(f"  accuracy toàn biển: {exact}/{n} = {exact / n:.4f}")
    print(f"  CER trung bình: {cer_sum / n:.4f}")
    print(f"  thời gian trung bình mỗi biển: {elapsed / n * 1000:.1f} ms")
    for layout, (ok, total) in per_layout.items():
        if total:
            print(f"  {layout}: {ok}/{total} = {ok / total:.4f}")

    return {
        "name": name, "n": n, "exact_accuracy": exact / n, "cer": cer_sum / n,
        "ms_per_plate": elapsed / n * 1000, "per_layout": per_layout, "rows": rows,
    }


def main() -> None:
    test_df = pd.read_csv(PROCESSED_DIR / "test.csv")

    from pipeline.ocr import EasyOCRRecognizer, RapidOCRRecognizer

    backends = {
        "RapidOCR (ONNXRuntime, pretrained đa ngôn ngữ)": RapidOCRRecognizer(),
        "EasyOCR (PyTorch, pretrained tiếng Anh)": EasyOCRRecognizer(gpu=True),
    }

    summary_rows = []
    for backend_name, recognizer in backends.items():
        res_topkek = evaluate(recognizer, test_df, f"{backend_name} / topkek test")
        summary_rows.append({
            "backend": backend_name,
            "topkek_accuracy": res_topkek["exact_accuracy"], "topkek_cer": res_topkek["cer"],
            "ms_per_plate": res_topkek["ms_per_plate"],
        })

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "ocr_baselines_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\n=== Bảng tổng hợp ===")
    for row in summary_rows:
        print(row)


if __name__ == "__main__":
    main()
