"""Cắt biển từ A1 (kaggle_vn_plate_segment) để làm tập test độc lập, có nhãn
thật, cho module OCR — đo domain gap giữa dataset train detector (A1, phân
giải cao) và dataset train OCR (topkek, phân giải thấp hơn).

A1 chỉ có nhãn vị trí (polygon 4 góc), không có nhãn chuỗi ký tự, nên script
này chỉ cắt ảnh (đã nắn phối cảnh phẳng) và xuất lưới để người đọc gán nhãn.
Cố ý KHÔNG chạy model và KHÔNG hiển thị dự đoán, đúng nguyên tắc đã áp dụng
cho `vn_plate` (`prepare_vnplate_testset.py`): nếu điền sẵn dự đoán rồi lấy đó
làm nhãn thì việc đánh giá thành vòng tròn logic, accuracy sẽ bị thổi phồng.

A1 không có split `test`, chỉ có `train`/`val`. Dùng `val` (không lan truyền
ngược lúc train) — cùng lựa chọn đã dùng ở `eval_ocr_on_a1.py`.

Lấy mẫu cân bằng 100 biển 1 dòng (bien_1hang) + 100 biển 2 dòng (bien_2hang),
lấy riêng theo từng lớp để đảm bảo đúng tỉ lệ, không lấy mẫu chung rồi lọc.

Chạy: .venv/Scripts/python.exe src/ml/data_prep/prepare_a1_ocr_testset.py
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":  # console Windows mặc định cp1252
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml"))

from pipeline.ocr import perspective_correct  # noqa: E402

A1_DIR = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment"
SPLIT = "val"  # A1 chỉ có train/val, không có test; val tránh ảnh detector đã học
CROP_DIR = REPO_ROOT / "data" / "processed" / "a1-ocr-test-crops"
MANIFEST = REPO_ROOT / "data" / "processed" / "a1-ocr-test-manifest.csv"
MONTAGE_DIR = REPO_ROOT / "data" / "processed" / "a1-ocr-test-montages"

A1_CLASS_TO_LAYOUT = {0: "bien_1hang", 1: "bien_2hang"}
N_PER_LAYOUT = 100
SEED = 2026
PADDING_FRAC = 0.08  # khớp quy ước cắt của eval_ocr_on_a1.py
PER_MONTAGE = 10


def collect_plates(split: str) -> dict[str, list[dict]]:
    """Đọc toàn bộ biển từ nhãn polygon A1, tách sẵn theo layout để lấy mẫu
    cân bằng theo từng lớp."""
    lbl_dir = A1_DIR / "labels" / split
    img_dir = A1_DIR / "images" / split
    by_layout: dict[str, list[dict]] = {"bien_1hang": [], "bien_2hang": []}

    for lp in sorted(lbl_dir.glob("*.txt")):
        img_path = next((img_dir / (lp.stem + ext) for ext in (".jpg", ".jpeg", ".png")
                         if (img_dir / (lp.stem + ext)).exists()), None)
        if img_path is None:
            continue
        for line_idx, line in enumerate(lp.read_text(encoding="utf-8").strip().splitlines()):
            parts = line.split()
            if len(parts) < 9:
                continue
            layout = A1_CLASS_TO_LAYOUT.get(int(parts[0]))
            if layout is None:
                continue
            by_layout[layout].append({
                "label_file": lp, "line_idx": line_idx, "layout": layout,
                "image_path": img_path, "coords": [float(v) for v in parts[1:9]],
            })
    return by_layout


def crop_one(item: dict) -> dict | None:
    """Cắt 1 biển theo bbox bao polygon + pad, rồi nắn phối cảnh phẳng ngay
    tại đây (khác `eval_ocr_on_a1.py` vốn nắn lúc OCR) để ảnh lưu ra dùng
    thẳng được với `read_plate(img, recognizer, layout=...)` không cần
    truyền `corners` — tập test A1 dùng chung schema với test.csv/vn-plate."""
    img = cv2.imread(str(item["image_path"]))
    if img is None:
        return None
    h, w = img.shape[:2]
    corners = np.array(item["coords"], dtype=float).reshape(4, 2)
    xs, ys = corners[:, 0] * w, corners[:, 1] * h
    x1, x2 = xs.min(), xs.max()
    y1, y2 = ys.min(), ys.max()
    pad_w, pad_h = (x2 - x1) * PADDING_FRAC, (y2 - y1) * PADDING_FRAC
    x1, y1 = int(max(0, x1 - pad_w)), int(max(0, y1 - pad_h))
    x2, y2 = int(min(w, x2 + pad_w)), int(min(h, y2 + pad_h))
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None

    crop = img[y1:y2, x1:x2]
    local_corners = np.stack([xs - x1, ys - y1], axis=1)
    corrected = perspective_correct(crop, local_corners)
    ch, cw = corrected.shape[:2]
    if ch < 8 or cw < 8:
        return None
    return {**item, "crop": corrected, "width": cw, "height": ch}


def save_montage(items: list[dict], out_path: Path, start_index: int) -> None:
    """Lưới ảnh có đánh số, chỉ hiện ảnh và mã số, không hiện bất kỳ dự đoán nào."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cols = 2
    rows = (len(items) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 6.0, rows * 2.2))
    for ax, (offset, item) in zip(np.ravel(axes), enumerate(items)):
        ax.imshow(cv2.cvtColor(item["crop"], cv2.COLOR_BGR2RGB))
        ax.set_title(f"#{start_index + offset:03d}  ({item['layout']}, "
                     f"{item['px_per_row']:.0f}px/dòng)", fontsize=11)
        ax.axis("off")
    for ax in np.ravel(axes)[len(items):]:
        ax.axis("off")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    by_layout = collect_plates(SPLIT)
    for layout, items in by_layout.items():
        print(f"A1/{SPLIT}: {len(items)} biển {layout}")

    # Xáo trộn toàn bộ pool mỗi layout (đủ dư so với 100 cần lấy) rồi cắt lần
    # lượt tới khi đủ 100 crop hợp lệ mỗi lớp, thay vì lấy đúng 100 rồi chấp
    # nhận thiếu nếu vài ảnh bị loại (quá nhỏ sau pad/nắn phối cảnh).
    rng = random.Random(SEED)
    CROP_DIR.mkdir(parents=True, exist_ok=True)
    cropped: list[dict] = []
    for layout in ("bien_1hang", "bien_2hang"):
        pool = by_layout[layout][:]
        rng.shuffle(pool)
        n_ok = 0
        for item in pool:
            if n_ok >= N_PER_LAYOUT:
                break
            c = crop_one(item)
            if c is None:
                continue
            rows_of_text = 2 if c["layout"] == "bien_2hang" else 1
            c["px_per_row"] = c["height"] / rows_of_text
            idx = len(cropped)
            crop_name = f"{idx:03d}_{item['image_path'].stem}_{item['line_idx']}.jpg"
            cv2.imwrite(str(CROP_DIR / crop_name), c["crop"], [cv2.IMWRITE_JPEG_QUALITY, 98])
            c["crop_file"] = crop_name
            c["index"] = idx
            cropped.append(c)
            n_ok += 1
        if n_ok < N_PER_LAYOUT:
            print(f"CẢNH BÁO: chỉ lấy được {n_ok}/{N_PER_LAYOUT} biển {layout} hợp lệ (hết pool)")

    n_1h = sum(1 for c in cropped if c["layout"] == "bien_1hang")
    print(f"\nĐã cắt {len(cropped)} biển vào {CROP_DIR.relative_to(REPO_ROOT)}")
    print(f"Bố cục: {n_1h} biển 1 dòng, {len(cropped) - n_1h} biển 2 dòng")

    MONTAGE_DIR.mkdir(parents=True, exist_ok=True)
    n_montages = 0
    for start in range(0, len(cropped), PER_MONTAGE):
        batch = cropped[start:start + PER_MONTAGE]
        save_montage(batch, MONTAGE_DIR / f"montage_{start:03d}.png", start)
        n_montages += 1
    print(f"Đã xuất {n_montages} lưới ảnh vào {MONTAGE_DIR.relative_to(REPO_ROOT)}")

    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "crop_file", "image_path", "source_image",
                    "layout", "width", "height", "px_per_row"])
        for c in cropped:
            w.writerow([
                c["index"], c["crop_file"],
                str((CROP_DIR / c["crop_file"]).relative_to(REPO_ROOT)),
                c["image_path"].name, c["layout"], c["width"], c["height"],
                round(c["px_per_row"], 1),
            ])
    print(f"Đã ghi {MANIFEST.relative_to(REPO_ROOT)}")

    ppr = np.array([c["px_per_row"] for c in cropped])
    print(f"px/dòng: trung vị {np.median(ppr):.0f}, tỉ lệ >=40px: {(ppr >= 40).mean():.1%}")


if __name__ == "__main__":
    main()
