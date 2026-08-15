"""Ablation: ảnh sinh tổng hợp nên dùng thế nào trong huấn luyện OCR biển số.

Bối cảnh: ảnh sinh tổng hợp của topkek chiếm khoảng một nửa số dòng huấn luyện
nhưng lệch phân phối nặng so với ảnh thật (100% đạt >=40px mỗi dòng ký tự và
sạch tinh, trong khi ảnh thật có trung vị 19px/dòng, chỉ 7% đạt >=40px).

Ba biến thể, chỉ khác nhau đúng cách xử lý ảnh sinh tổng hợp, mọi thứ còn lại
giữ nguyên để so sánh công bằng:

  V0  thật + sinh tổng hợp nguyên bản
  V1  chỉ ảnh thật (bỏ hẳn sinh tổng hợp)
  V2  thật + sinh tổng hợp đã hạ cấp cho khớp phân phối ảnh thật

Lưu ý: cả 3 đều huấn luyện lại trong lần chạy này, kể cả V0 dù đã có model cũ,
vì augmentation vừa được bổ sung biến dạng phối cảnh. Dùng lại số cũ của V0 sẽ
làm lẫn hai thay đổi vào nhau, không kết luận được nguyên nhân.

Chạy: (môi trường ml-gpu) python src/ml/train_ocr_ablation.py
"""

from __future__ import annotations

import csv
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

VARIANTS = {
    "V0_synthetic_raw": {"use_synthetic": True, "degrade": False,
                         "desc": "thật + sinh tổng hợp nguyên bản"},
    "V1_real_only": {"use_synthetic": False, "degrade": False,
                     "desc": "chỉ ảnh thật"},
    "V2_synthetic_degraded": {"use_synthetic": True, "degrade": True,
                              "desc": "thật + sinh tổng hợp đã hạ cấp"},
}


def evaluate_by_band(model_path: Path, test_csv: Path) -> dict:
    """Đánh giá mức cả biển, tách theo dải độ phân giải và theo bố cục biển."""
    recognizer = CRNNRecognizer(model_path)
    df = pd.read_csv(test_csv)
    rows = []
    for _, r in df.iterrows():
        img = cv2.imread(str(REPO_ROOT / r.image_path))
        if img is None:
            img = cv2.imread(r.image_path)
        if img is None:
            continue
        result = read_plate(img, recognizer, layout=r.layout)
        px_per_row = r.height / 2 if r.layout == "bien_2hang" else r.height
        rows.append({
            "px_per_row": px_per_row, "layout": r.layout,
            "ok": int(result.text_normalized == r.label_clean),
            "cer": char_error_rate(result.text_normalized, r.label_clean),
        })
    d = pd.DataFrame(rows)
    out = {"accuracy": d.ok.mean(), "cer": d.cer.mean(), "n": len(d)}
    for name, (lo, hi) in {"<20px": (0, 20), "20-30px": (20, 30),
                           "30-40px": (30, 40), ">=40px": (40, 1e9)}.items():
        sub = d[(d.px_per_row >= lo) & (d.px_per_row < hi)]
        out[name] = {"n": len(sub), "accuracy": sub.ok.mean() if len(sub) else None}
    for layout in ("bien_1hang", "bien_2hang"):
        sub = d[d.layout == layout]
        out[layout] = {"n": len(sub), "accuracy": sub.ok.mean() if len(sub) else None}
    return out


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for name, cfg in VARIANTS.items():
        print(f"\n===== {name}: {cfg['desc']} =====")
        model, best_path, history = train_crnn(
            train_csvs=[DATA_DIR / "train.csv"],
            val_csvs=[DATA_DIR / "val.csv"],
            epochs=EPOCHS, checkpoint_dir=CHECKPOINT_DIR, batch_size=BATCH, lr=LR,
            device=device,
            train_synthetic_csv=(DATA_DIR / "train_synthetic.csv") if cfg["use_synthetic"] else None,
            degrade_synthetic=cfg["degrade"],
            checkpoint_name=f"crnn_{name}_best.pt",
        )

        pt_path = WEIGHTS_DIR / f"plate-ocr-crnn-{name}.pt"
        shutil.copy(best_path, pt_path)
        onnx_path = WEIGHTS_DIR / f"plate-ocr-crnn-{name}.onnx"
        export_onnx(model, onnx_path, device="cpu")

        res = evaluate_by_band(pt_path, DATA_DIR / "test.csv")
        print(f"[{name}] test topkek: accuracy={res['accuracy']:.4f} CER={res['cer']:.4f}")

        history["test_topkek"] = res
        history["params"] = count_params(model)
        history["onnx_size_mb"] = round(onnx_path.stat().st_size / 1e6, 2)
        history["cpu_ms"] = benchmark_cpu(model, num_runs=50)
        history["variant"] = name
        history["description"] = cfg["desc"]
        (EXPERIMENTS_DIR / f"ocr_ablation_{name}_history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2, default=float), encoding="utf-8"
        )
        results[name] = {"res": res, "weights": pt_path, "history": history}

    print("\n=== Bảng so sánh (tập test topkek) ===")
    header = f"{'biến thể':24s} {'accuracy':>9s} {'CER':>7s} {'<20px':>7s} {'20-30':>7s} {'30-40':>7s} {'>=40px':>7s}"
    print(header)
    for name, r in results.items():
        res = r["res"]
        cells = []
        for band in ("<20px", "20-30px", "30-40px", ">=40px"):
            a = res[band]["accuracy"]
            cells.append(f"{a:6.1%}" if a is not None else "     -")
        print(f"{name:24s} {res['accuracy']:8.1%} {res['cer']:7.4f} " + " ".join(f"{c:>7s}" for c in cells))

    with open(EXPERIMENTS_DIR / "ocr_ablation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variant", "description", "accuracy", "cer", "n",
                    "acc_lt20px", "acc_20_30px", "acc_30_40px", "acc_ge40px",
                    "acc_1hang", "acc_2hang", "params", "onnx_mb", "cpu_ms", "weights"])
        for name, r in results.items():
            res, h = r["res"], r["history"]
            w.writerow([
                name, VARIANTS[name]["desc"], round(res["accuracy"], 4), round(res["cer"], 4), res["n"],
                res["<20px"]["accuracy"], res["20-30px"]["accuracy"],
                res["30-40px"]["accuracy"], res[">=40px"]["accuracy"],
                res["bien_1hang"]["accuracy"], res["bien_2hang"]["accuracy"],
                h["params"], h["onnx_size_mb"], round(h["cpu_ms"], 2),
                str(r["weights"].relative_to(REPO_ROOT)),
            ])
    print(f"\nĐã ghi {(EXPERIMENTS_DIR / 'ocr_ablation.csv').relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
