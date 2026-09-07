"""Kiểm tra model phân loại loại xe (vehicle-type) trên ảnh NGOÀI phân phối
train — tức ảnh chưa từng dùng để train/valid/test, khác cả nguồn lẫn phong
cách chụp so với dữ liệu huấn luyện.

Vì sao cần script này: lần train đầu tiên đạt accuracy 100% trên tập test,
nhưng test set đó lấy mẫu từ ĐÚNG các nguồn đã dùng để train (carlong_ cho
car, greenpack_ cho motorbike) — không hề kiểm tra được việc model có học
đúng "hình dáng xe" hay chỉ học tắt theo "phong cách ảnh/camera". Chạy đúng
12 ảnh dưới đây (toàn bộ lấy từ Dieu_/Hung_, xem tay biết chắc nhãn thật,
XÁC NHẬN không nằm trong danh sách đã dùng train ở prepare_vehicle_type_dataset.py)
với model của lần train đầu: sai 12/13 — mọi ảnh phong cách "đường phố" đều
bị đoán thành "truck" bất kể là xe gì, vì truck là lớp DUY NHẤT có ảnh đường
phố lúc đó. Sau khi bổ sung ảnh car/motorbike từ Dieu_/Hung_ vào dataset
(xem prepare_vehicle_type_dataset.py), chạy lại: resnet18 13/13 (100%),
mobilenet_v3_small 12/13 (92%).

Dùng script này mỗi khi đổi dataset/kiến trúc cho bài toán vehicle-type, để
tránh lặp lại đúng lỗi này (test set không độc lập với nguồn train).

Chạy: .venv/Scripts/python.exe src/ml/sanity_check_vehicle_type_ood.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))

import torch  # noqa: E402
from PIL import Image  # noqa: E402

from classifier import build_model, build_transforms  # noqa: E402

DATA_TRAIN = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment" / "images" / "train"
DATA_VAL = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment" / "images" / "val"
WEIGHTS_DIR = REPO_ROOT / "src" / "ml" / "weights"
MODELS = ["resnet18", "mobilenet_v3_small"]

# Ảnh xe con và xe máy lấy từ Dieu_/Hung_ (KHÔNG phải carlong_/greenpack_),
# nhãn thật biết trước qua xem tay. Đã xác nhận KHÔNG nằm trong danh sách
# _CAR_EXTRA_ACCEPTED / _MOTORBIKE_EXTRA_ACCEPTED của prepare_vehicle_type_dataset.py
# (giữ làm holdout độc lập thật sự, đừng vô tình thêm các file này vào train).
TEST_CASES: list[tuple[Path, str]] = [
    (DATA_TRAIN / "Dieu_0028.png", "car"),        # Subaru SUV
    (DATA_TRAIN / "Dieu_0146.png", "car"),        # red Kia Seltos SUV
    (DATA_TRAIN / "Dieu_0059.png", "car"),        # white Mitsubishi Pajero SUV
    (DATA_TRAIN / "Dieu_0167.png", "car"),        # red Kia Seltos
    (DATA_TRAIN / "Hung_0009.png", "car"),        # black Toyota Fortuner
    (DATA_TRAIN / "Hung_0058.png", "car"),        # maroon Honda CR-V
    (DATA_TRAIN / "Dieu_0074.png", "motorbike"),  # motorbike, pickup in bg
    (DATA_TRAIN / "Dieu_0104.png", "motorbike"),
    (DATA_TRAIN / "Dieu_0136.png", "motorbike"),
    (DATA_TRAIN / "Hung_0048.png", "motorbike"),
    (DATA_TRAIN / "Hung_0136.png", "motorbike"),
    (DATA_VAL / "Hung_0293.png", "motorbike"),
]


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    transform = build_transforms(train=False)

    for model_name in MODELS:
        ckpt = torch.load(WEIGHTS_DIR / f"vehicle-type-{model_name}.pt", map_location=device)
        class_names = ckpt["class_names"]
        model = build_model(model_name, len(class_names)).to(device)
        model.load_state_dict(ckpt["model_state"])
        model.eval()

        print(f"\n===== {model_name} (classes={class_names}) =====")
        correct = 0
        for path, true_label in TEST_CASES:
            img = Image.open(path).convert("RGB")
            x = transform(img).unsqueeze(0).to(device)
            with torch.no_grad():
                probs = torch.softmax(model(x), dim=1)[0]
            idx = int(probs.argmax())
            pred = class_names[idx]
            ok = pred == true_label
            correct += int(ok)
            print(f"  {path.name:20s} that={true_label:10s} du_doan={pred:10s} "
                  f"conf={probs[idx]:.1%}  {'OK' if ok else 'SAI'}")
        print(f"  => {correct}/{len(TEST_CASES)} dung ({correct / len(TEST_CASES):.0%})")


if __name__ == "__main__":
    main()
