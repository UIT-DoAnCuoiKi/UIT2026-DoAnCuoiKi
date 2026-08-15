"""Chạy OCR trên crop biển cắt từ A1 (kaggle_vn_plate_segment) - dataset mà
module phát hiện biển số (Đức) dùng để huấn luyện.

Mục đích: kiểm chứng OCR trên đúng phân phối ảnh mà pipeline thật sẽ gặp, thay
vì chỉ trên crop sẵn của topkek. Biển được cắt theo toạ độ polygon có sẵn trong
nhãn A1, tức đánh giá ở điều kiện "biết trước vị trí biển" (ground-truth box),
tách biệt với sai số của bước phát hiện.

A1 không có nhãn chuỗi ký tự, nên không tính được accuracy tự động. Script này
báo 2 chỉ số thay thế:
  - Tỉ lệ chuỗi đọc được khớp định dạng biển số VN (proxy tự động).
  - Xuất 1 lưới ảnh kèm chuỗi đọc được để đối chiếu bằng mắt, lấy accuracy thật
    trên mẫu nhỏ.

Chạy: .venv/Scripts/python.exe src/ml/eval_ocr_on_a1.py
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))
sys.path.insert(0, str(REPO_ROOT / "src" / "ml"))

from pipeline.ocr import CRNNRecognizer, perspective_correct, read_plate  # noqa: E402

A1_DIR = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment"
OUT_DIR = REPO_ROOT / "src" / "ml" / "experiments"
FIG_DIR = REPO_ROOT / "docs" / "report" / "figures"

# A1 đặt tên lớp theo bố cục biển: BSD = biển số dài (1 dòng), BSV = biển số
# vuông (2 dòng). Ánh xạ sang tên lớp dùng chung trong pipeline OCR.
A1_CLASS_TO_LAYOUT = {0: "bien_1hang", 1: "bien_2hang"}

PADDING_FRAC = 0.08  # biên thêm quanh biển, hợp với quy ước lúc cắt của detector
SPLIT = "val"        # A1 chỉ có train/val; dùng val để tránh ảnh detector đã học
MONTAGE_N = 24
SEED = 11


def crop_plates(split: str, limit: int | None = None) -> list[dict]:
    """Cắt từng biển theo polygon trong nhãn A1. Trả về list dict gồm ảnh đã
    cắt, layout và chiều cao mỗi dòng ký tự (để phân tầng theo độ phân giải)."""
    lbl_dir = A1_DIR / "labels" / split
    img_dir = A1_DIR / "images" / split
    label_files = sorted(lbl_dir.glob("*.txt"))
    if limit:
        rng = random.Random(SEED)
        label_files = rng.sample(label_files, min(limit, len(label_files)))

    out = []
    for lp in label_files:
        ip = next((img_dir / (lp.stem + ext) for ext in (".jpg", ".jpeg", ".png")
                   if (img_dir / (lp.stem + ext)).exists()), None)
        if ip is None:
            continue
        img = cv2.imread(str(ip))
        if img is None:
            continue
        h, w = img.shape[:2]

        for line in lp.read_text(encoding="utf-8").strip().splitlines():
            parts = line.split()
            if len(parts) < 9:
                continue
            cls_id = int(parts[0])
            layout = A1_CLASS_TO_LAYOUT.get(cls_id)
            if layout is None:
                continue
            corners = np.array([float(v) for v in parts[1:9]], dtype=float).reshape(4, 2)
            xs, ys = corners[:, 0] * w, corners[:, 1] * h
            x1, x2 = xs.min(), xs.max()
            y1, y2 = ys.min(), ys.max()
            pad_w, pad_h = (x2 - x1) * PADDING_FRAC, (y2 - y1) * PADDING_FRAC
            x1, y1 = int(max(0, x1 - pad_w)), int(max(0, y1 - pad_h))
            x2, y2 = int(min(w, x2 + pad_w)), int(min(h, y2 + pad_h))
            if x2 - x1 < 8 or y2 - y1 < 8:
                continue

            crop = img[y1:y2, x1:x2]
            rows_of_text = 2 if layout == "bien_2hang" else 1
            # Toạ độ 4 góc quy về hệ toạ độ của ảnh đã cắt, để nắn phối cảnh
            local_corners = np.stack([xs - x1, ys - y1], axis=1)
            out.append({
                "source_image": ip.name, "crop": crop, "layout": layout,
                "corners": local_corners,
                "px_per_row": (y2 - y1) / rows_of_text,
            })
    return out


def main() -> None:
    plates = crop_plates(SPLIT, limit=400)
    print(f"Đã cắt {len(plates)} biển từ A1/{SPLIT}")

    recognizer = CRNNRecognizer(REPO_ROOT / "src" / "ml" / "weights" / "plate-ocr-crnn.pt")

    # So sánh 2 cách xử lý hình học trước khi OCR, trên đúng cùng tập biển:
    #   deskew    - chỉ xoay trong mặt phẳng (cách cũ)
    #   perspective - nắn 4 góc về hình chữ nhật phẳng (khử góc nhìn chéo)
    variants = {"deskew": None, "perspective": "corners"}
    all_results: dict[str, list[dict]] = {}

    for name, corner_key in variants.items():
        results = []
        for p in plates:
            corners = p["corners"] if corner_key else None
            reading = read_plate(p["crop"], recognizer, layout=p["layout"], corners=corners)
            results.append({**p, "pred": reading.text_normalized,
                            "valid": reading.valid_format, "conf": reading.confidence})
        all_results[name] = results

        n = len(results)
        print(f"\n=== {name} ===")
        print(f"Tỉ lệ khớp định dạng biển VN: {sum(r['valid'] for r in results) / n:.1%} "
              f"({sum(r['valid'] for r in results)}/{n})")
        for layout in ("bien_1hang", "bien_2hang"):
            sub = [r for r in results if r["layout"] == layout]
            if sub:
                print(f"  {layout}: {sum(r['valid'] for r in sub) / len(sub):.1%} ({len(sub)} biển)")

    # Số biển mà 2 cách cho kết quả khác nhau, để thấy tác động thật sự
    changed = sum(1 for a, b in zip(all_results["deskew"], all_results["perspective"])
                  if a["pred"] != b["pred"])
    print(f"\nSố biển bị đổi kết quả khi nắn phối cảnh: {changed}/{len(plates)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "ocr_a1_predictions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_image", "layout", "px_per_row",
                         "pred_deskew", "valid_deskew", "pred_perspective", "valid_perspective"])
        for a, b in zip(all_results["deskew"], all_results["perspective"]):
            writer.writerow([a["source_image"], a["layout"], round(a["px_per_row"], 1),
                             a["pred"], a["valid"], b["pred"], b["valid"]])

    # Lưới ảnh để đối chiếu bằng mắt: ưu tiên biển đủ nét, nơi kết quả OCR có ý
    # nghĩa để đánh giá, thay vì lấy ngẫu nhiên lẫn cả ảnh không đọc nổi
    persp = all_results["perspective"]
    order = sorted(range(len(persp)), key=lambda i: -persp[i]["px_per_row"])
    picked = [i for i in order if persp[i]["px_per_row"] >= 25][:MONTAGE_N]
    if picked:
        items = []
        for i in picked:
            items.append({
                "crop": perspective_correct(plates[i]["crop"], plates[i]["corners"]),
                "pred": persp[i]["pred"],
                "px_per_row": persp[i]["px_per_row"],
            })
        save_montage(items, FIG_DIR / "plate_ocr_a1_montage.png")
        print(f"\nĐã lưu lưới {len(items)} ảnh đã nắn phối cảnh để đối chiếu tay: "
              f"{(FIG_DIR / 'plate_ocr_a1_montage.png').relative_to(REPO_ROOT)}")


def save_montage(items: list[dict], out_path: Path, cols: int = 4) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = (len(items) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 2.0))
    for ax, item in zip(np.ravel(axes), items):
        ax.imshow(cv2.cvtColor(item["crop"], cv2.COLOR_BGR2RGB))
        ax.set_title(f"{item['pred']}  ({item['px_per_row']:.0f}px/dòng)", fontsize=9)
        ax.axis("off")
    for ax in np.ravel(axes)[len(items):]:
        ax.axis("off")
    fig.suptitle("Kết quả OCR trên biển cắt từ A1 (dataset của module phát hiện)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
