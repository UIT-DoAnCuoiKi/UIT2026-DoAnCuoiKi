"""Dựng tập dữ liệu phân loại LOẠI XE THÔ (motorbike/car/truck) từ
`data/raw/kaggle_vn_plate_segment`, thay cho việc dùng thẳng nhãn lớp của
YOLOv8n pretrained COCO (không train lại, sai nhiều với ảnh cận cảnh kiểu
camera cổng — xem `predict_vehicle.detect_vehicle_crop`).

Dataset gốc chia sẵn theo 5 tiền tố tên file, nội dung rất khác nhau — đã xem
tay xác nhận:
  - `carlong_*`  (989 ảnh, cả train+val gộp): ô tô cận cảnh kiểu camera
    barrier/gờ giảm tốc, thuần 1 loại (xem tay ~15 ảnh rải rác, 15/15 ô tô).
  - `greenpack_*` (1747 ảnh): xe máy cận cảnh kiểu CCTV cổng, thuần 1 loại
    (xem tay ~15 ảnh, 15/15 xe máy).
  - `Dieu_*`/`Hung_*` (925 ảnh gộp): ảnh phố hỗn hợp, nhiều loại xe lẫn hậu
    cảnh lộn xộn — không có thư mục riêng cho xe tải.
  - `Tgmt_*` (917 ảnh): cắt cực sát chỉ thấy biển + góc ca-lăng, không thấy
    dáng xe — không dùng được cho phân loại loại xe.

Xe tải KHÔNG có thư mục riêng, phải lọc từ Dieu_/Hung_. Đã dùng
YOLOv8n pretrained (predict_vehicle.detect_vehicle_crop) quét toàn bộ 925 ảnh
để ra 151 ứng viên có nhãn "truck" — rồi xem tay TỪNG ảnh trong 151 ứng viên
đó, vì độ tin cậy của detector này KHÔNG đáng tin để lọc tự động (dương tính
giả rải đều mọi mức điểm, kể cả điểm cao — vd 1 ảnh Toyota Camry vẫn ra
"truck" 0.79). Tiêu chí nhận: xe tải là chủ thể chính, không phải xe con/SUV/
van/xe khách, không phải chỉ lấp ló hậu cảnh trong khi chủ thể chính là xe
khác. Kết quả: 73/151 đạt (danh sách `_TRUCK_ACCEPTED` dưới, cố định — không
random để tái lập đúng lần xem tay đã làm, xem thêm biên bản đầy đủ 151 dòng
tại scratchpad `truck_review_manifest.csv` lúc làm việc này).

QUAN TRỌNG — lỗi đã phát hiện sau lần train đầu: bản đầu chỉ lấy car từ
carlong_ và motorbike từ greenpack_ (mỗi lớp đúng 1 nguồn/1 kiểu camera).
Model học theo "phong cách ảnh/camera" thay vì hình dáng xe — mọi ảnh kiểu
đường phố (Dieu_/Hung_) đều bị đoán thành "truck" bất kể là xe gì, vì truck
là lớp DUY NHẤT có ảnh đường phố lúc đó. Kiểm tra thật trên ảnh Dieu_/Hung_
ngoài tập train: sai 12/13. Để sửa: bổ sung thêm ảnh car/motorbike LẤY TỪ
Dieu_/Hung_ (đường phố) trộn cùng carlong_/greenpack_ (cận cảnh cổng), để mỗi
lớp có đủ cả 2 phong cách ảnh — model buộc phải học hình dáng xe thật.
  - `_CAR_EXTRA_ACCEPTED` (92 ảnh): lấy mẫu 128 ứng viên "car" từ scan
    YOLOv8n trên Dieu_/Hung_ (216 ứng viên gốc), xem tay từng ảnh, tiêu chí
    như xe tải (ô tô là chủ thể chính, không phải chỉ lấp ló hậu cảnh khi
    chủ thể chính là xe máy; loại luôn vài ảnh detector nhầm xe tải/xe đạp
    thành "car"). 92/128 đạt.
  - `_MOTORBIKE_EXTRA_ACCEPTED` (128 ảnh): lấy mẫu 128 ứng viên "motorcycle"
    (481 ứng viên gốc), xem tay — độ chính xác cao hơn hẳn (128/128 đạt,
    không có dương tính giả nào), vì xe máy có hình dáng đặc trưng hơn nhiều
    so với xe tải/van dễ nhầm với ô tô.

Vì xe tải chỉ có 73 ảnh (so với car/motorbike lấy được hàng trăm), tỉ lệ chia
train/valid/test dùng chung 1 công thức theo % cho cả 3 lớp thay vì cố định
số lượng, để lớp thiếu dữ liệu không bị lệch tỉ lệ so với 2 lớp còn lại.

Chạy: .venv/Scripts/python.exe src/ml/data_prep/prepare_vehicle_type_dataset.py
Ghi ra: data/processed/vehicle-type/{train,valid,test}/{motorbike,car,truck}/
        data/processed/vehicle-type/manifest.csv (nguồn -> đích, để truy vết)
"""
from __future__ import annotations

import csv
import random
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment" / "images"
OUT_DIR = REPO_ROOT / "data" / "processed" / "vehicle-type"

SEED = 2026
N_CAR = 350       # carlong_ có 989 ảnh, đủ dư
N_MOTORBIKE = 350  # greenpack_ có 1747 ảnh, đủ dư
# Tỉ lệ chia áp dụng chung cho cả 3 lớp (xem docstring trên).
TRAIN_FRAC, VALID_FRAC = 0.70, 0.15  # phần còn lại (0.15) là test

# 73 ảnh xe tải đã xem tay xác nhận (split trong ngoặc là split GỐC của
# kaggle_vn_plate_segment, không liên quan tới split train/valid/test mới
# dựng ở đây). Xem docstring đầu file về tiêu chí nhận.
_TRUCK_ACCEPTED: list[tuple[str, str]] = [
    ("train", "Dieu_0011.png"), ("train", "Dieu_0012.png"), ("val", "Dieu_0018.png"),
    ("train", "Dieu_0024.png"), ("val", "Dieu_0035.png"), ("train", "Dieu_0036.png"),
    ("val", "Dieu_0101.png"), ("train", "Dieu_0109.png"), ("val", "Dieu_0140.png"),
    ("train", "Dieu_0157.png"), ("train", "Dieu_0198.png"), ("train", "Dieu_0204.png"),
    ("val", "Dieu_0207.png"), ("train", "Dieu_0221.png"), ("train", "Dieu_0222.png"),
    ("train", "Dieu_0226.png"), ("train", "Dieu_0228.png"), ("train", "Dieu_0232.png"),
    ("val", "Dieu_0234.png"), ("train", "Dieu_0235.png"), ("val", "Dieu_0239.png"),
    ("train", "Dieu_0241.png"), ("train", "Dieu_0242.png"), ("train", "Dieu_0246.png"),
    ("train", "Dieu_0247.png"), ("train", "Dieu_0252.png"), ("train", "Dieu_0256.png"),
    ("train", "Dieu_0259.png"), ("train", "Dieu_0260.png"), ("train", "Dieu_0261.png"),
    ("train", "Dieu_0280.png"), ("val", "Dieu_0288.png"), ("val", "Dieu_0292.png"),
    ("train", "Dieu_0295.png"), ("train", "Dieu_0296.png"), ("train", "Dieu_0299.png"),
    ("train", "Dieu_0301.png"), ("train", "Dieu_0302.png"), ("train", "Dieu_0304.png"),
    ("train", "Dieu_0307.png"), ("train", "Dieu_0310.png"), ("train", "Dieu_0311.png"),
    ("train", "Dieu_0313.png"), ("val", "Dieu_0323.png"), ("train", "Dieu_0327.png"),
    ("val", "Dieu_0330.png"), ("train", "Dieu_0334.png"), ("train", "Dieu_0336.png"),
    ("train", "Dieu_0375.png"), ("train", "Dieu_0377.png"), ("train", "Dieu_0408.png"),
    ("train", "Dieu_0411.png"), ("val", "Dieu_0413.png"), ("train", "Hung_0002.png"),
    ("train", "Hung_0017.png"), ("val", "Hung_0018.png"), ("train", "Hung_0022.png"),
    ("train", "Hung_0024.png"), ("val", "Hung_0025.png"), ("train", "Hung_0026.png"),
    ("train", "Hung_0044.png"), ("train", "Hung_0045.png"), ("train", "Hung_0050.png"),
    ("train", "Hung_0079.png"), ("train", "Hung_0083.png"), ("train", "Hung_0106.png"),
    ("val", "Hung_0110.png"), ("train", "Hung_0112.png"), ("train", "Hung_0128.png"),
    ("train", "Hung_0135.png"), ("train", "Hung_0304.png"), ("val", "Hung_0327.png"),
    ("train", "Hung_0362.png"),
]

# 92 anh o to lay tu Dieu_/Hung_ (duong pho), xem tay tung anh trong mau 128
# ung vien "car" cua scan YOLOv8n (xem docstring dau file).
_CAR_EXTRA_ACCEPTED: list[tuple[str, str]] = [
    ("train", "Dieu_0001.png"), ("train", "Dieu_0004.png"), ("train", "Dieu_0008.png"),
    ("train", "Dieu_0015.png"), ("train", "Dieu_0019.png"), ("val", "Dieu_0037.png"),
    ("train", "Dieu_0048.png"), ("val", "Dieu_0079.png"), ("val", "Dieu_0083.png"),
    ("train", "Dieu_0090.png"), ("val", "Dieu_0097.png"), ("train", "Dieu_0100.png"),
    ("train", "Dieu_0126.png"), ("val", "Dieu_0137.png"), ("train", "Dieu_0142.png"),
    ("train", "Dieu_0143.png"), ("train", "Dieu_0148.png"), ("train", "Dieu_0149.png"),
    ("val", "Dieu_0188.png"), ("train", "Dieu_0192.png"), ("val", "Dieu_0195.png"),
    ("val", "Dieu_0196.png"), ("val", "Dieu_0200.png"), ("val", "Dieu_0210.png"),
    ("train", "Dieu_0211.png"), ("train", "Dieu_0213.png"), ("val", "Dieu_0220.png"),
    ("train", "Dieu_0225.png"), ("train", "Dieu_0250.png"), ("val", "Dieu_0257.png"),
    ("val", "Dieu_0265.png"), ("train", "Dieu_0266.png"), ("train", "Dieu_0268.png"),
    ("train", "Dieu_0270.png"), ("val", "Dieu_0273.png"), ("train", "Dieu_0282.png"),
    ("train", "Dieu_0284.png"), ("val", "Dieu_0289.png"), ("train", "Dieu_0291.png"),
    ("train", "Dieu_0293.png"), ("train", "Dieu_0297.png"), ("train", "Dieu_0303.png"),
    ("train", "Dieu_0318.png"), ("train", "Dieu_0320.png"), ("train", "Dieu_0325.png"),
    ("val", "Dieu_0335.png"), ("train", "Dieu_0338.png"), ("train", "Dieu_0345.png"),
    ("val", "Dieu_0350.png"), ("train", "Dieu_0361.png"), ("train", "Dieu_0362.png"),
    ("train", "Dieu_0365.png"), ("train", "Dieu_0379.png"), ("train", "Dieu_0403.png"),
    ("train", "Hung_0007.png"), ("val", "Hung_0011.png"), ("train", "Hung_0028.png"),
    ("train", "Hung_0046.png"), ("train", "Hung_0056.png"), ("train", "Hung_0076.png"),
    ("train", "Hung_0084.png"), ("train", "Hung_0085.png"), ("train", "Hung_0094.png"),
    ("val", "Hung_0095.png"), ("train", "Hung_0111.png"), ("train", "Hung_0125.png"),
    ("train", "Hung_0126.png"), ("train", "Hung_0127.png"), ("train", "Hung_0132.png"),
    ("train", "Hung_0146.png"), ("val", "Hung_0151.png"), ("train", "Hung_0152.png"),
    ("train", "Hung_0153.png"), ("train", "Hung_0154.png"), ("train", "Hung_0155.png"),
    ("train", "Hung_0220.png"), ("train", "Hung_0233.png"), ("val", "Hung_0284.png"),
    ("val", "Hung_0289.png"), ("train", "Hung_0298.png"), ("val", "Hung_0306.png"),
    ("train", "Hung_0318.png"), ("train", "Hung_0349.png"), ("train", "Hung_0357.png"),
    ("val", "Hung_0360.png"), ("val", "Hung_0361.png"), ("train", "Hung_0363.png"),
    ("train", "Hung_0368.png"), ("train", "Hung_0438.png"), ("train", "Hung_0441.png"),
    ("train", "Hung_0442.png"), ("train", "Hung_0445.png"),
]

# 128 anh xe may lay tu Dieu_/Hung_ (duong pho): mau 128 ung vien "motorcycle"
# xem tay ca 128, KHONG co duong tinh gia nao ca (khac han xe tai/o to - xe
# may co hinh dang de nhan hon nhieu doi voi detector nay).
_MOTORBIKE_EXTRA_ACCEPTED: list[tuple[str, str]] = [
    ("train", "Dieu_0007.png"), ("train", "Dieu_0010.png"), ("train", "Dieu_0033.png"),
    ("train", "Dieu_0045.png"), ("train", "Dieu_0057.png"), ("train", "Dieu_0066.png"),
    ("train", "Dieu_0081.png"), ("train", "Dieu_0094.png"), ("train", "Dieu_0107.png"),
    ("val", "Dieu_0112.png"), ("train", "Dieu_0117.png"), ("val", "Dieu_0120.png"),
    ("train", "Dieu_0123.png"), ("train", "Dieu_0127.png"), ("train", "Dieu_0138.png"),
    ("val", "Dieu_0141.png"), ("train", "Dieu_0144.png"), ("train", "Dieu_0145.png"),
    ("train", "Dieu_0155.png"), ("train", "Dieu_0168.png"), ("train", "Dieu_0169.png"),
    ("train", "Dieu_0177.png"), ("train", "Dieu_0180.png"), ("train", "Dieu_0202.png"),
    ("train", "Dieu_0215.png"), ("val", "Dieu_0240.png"), ("val", "Dieu_0249.png"),
    ("train", "Dieu_0258.png"), ("train", "Dieu_0277.png"), ("train", "Dieu_0283.png"),
    ("val", "Dieu_0309.png"), ("train", "Dieu_0326.png"), ("val", "Dieu_0340.png"),
    ("train", "Dieu_0346.png"), ("train", "Dieu_0354.png"), ("train", "Dieu_0356.png"),
    ("train", "Dieu_0357.png"), ("train", "Dieu_0372.png"), ("val", "Dieu_0381.png"),
    ("val", "Dieu_0383.png"), ("val", "Dieu_0385.png"), ("train", "Dieu_0390.png"),
    ("train", "Dieu_0396.png"), ("val", "Dieu_0416.png"), ("train", "Dieu_0418.png"),
    ("train", "Dieu_0429.png"), ("val", "Dieu_0435.png"), ("train", "Dieu_0436.png"),
    ("train", "Dieu_0437.png"), ("val", "Dieu_0443.png"), ("train", "Dieu_0456.png"),
    ("train", "Dieu_0469.png"), ("train", "Dieu_0471.png"), ("train", "Dieu_0477.png"),
    ("train", "Dieu_0480.png"), ("train", "Dieu_0484.png"), ("train", "Dieu_0485.png"),
    ("val", "Dieu_0492.png"), ("val", "Dieu_0494.png"), ("train", "Hung_0006.png"),
    ("train", "Hung_0033.png"), ("train", "Hung_0036.png"), ("train", "Hung_0042.png"),
    ("train", "Hung_0065.png"), ("train", "Hung_0069.png"), ("val", "Hung_0082.png"),
    ("train", "Hung_0102.png"), ("val", "Hung_0114.png"), ("val", "Hung_0117.png"),
    ("train", "Hung_0121.png"), ("val", "Hung_0122.png"), ("train", "Hung_0141.png"),
    ("val", "Hung_0143.png"), ("train", "Hung_0158.png"), ("train", "Hung_0168.png"),
    ("train", "Hung_0174.png"), ("train", "Hung_0177.png"), ("val", "Hung_0178.png"),
    ("val", "Hung_0182.png"), ("train", "Hung_0187.png"), ("train", "Hung_0188.png"),
    ("train", "Hung_0193.png"), ("train", "Hung_0199.png"), ("val", "Hung_0200.png"),
    ("train", "Hung_0204.png"), ("train", "Hung_0205.png"), ("train", "Hung_0207.png"),
    ("val", "Hung_0213.png"), ("train", "Hung_0217.png"), ("train", "Hung_0224.png"),
    ("train", "Hung_0225.png"), ("train", "Hung_0228.png"), ("train", "Hung_0229.png"),
    ("train", "Hung_0232.png"), ("val", "Hung_0236.png"), ("train", "Hung_0240.png"),
    ("train", "Hung_0252.png"), ("train", "Hung_0272.png"), ("train", "Hung_0275.png"),
    ("train", "Hung_0300.png"), ("train", "Hung_0311.png"), ("train", "Hung_0314.png"),
    ("train", "Hung_0321.png"), ("train", "Hung_0323.png"), ("train", "Hung_0329.png"),
    ("train", "Hung_0332.png"), ("train", "Hung_0333.png"), ("train", "Hung_0346.png"),
    ("train", "Hung_0356.png"), ("val", "Hung_0370.png"), ("train", "Hung_0371.png"),
    ("val", "Hung_0372.png"), ("train", "Hung_0373.png"), ("train", "Hung_0382.png"),
    ("train", "Hung_0388.png"), ("val", "Hung_0390.png"), ("train", "Hung_0394.png"),
    ("train", "Hung_0396.png"), ("train", "Hung_0407.png"), ("train", "Hung_0408.png"),
    ("val", "Hung_0409.png"), ("train", "Hung_0412.png"), ("val", "Hung_0417.png"),
    ("train", "Hung_0421.png"), ("train", "Hung_0425.png"), ("train", "Hung_0429.png"),
    ("train", "Hung_0430.png"), ("train", "Hung_0431.png"),
]


def _list_prefixed(prefix: str) -> list[tuple[str, str]]:
    """Trả (split_goc, filename) cho mọi ảnh có tiền tố cho trước, gộp cả
    train+val của dataset gốc (split gốc không liên quan split mới ở đây)."""
    out = []
    for split in ("train", "val"):
        d = SRC_DIR / split
        for f in sorted(d.iterdir()):
            if f.name.startswith(prefix):
                out.append((split, f.name))
    return out


def _split_train_valid_test(items: list, seed: int) -> dict[str, list]:
    rng = random.Random(seed)
    shuffled = items[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = round(n * TRAIN_FRAC)
    n_valid = round(n * VALID_FRAC)
    return {
        "train": shuffled[:n_train],
        "valid": shuffled[n_train:n_train + n_valid],
        "test": shuffled[n_train + n_valid:],
    }


def main() -> None:
    rng = random.Random(SEED)

    car_pool = _list_prefixed("carlong_")
    moto_pool = _list_prefixed("greenpack_")
    # Cong don ca nguon cong barrier/CCTV thuan (carlong_/greenpack_) LAN
    # nguon duong pho (Dieu_/Hung_) cho moi lop car/motorbike, de model khong
    # con hoc tat theo phong cach anh (xem canh bao dau file).
    car_items = rng.sample(car_pool, min(N_CAR, len(car_pool))) + list(_CAR_EXTRA_ACCEPTED)
    moto_items = rng.sample(moto_pool, min(N_MOTORBIKE, len(moto_pool))) + list(_MOTORBIKE_EXTRA_ACCEPTED)
    truck_items = list(_TRUCK_ACCEPTED)

    classes = {"car": car_items, "motorbike": moto_items, "truck": truck_items}

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    manifest_rows = []
    for cls_name, items in classes.items():
        splits = _split_train_valid_test(items, seed=SEED)
        for split_name, split_items in splits.items():
            dest_dir = OUT_DIR / split_name / cls_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            for src_split, filename in split_items:
                src_path = SRC_DIR / src_split / filename
                dest_path = dest_dir / filename
                shutil.copy2(src_path, dest_path)
                manifest_rows.append({
                    "class": cls_name, "split": split_name,
                    "source_split": src_split, "filename": filename,
                    "source_path": str(src_path.relative_to(REPO_ROOT)),
                    "dest_path": str(dest_path.relative_to(REPO_ROOT)),
                })
        print(f"{cls_name}: train={len(splits['train'])} valid={len(splits['valid'])} "
              f"test={len(splits['test'])} (tong {len(items)})")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(manifest_rows[0].keys()))
        w.writeheader()
        w.writerows(manifest_rows)
    print(f"Da ghi {len(manifest_rows)} anh vao {OUT_DIR}")
    print(f"Manifest: {OUT_DIR / 'manifest.csv'}")


if __name__ == "__main__":
    main()
