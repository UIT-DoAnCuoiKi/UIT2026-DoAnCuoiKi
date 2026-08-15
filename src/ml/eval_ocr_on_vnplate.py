"""Đánh giá các biến thể CRNN trên tập test vn_plate đã gán nhãn thủ công.

Tập này khác topkek ở chỗ độ phân giải sát điều kiện triển khai hơn (88% biển
đạt >=40px mỗi dòng ký tự, so với 21,9% của topkek), và nhãn được gán độc lập
với model nên không có vòng lặp logic khi đánh giá.

Kết quả tách theo bố cục biển và theo dải độ phân giải, kèm khoảng tin cậy vì
cỡ mẫu nhỏ (96 biển) nên một con số accuracy đơn lẻ dễ gây hiểu nhầm.

Chạy: .venv/Scripts/python.exe src/ml/eval_ocr_on_vnplate.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))
sys.path.insert(0, str(REPO_ROOT / "src" / "ml"))

import cv2  # noqa: E402
import pandas as pd  # noqa: E402

from pipeline.ocr import CRNNRecognizer, char_error_rate, read_plate  # noqa: E402

TEST_CSV = REPO_ROOT / "data" / "processed" / "vn-plate-test.csv"
WEIGHTS_DIR = REPO_ROOT / "src" / "ml" / "weights"
OUT_CSV = REPO_ROOT / "src" / "ml" / "experiments" / "ocr_vnplate_results.csv"


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson cho tỉ lệ. Dùng Wilson thay vì công thức chuẩn
    thông thường vì cỡ mẫu nhỏ và tỉ lệ có thể gần 0 hoặc 1."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def evaluate(model_path: Path, df: pd.DataFrame) -> dict:
    recognizer = CRNNRecognizer(model_path)
    rows = []
    for _, r in df.iterrows():
        img = cv2.imread(str(REPO_ROOT / r.image_path))
        if img is None:
            continue
        result = read_plate(img, recognizer, layout=r.layout)
        px_per_row = r.height / 2 if r.layout == "bien_2hang" else r.height
        rows.append({
            "px_per_row": px_per_row, "layout": r.layout,
            "gold": r.label_clean, "pred": result.text_normalized,
            "ok": int(result.text_normalized == r.label_clean),
            "cer": char_error_rate(result.text_normalized, r.label_clean),
        })
    return {"rows": pd.DataFrame(rows)}


def report(name: str, d: pd.DataFrame) -> dict:
    k, n = int(d.ok.sum()), len(d)
    lo, hi = wilson_interval(k, n)
    print(f"\n=== {name} ===")
    print(f"  accuracy toàn biển: {k}/{n} = {k / n:.1%}  (KTC 95%: {lo:.1%} - {hi:.1%})")
    print(f"  CER trung bình: {d.cer.mean():.4f}")

    out = {"accuracy": k / n, "n": n, "ci_low": lo, "ci_high": hi, "cer": d.cer.mean()}
    print("  theo bố cục:")
    for layout in ("bien_1hang", "bien_2hang"):
        sub = d[d.layout == layout]
        if len(sub):
            kk = int(sub.ok.sum())
            print(f"    {layout}: {kk}/{len(sub)} = {kk / len(sub):.1%}")
            out[f"acc_{layout}"] = kk / len(sub)
    print("  theo độ phân giải:")
    for label, lo_px, hi_px in (("<30px", 0, 30), ("30-45px", 30, 45),
                                ("45-70px", 45, 70), (">=70px", 70, 1e9)):
        sub = d[(d.px_per_row >= lo_px) & (d.px_per_row < hi_px)]
        if len(sub):
            kk = int(sub.ok.sum())
            print(f"    {label:9s} n={len(sub):3d}  {kk / len(sub):.1%}")
            out[f"acc_{label}"] = kk / len(sub)
    return out


TEST_SETS = {
    "vn_plate": TEST_CSV,
    "topkek": REPO_ROOT / "data" / "processed" / "plate-ocr" / "test.csv",
}


def main() -> None:
    candidates = {
        "V2_synthetic_degraded": WEIGHTS_DIR / "plate-ocr-crnn-V2_synthetic_degraded.pt",
        "V3_fixed_labels": WEIGHTS_DIR / "plate-ocr-crnn-V3_fixed_labels.pt",
    }

    summary = []
    for set_name, csv_path in TEST_SETS.items():
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        print(f"\n{'#' * 60}\n# Tập test {set_name}: {len(df)} biển\n{'#' * 60}")

        for name, path in candidates.items():
            if not path.exists():
                print(f"\n(bỏ qua {name}: chưa có {path.name})")
                continue
            res = evaluate(path, df)
            stats = report(f"{set_name} / {name}", res["rows"])
            summary.append({"test_set": set_name, "variant": name, **stats})

            errors = res["rows"][res["rows"].ok == 0]
            if len(errors):
                print("  ví dụ sai (tối đa 5): ", end="")
                print(", ".join(f"{r.gold}->{r.pred or '(rỗng)'}"
                                for _, r in errors.head(5).iterrows()))

    if summary:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({k for row in summary for k in row})
        # Giữ 2 cột định danh lên đầu cho dễ đọc
        for key in ("variant", "test_set"):
            fields.remove(key)
            fields.insert(0, key)
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(summary)
        print(f"\nĐã ghi {OUT_CSV.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
