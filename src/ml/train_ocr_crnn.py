"""Huấn luyện CRNN đọc ký tự biển số (charset 0-9, A-Z), đánh giá ở MỨC CẢ
BIỂN (ghép dòng trên+dưới cho biển 2 dòng qua `read_plate`), xuất ONNX và đo
tốc độ CPU để so sánh với 2 baseline pretrained (RapidOCR, EasyOCR) đã đánh
giá ở `src/ml/eval_ocr_baselines.py`.

Dữ liệu train: train.csv (crop thật) + train_synthetic.csv (crop sinh tổng
hợp, chỉ dùng để tăng dữ liệu, không xuất hiện trong val/test). Dữ liệu test
là test.csv - cùng tập giữ lại cho cả 2 baseline, so sánh công bằng.

Chạy: (môi trường ml-gpu) python src/ml/train_ocr_crnn.py
"""

from __future__ import annotations

import csv
import datetime
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))
sys.path.insert(0, str(REPO_ROOT / "src" / "ml"))

import cv2  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from ocr_model import (  # noqa: E402
    benchmark_cpu, count_params, export_onnx, train_crnn,
)
from pipeline.ocr import CRNNRecognizer, char_error_rate, read_plate  # noqa: E402

DATA_DIR = REPO_ROOT / "data" / "processed" / "plate-ocr"
CHECKPOINT_DIR = REPO_ROOT / "src" / "ml" / "checkpoints" / "plate-ocr"
WEIGHTS_DIR = REPO_ROOT / "src" / "ml" / "weights"
EXPERIMENTS_CSV = REPO_ROOT / "src" / "ml" / "experiments.csv"
EXPERIMENTS_DIR = REPO_ROOT / "src" / "ml" / "experiments"

EPOCHS = 40
BATCH = 64
LR = 1e-3


def evaluate_plate_level(model_path: Path, test_csv: Path) -> dict:
    """Đánh giá CRNN đã huấn luyện ở mức cả biển số (không phải mức dòng),
    dùng chung `read_plate()` với 2 baseline để số liệu so sánh được trực
    tiếp với `ocr_baselines_summary.csv`."""
    recognizer = CRNNRecognizer(model_path)
    df = pd.read_csv(test_csv)
    exact, cer_sum, n = 0, 0.0, 0
    per_layout: dict[str, list[int]] = {"bien_1hang": [0, 0], "bien_2hang": [0, 0]}
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
        n += 1
    return {
        "accuracy": exact / n, "cer": cer_sum / n, "n": n,
        "per_layout": {k: (v[0] / v[1] if v[1] else None) for k, v in per_layout.items()},
    }


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if device == "cuda" else "cpu"
    print(f"device: {device} ({device_name})")

    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    model, best_path, history = train_crnn(
        train_csvs=[DATA_DIR / "train.csv"],
        val_csvs=[DATA_DIR / "val.csv"],
        epochs=EPOCHS, checkpoint_dir=CHECKPOINT_DIR, batch_size=BATCH, lr=LR,
        device=device, train_synthetic_csv=DATA_DIR / "train_synthetic.csv",
    )

    pt_path = WEIGHTS_DIR / "plate-ocr-crnn.pt"
    shutil.copy(best_path, pt_path)
    onnx_path = WEIGHTS_DIR / "plate-ocr-crnn.onnx"
    export_onnx(model, onnx_path, device="cpu")

    cpu_ms = benchmark_cpu(model, num_runs=50)
    params = count_params(model)
    onnx_size_mb = round(onnx_path.stat().st_size / 1e6, 2)

    print("\nĐánh giá ở mức cả biển trên test.csv...")
    plate_res = evaluate_plate_level(pt_path, DATA_DIR / "test.csv")
    print(f"  accuracy toàn biển: {plate_res['accuracy']:.4f}  CER: {plate_res['cer']:.4f}")
    for layout, acc in plate_res["per_layout"].items():
        print(f"  {layout}: {acc}")

    history["test"] = plate_res
    history["params"] = params
    history["onnx_size_mb"] = onnx_size_mb
    history["cpu_ms"] = cpu_ms
    (EXPERIMENTS_DIR / "ocr_crnn_history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    row = [
        datetime.date.today().isoformat(), "crnn_ctc", "ocr",
        "topkek_plate_ocr (train.csv + train_synthetic.csv)",
        f"epochs={EPOCHS};batch={BATCH};lr={LR}",
        "", "", "", "",  # mAP50, mAP50-95, precision, recall: cột của detection, không áp dụng
        str(pt_path.relative_to(REPO_ROOT)),
        round(plate_res["accuracy"], 4), "",  # f1_macro không áp dụng cho OCR chuỗi
        params, onnx_size_mb, round(cpu_ms, 2),
    ]
    with open(EXPERIMENTS_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)
    print(f"\nĐã ghi 1 dòng vào {EXPERIMENTS_CSV}")


if __name__ == "__main__":
    main()
