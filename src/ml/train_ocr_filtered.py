"""Thử nghiệm: huấn luyện lại CRNN chỉ trên crop đủ độ phân giải, rồi so sánh
với model gốc (huấn luyện trên toàn bộ dữ liệu).

Giả thuyết: crop dưới ~25px mỗi dòng ký tự thì mắt người cũng không đọc được,
nên nhãn của chúng gần như là nhiễu; bỏ đi có thể giúp model học tốt hơn ở
đúng dải độ phân giải mà camera bãi xe thật sẽ cho.

So sánh trên cùng tập test, tách riêng theo dải độ phân giải để thấy model lọc
có đánh đổi gì ở nhóm ảnh nhỏ hay không.

Chạy: (môi trường ml-gpu) python src/ml/train_ocr_filtered.py
"""

from __future__ import annotations

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

from ocr_model import benchmark_cpu, count_params, export_onnx, train_crnn  # noqa: E402
from pipeline.ocr import CRNNRecognizer, char_error_rate, read_plate  # noqa: E402

DATA_DIR = REPO_ROOT / "data" / "processed" / "plate-ocr"
CHECKPOINT_DIR = REPO_ROOT / "src" / "ml" / "checkpoints" / "plate-ocr"
WEIGHTS_DIR = REPO_ROOT / "src" / "ml" / "weights"
EXPERIMENTS_DIR = REPO_ROOT / "src" / "ml" / "experiments"

EPOCHS = 40
BATCH = 64
LR = 1e-3
MIN_PX_PER_ROW = 25.0


def evaluate_by_band(model_path: Path, test_csv: Path) -> dict:
    """Đánh giá mức cả biển, tách theo dải độ phân giải."""
    recognizer = CRNNRecognizer(model_path)
    df = pd.read_csv(test_csv)
    rows = []
    for _, r in df.iterrows():
        img = cv2.imread(r.image_path)
        if img is None:
            continue
        result = read_plate(img, recognizer, layout=r.layout)
        px_per_row = r.height / 2 if r.layout == "bien_2hang" else r.height
        rows.append({
            "px_per_row": px_per_row,
            "ok": int(result.text_normalized == r.label_clean),
            "cer": char_error_rate(result.text_normalized, r.label_clean),
        })
    d = pd.DataFrame(rows)
    bands = {"<20px": (0, 20), "20-30px": (20, 30), "30-40px": (30, 40), ">=40px": (40, 1e9)}
    out = {"overall_accuracy": d.ok.mean(), "overall_cer": d.cer.mean(), "n": len(d)}
    for name, (lo, hi) in bands.items():
        sub = d[(d.px_per_row >= lo) & (d.px_per_row < hi)]
        out[name] = {"n": len(sub), "accuracy": sub.ok.mean() if len(sub) else None}
    return out


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")

    model, best_path, history = train_crnn(
        train_csvs=[DATA_DIR / "train.csv"],
        val_csvs=[DATA_DIR / "val.csv"],
        epochs=EPOCHS, checkpoint_dir=CHECKPOINT_DIR, batch_size=BATCH, lr=LR,
        device=device, train_synthetic_csv=DATA_DIR / "train_synthetic.csv",
        min_px_per_row=MIN_PX_PER_ROW, checkpoint_name="crnn_filtered_best.pt",
    )

    pt_path = WEIGHTS_DIR / "plate-ocr-crnn-filtered.pt"
    shutil.copy(best_path, pt_path)
    onnx_path = WEIGHTS_DIR / "plate-ocr-crnn-filtered.onnx"
    export_onnx(model, onnx_path, device="cpu")

    print("\n=== So sánh 2 model trên cùng tập test ===")
    baseline = evaluate_by_band(WEIGHTS_DIR / "plate-ocr-crnn.pt", DATA_DIR / "test.csv")
    filtered = evaluate_by_band(pt_path, DATA_DIR / "test.csv")

    print(f"\n{'Dải':10s} {'n':>5s} {'gốc':>10s} {'lọc':>10s}")
    print(f"{'toàn bộ':10s} {baseline['n']:5d} {baseline['overall_accuracy']:9.1%} "
          f"{filtered['overall_accuracy']:9.1%}")
    for band in ("<20px", "20-30px", "30-40px", ">=40px"):
        b, f = baseline[band], filtered[band]
        if b["n"]:
            print(f"{band:10s} {b['n']:5d} {b['accuracy']:9.1%} {f['accuracy']:9.1%}")
    print(f"\nCER toàn bộ: gốc {baseline['overall_cer']:.4f} -> lọc {filtered['overall_cer']:.4f}")

    history["test_filtered"] = filtered
    history["test_baseline"] = baseline
    history["params"] = count_params(model)
    history["onnx_size_mb"] = round(onnx_path.stat().st_size / 1e6, 2)
    history["cpu_ms"] = benchmark_cpu(model, num_runs=50)
    history["min_px_per_row"] = MIN_PX_PER_ROW
    (EXPERIMENTS_DIR / "ocr_crnn_filtered_history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2, default=float), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
