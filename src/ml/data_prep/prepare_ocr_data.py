"""Chuẩn bị dữ liệu huấn luyện/đánh giá cho module OCR đọc ký tự biển số.

Nguồn:
  - topkek_plate_ocr (Kaggle topkek69/vietnamese-license-plate-ocr): crop biển
    thật (`cropped/`, `labels/crop_labels.csv`) và crop biển sinh tổng hợp
    (`generated/`, `labels/gen_labels.csv`). Nhãn dạng "30F 11292" (chuỗi có
    khoảng trắng ngăn seri và số thứ tự, không phân biệt biển 1 hay 2 dòng).
  - dtkngan_motorbike_ocr_100 (Kaggle dtkngan/100-bien-so-xe-may-ocr): 116 ảnh
    biển xe máy 2 dòng thật, nhãn trong file .txt riêng dạng "59E12150" (không
    khoảng trắng). Dùng làm tập test biển 2 dòng độc lập với topkek.

Layout biển (1 dòng / 2 dòng) không có nhãn sẵn trong topkek, nên suy ra từ tỉ
lệ khung ảnh (aspect ratio width/height) theo cùng ngưỡng dùng lúc suy luận
(< 2.0 coi là 2 dòng), khớp tên lớp `bien_1hang`/`bien_2hang` mà detector của
Đức xuất ra, để code đánh giá và code suy luận dùng chung một quy ước.

Ghi ra data/processed/plate-ocr/:
  train.csv, val.csv, test.csv   - crop thật topkek, chia theo layout (80/10/10)
  train_synthetic.csv            - crop sinh tổng hợp topkek, chỉ để augment
                                    lúc train, không dùng để đánh giá
  test_motorbike_2row.csv        - 115 ảnh dtkngan, tập test biển 2 dòng riêng

Mỗi CSV có cột: image_path (tương đối REPO_ROOT), label_raw, label_clean (chữ
hoa, bỏ khoảng trắng/dấu phân cách), layout, width, height, source.

Chạy: .venv/Scripts/python.exe src/ml/data_prep/prepare_ocr_data.py
"""

from __future__ import annotations

import csv
import random
import re
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
TOPKEK_DIR = REPO_ROOT / "data" / "raw" / "topkek_plate_ocr"
DTKNGAN_DIR = REPO_ROOT / "data" / "raw" / "dtkngan_motorbike_ocr_100" / "biensoxemayhon100bien"
OUT_DIR = REPO_ROOT / "data" / "processed" / "plate-ocr"

ASPECT_2ROW_THRESHOLD = 2.0  # width/height < ngưỡng này -> coi là biển 2 dòng
SPLIT_RATIOS = (0.8, 0.1, 0.1)  # train, val, test
SEED = 42

FIELDS = ["image_path", "label_raw", "label_clean", "layout", "width", "height", "source"]


def clean_label(raw: str) -> str:
    """Chuẩn hoá nhãn về chuỗi ký tự thuần: chữ hoa, bỏ khoảng trắng/dấu nối."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def layout_from_aspect(width: int, height: int) -> str:
    aspect = width / height
    return "bien_1hang" if aspect >= ASPECT_2ROW_THRESHOLD else "bien_2hang"


def load_topkek_csv(csv_path: Path, images_dir: Path, source: str) -> list[dict]:
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name, raw = r["Name"].strip(), r["Label"].strip()
            if not name or not raw:
                continue
            img_path = images_dir / name
            if not img_path.exists():
                continue
            with Image.open(img_path) as img:
                w, h = img.size
            rows.append({
                "image_path": str(img_path.relative_to(REPO_ROOT)),
                "label_raw": raw,
                "label_clean": clean_label(raw),
                "layout": layout_from_aspect(w, h),
                "width": w, "height": h,
                "source": source,
            })
    return rows


def load_dtkngan(base_dir: Path) -> list[dict]:
    images_dir, labels_dir = base_dir / "anh", base_dir / "label"
    img_stems = {p.stem: p for p in images_dir.glob("*.jpg")}
    label_stems = {p.stem: p for p in labels_dir.glob("*.txt")}
    rows = []
    for stem in sorted(img_stems.keys() & label_stems.keys()):
        img_path = img_stems[stem]
        raw = label_stems[stem].read_text(encoding="utf-8").strip()
        if not raw:
            continue
        with Image.open(img_path) as img:
            w, h = img.size
        rows.append({
            "image_path": str(img_path.relative_to(REPO_ROOT)),
            "label_raw": raw,
            "label_clean": clean_label(raw),
            "layout": "bien_2hang",  # toàn bộ dataset này là biển xe máy 2 dòng
            "width": w, "height": h,
            "source": "dtkngan_2row_test",
        })
    return rows


def stratified_split(rows: list[dict], ratios: tuple[float, float, float], seed: int):
    rng = random.Random(seed)
    by_layout: dict[str, list[dict]] = {}
    for row in rows:
        by_layout.setdefault(row["layout"], []).append(row)

    train, val, test = [], [], []
    for layout_rows in by_layout.values():
        rng.shuffle(layout_rows)
        n = len(layout_rows)
        n_train = int(n * ratios[0])
        n_val = int(n * ratios[1])
        train.extend(layout_rows[:n_train])
        val.extend(layout_rows[n_train:n_train + n_val])
        test.extend(layout_rows[n_train + n_val:])
    return train, val, test


def write_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    real = load_topkek_csv(
        TOPKEK_DIR / "labels" / "crop_labels.csv", TOPKEK_DIR / "cropped", "topkek_real"
    )
    synthetic = load_topkek_csv(
        TOPKEK_DIR / "labels" / "gen_labels.csv", TOPKEK_DIR / "generated", "topkek_synthetic"
    )
    motorbike_test = load_dtkngan(DTKNGAN_DIR)

    print(f"topkek crop thật: {len(real)} ảnh")
    print(f"topkek sinh tổng hợp: {len(synthetic)} ảnh (chỉ dùng để augment, không đánh giá)")
    print(f"dtkngan biển xe máy 2 dòng: {len(motorbike_test)} ảnh (tập test riêng)")

    train, val, test = stratified_split(real, SPLIT_RATIOS, SEED)
    for name, rows in (("train", train), ("val", val), ("test", test)):
        n_1hang = sum(1 for r in rows if r["layout"] == "bien_1hang")
        n_2hang = len(rows) - n_1hang
        print(f"  {name:5s}: {len(rows):5d} ảnh (1 hàng={n_1hang}, 2 hàng={n_2hang})")

    write_csv(train, OUT_DIR / "train.csv")
    write_csv(val, OUT_DIR / "val.csv")
    write_csv(test, OUT_DIR / "test.csv")
    write_csv(synthetic, OUT_DIR / "train_synthetic.csv")
    write_csv(motorbike_test, OUT_DIR / "test_motorbike_2row.csv")
    print(f"\nĐã ghi CSV vào {OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
