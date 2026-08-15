"""Kiểm tra riêng OCR trên biển 2 dòng cắt từ A1, có nắn phối cảnh.

Biển 2 dòng (xe máy) là loại chiếm đa số ở bãi giữ xe và cũng là loại khó hơn
biển 1 dòng, vì phụ thuộc thêm bước tách dòng. Script này lấy mẫu trải đều
theo độ phân giải (thay vì chỉ lấy nhóm nét nhất) rồi xuất lưới ảnh kèm chuỗi
đọc được, để đối chiếu tay và đếm accuracy thật.

Chạy: .venv/Scripts/python.exe src/ml/eval_ocr_2row.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))
sys.path.insert(0, str(REPO_ROOT / "src" / "ml"))

from eval_ocr_on_a1 import crop_plates, save_montage  # noqa: E402
from pipeline.ocr import CRNNRecognizer, perspective_correct, read_plate  # noqa: E402

FIG_DIR = REPO_ROOT / "docs" / "report" / "figures"

# Lấy mẫu theo dải độ phân giải để thấy cả trường hợp dễ lẫn khó, mỗi dải một
# số lượng cố định thay vì lấy ngẫu nhiên toàn bộ (vốn nghiêng về ảnh nhỏ)
BANDS = [(20, 30), (30, 45), (45, 70), (70, 1e9)]
PER_BAND = 6


def main() -> None:
    plates = [p for p in crop_plates("val", limit=400) if p["layout"] == "bien_2hang"]
    print(f"Tổng biển 2 dòng cắt được: {len(plates)}")

    recognizer = CRNNRecognizer(REPO_ROOT / "src" / "ml" / "weights" / "plate-ocr-crnn.pt")

    picked = []
    for lo, hi in BANDS:
        band = [p for p in plates if lo <= p["px_per_row"] < hi]
        band.sort(key=lambda p: -p["px_per_row"])
        step = max(1, len(band) // PER_BAND)
        chosen = band[::step][:PER_BAND]
        label = f">={lo}px" if hi > 1e8 else f"{lo}-{hi}px"
        print(f"  dải {label:9s}: có {len(band):3d} biển, lấy {len(chosen)}")
        picked.extend(chosen)

    items = []
    for p in picked:
        warped = perspective_correct(p["crop"], p["corners"])
        reading = read_plate(p["crop"], recognizer, layout="bien_2hang", corners=p["corners"])
        items.append({"crop": warped, "pred": reading.text_normalized,
                      "px_per_row": p["px_per_row"]})

    out = FIG_DIR / "plate_ocr_2row_montage.png"
    save_montage(items, out, cols=6)
    print(f"\nĐã lưu lưới {len(items)} biển 2 dòng: {out.relative_to(REPO_ROOT)}")

    # Thống kê trên toàn bộ biển 2 dòng, không chỉ mẫu đã chọn
    valid = 0
    for p in plates:
        r = read_plate(p["crop"], recognizer, layout="bien_2hang", corners=p["corners"])
        valid += r.valid_format
    print(f"Khớp định dạng trên toàn bộ {len(plates)} biển 2 dòng: {valid / len(plates):.1%}")


if __name__ == "__main__":
    main()
