"""Chuẩn bị dữ liệu huấn luyện cho bộ phân loại kiểu dáng xe con.

Nguồn: B5 (Vehicle Body Style Dataset). Cắt từng xe theo bounding box gốc
kèm biên 10%, gộp 12 kiểu dáng gốc thành 3 nhóm phù hợp vận hành bãi xe:
  - Sedan:  Sedan, Fastback, Hatchback, Wagon, Convertible,
            Hardtop Convertible, Sports (thân thấp, gọn)
  - GamCao: SUV, Crossover, MPV, Minibus (gầm cao, thân cao)
  - XeTai:  Pickup Truck

Giữ nguyên split train/valid/test sẵn có của B5 (Roboflow export), không tự
chia lại, để kết quả giữa các lần chạy so sánh được với nhau.

Chạy: .venv/Scripts/python.exe src/ml/data_prep/prepare_classification_data.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import cv2
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
CLASSES_OUT_DIR = REPO_ROOT / "src" / "ml" / "data"

SPLITS = ("train", "valid", "test")
CROP_SIZE = 256  # kích thước ảnh crop lưu ra; lúc huấn luyện mới cắt tiếp về 224
PADDING_FRAC = 0.10  # biên thêm quanh mỗi bbox, tính theo tỉ lệ cạnh của box

STYLE_DIR = DATA_PROCESSED / "vehicle-style"

# Tên lớp gốc của B5 -> nhóm gộp
STYLE_NAME_MAP = {
    "Sedan": "Sedan", "Fastback": "Sedan", "Hatchback": "Sedan", "Wagon": "Sedan",
    "Convertible": "Sedan", "Hardtop Convertible": "Sedan", "Sports": "Sedan",
    "SUV": "GamCao", "Crossover": "GamCao", "MPV": "GamCao", "Minibus": "GamCao",
    "Pickup Truck": "XeTai",
}
STYLE_CLASSES = ["Sedan", "GamCao", "XeTai"]


def load_yolo_classes(dataset_dir: Path) -> list[str]:
    with open(dataset_dir / "data.yaml", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d["names"]


def crop_boxes(
    dataset_dir: Path,
    split: str,
    raw_names: list[str],
    name_map: dict[str, str],
    out_root: Path,
    counts: Counter,
) -> None:
    images_dir = dataset_dir / split / "images"
    labels_dir = dataset_dir / split / "labels"
    if not images_dir.exists():
        print(f"  [bỏ qua] không thấy {images_dir}")
        return

    for label_path in sorted(labels_dir.glob("*.txt")):
        img_path = next(
            (images_dir / (label_path.stem + ext) for ext in (".jpg", ".jpeg", ".png")
             if (images_dir / (label_path.stem + ext)).exists()),
            None,
        )
        if img_path is None:
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]

        lines = label_path.read_text(encoding="utf-8").strip().splitlines()
        for i, line in enumerate(lines):
            parts = line.split()
            if len(parts) < 5:
                continue
            cls_id = int(parts[0])
            xc, yc, bw, bh = (float(v) for v in parts[1:5])
            raw_name = raw_names[cls_id]
            if raw_name not in name_map:
                continue
            class_name = name_map[raw_name]

            box_w, box_h = bw * w, bh * h
            cx, cy = xc * w, yc * h
            pad_w, pad_h = box_w * PADDING_FRAC, box_h * PADDING_FRAC
            x1 = max(0, int(cx - box_w / 2 - pad_w))
            y1 = max(0, int(cy - box_h / 2 - pad_h))
            x2 = min(w, int(cx + box_w / 2 + pad_w))
            y2 = min(h, int(cy + box_h / 2 + pad_h))
            if x2 <= x1 or y2 <= y1:
                continue

            crop = img[y1:y2, x1:x2]
            crop = cv2.resize(crop, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_AREA)

            out_dir = out_root / split / class_name
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{img_path.stem}_{i}.jpg"
            cv2.imwrite(str(out_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            counts[(split, class_name)] += 1


def main() -> None:
    dataset_dir = DATA_RAW / "vehicle_body_style"
    if STYLE_DIR.exists():
        print(f"[cảnh báo] {STYLE_DIR} đã tồn tại, ảnh mới sẽ ghi đè hoặc trộn với ảnh cũ.")

    raw_names = load_yolo_classes(dataset_dir)
    print(f"B5 có {len(raw_names)} kiểu dáng gốc: {raw_names}")
    print(f"Gộp thành {len(STYLE_CLASSES)} nhóm: {STYLE_CLASSES}")

    counts: Counter = Counter()
    for split in SPLITS:
        crop_boxes(dataset_dir, split, raw_names, STYLE_NAME_MAP, STYLE_DIR, counts)

    CLASSES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Ghi theo thứ tự bảng chữ cái để khớp đúng thứ tự nhãn mà ImageFolder tạo
    # ra lúc huấn luyện. Thứ tự trong STYLE_CLASSES chỉ để hiển thị cho dễ đọc,
    # không phải thứ tự nhãn thật của model.
    (CLASSES_OUT_DIR / "vehicle-style-classes.json").write_text(
        json.dumps(sorted(STYLE_CLASSES), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nSố ảnh đã crop, theo lớp và split:")
    for split in SPLITS:
        print(f"  [{split}]")
        for cls in STYLE_CLASSES:
            print(f"    {cls:10s} {counts.get((split, cls), 0)}")
    print(f"\nTổng: {sum(counts.values())}")


if __name__ == "__main__":
    main()
