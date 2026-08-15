"""Cắt biển từ vn_plate để làm tập test độc lập cho module OCR.

vn_plate (Roboflow "Vietnam license-plate", CC BY 4.0) có sẵn bounding box biển
nhưng KHÔNG có nhãn chuỗi ký tự. Bộ này đáng dùng làm tập test vì độ phân giải
tốt hơn hẳn topkek (76% biển đạt >=40px mỗi dòng ký tự, so với 21,9%), tức sát
với điều kiện camera thật ở cổng bãi xe hơn.

Script chỉ cắt ảnh và xuất lưới để người đọc gán nhãn. Cố ý KHÔNG chạy model
và KHÔNG hiển thị dự đoán: nếu điền sẵn dự đoán rồi lấy đó làm nhãn thì việc
đánh giá thành vòng tròn logic, accuracy sẽ bị thổi phồng.

Lấy mẫu ngẫu nhiên (seed cố định) chứ không chọn lọc theo độ phân giải hay bố
cục, để con số đo được là ước lượng không thiên lệch trên đúng phân phối của
vn_plate.

Chạy: .venv/Scripts/python.exe src/ml/data_prep/prepare_vnplate_testset.py
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
VN_PLATE_DIR = REPO_ROOT / "data" / "raw" / "vn_plate"
CROP_DIR = REPO_ROOT / "data" / "processed" / "vn-plate-test-crops"
MANIFEST = REPO_ROOT / "data" / "processed" / "vn-plate-test-manifest.csv"
MONTAGE_DIR = REPO_ROOT / "data" / "processed" / "vn-plate-test-montages"

N_SAMPLE = 100
SEED = 2026
PADDING_FRAC = 0.06
ASPECT_2ROW = 2.0
PER_MONTAGE = 10


def collect_plates() -> list[dict]:
    """Đọc toàn bộ bbox từ 3 split của bản export COCO."""
    out = []
    for split in ("train", "valid", "test"):
        ann_path = VN_PLATE_DIR / split / "_annotations.coco.json"
        if not ann_path.exists():
            continue
        data = json.loads(ann_path.read_text(encoding="utf-8"))
        by_id = {im["id"]: im["file_name"] for im in data["images"]}
        for ann in data["annotations"]:
            fname = by_id.get(ann["image_id"])
            if fname:
                out.append({"split": split, "file_name": fname,
                            "ann_id": ann["id"], "bbox": ann["bbox"]})
    return out


def crop_one(item: dict) -> dict | None:
    img = cv2.imread(str(VN_PLATE_DIR / item["split"] / item["file_name"]))
    if img is None:
        return None
    H, W = img.shape[:2]
    x, y, w, h = item["bbox"]
    pad_w, pad_h = w * PADDING_FRAC, h * PADDING_FRAC
    x1, y1 = int(max(0, x - pad_w)), int(max(0, y - pad_h))
    x2, y2 = int(min(W, x + w + pad_w)), int(min(H, y + h + pad_h))
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None

    crop = img[y1:y2, x1:x2]
    crop_w, crop_h = x2 - x1, y2 - y1
    layout = "bien_1hang" if crop_w / crop_h >= ASPECT_2ROW else "bien_2hang"
    return {**item, "crop": crop, "width": crop_w, "height": crop_h, "layout": layout,
            "px_per_row": crop_h / (2 if layout == "bien_2hang" else 1)}


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
    plates = collect_plates()
    print(f"Tổng số biển có bbox trong vn_plate: {len(plates)}")

    rng = random.Random(SEED)
    picked = rng.sample(plates, min(N_SAMPLE, len(plates)))

    CROP_DIR.mkdir(parents=True, exist_ok=True)
    cropped = []
    for item in picked:
        c = crop_one(item)
        if c is None:
            continue
        idx = len(cropped)
        crop_name = f"{idx:03d}_{item['split']}_{item['ann_id']}.jpg"
        cv2.imwrite(str(CROP_DIR / crop_name), c["crop"], [cv2.IMWRITE_JPEG_QUALITY, 98])
        c["crop_file"] = crop_name
        c["index"] = idx
        cropped.append(c)

    print(f"Đã cắt {len(cropped)} biển vào {CROP_DIR.relative_to(REPO_ROOT)}")

    MONTAGE_DIR.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(cropped), PER_MONTAGE):
        batch = cropped[start:start + PER_MONTAGE]
        save_montage(batch, MONTAGE_DIR / f"montage_{start:03d}.png", start)
    print(f"Đã xuất {len(range(0, len(cropped), PER_MONTAGE))} lưới ảnh vào "
          f"{MONTAGE_DIR.relative_to(REPO_ROOT)}")

    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "crop_file", "image_path", "source_image", "split",
                    "layout", "width", "height", "px_per_row"])
        for c in cropped:
            w.writerow([
                c["index"], c["crop_file"],
                str((CROP_DIR / c["crop_file"]).relative_to(REPO_ROOT)),
                c["file_name"], c["split"], c["layout"], c["width"], c["height"],
                round(c["px_per_row"], 1),
            ])
    print(f"Đã ghi {MANIFEST.relative_to(REPO_ROOT)}")

    n_1h = sum(1 for c in cropped if c["layout"] == "bien_1hang")
    print(f"\nBố cục: {n_1h} biển 1 dòng, {len(cropped) - n_1h} biển 2 dòng")
    ppr = np.array([c["px_per_row"] for c in cropped])
    print(f"px/dòng: trung vị {np.median(ppr):.0f}, tỉ lệ >=40px: {(ppr >= 40).mean():.1%}")


if __name__ == "__main__":
    main()
