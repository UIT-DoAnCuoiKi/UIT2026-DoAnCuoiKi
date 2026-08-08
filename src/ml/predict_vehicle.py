"""Chạy pipeline phân loại xe trên 1 ảnh, dùng để thử nhanh từ dòng lệnh.

Pipeline gồm 2 bước:
  1. Loại thô (car/motorcycle/bus/truck): YOLOv8n pretrained trên COCO,
     không huấn luyện thêm. Đồng thời dùng luôn box của bước này để cắt
     vùng xe cho bước 2.
  2. Kiểu dáng (chỉ chạy khi bước 1 ra "car"): model tự huấn luyện, 3 lớp
     Sedan / GamCao / XeTai (xem src/ml/data_prep/prepare_classification_data.py
     để biết 12 kiểu dáng gốc của B5 được gộp vào 3 nhóm này thế nào).

Ảnh đầu vào không cần cắt sẵn: script tự phát hiện và cắt vùng xe lớn nhất
kèm biên 10%, đúng quy ước lúc chuẩn bị dữ liệu huấn luyện. Đây là bản ghép
ở mức 1 ảnh; tích hợp vào luồng camera thật thuộc phạm vi Tuần 6.

Chạy: (môi trường ml-gpu) python src/ml/predict_vehicle.py duong/dan/anh.jpg
      python src/ml/predict_vehicle.py duong/dan/anh.jpg --model mobilenet_v3_small
      python src/ml/predict_vehicle.py anh_o_to_da_cat_san.jpg --no-detect
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))

import torch  # noqa: E402
from PIL import Image  # noqa: E402

from classifier import build_model, build_transforms  # noqa: E402

WEIGHTS_DIR = REPO_ROOT / "src" / "ml" / "weights"

# Chỉ giữ 4 lớp phương tiện trong COCO, bỏ qua người/vật thể khác trong khung hình
COCO_VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


def detect_vehicle_crop(img: Image.Image, padding_frac: float = 0.10):
    """Phát hiện và cắt vùng xe lớn nhất trong ảnh bằng YOLOv8n pretrained.

    Biên 10% mặc định khớp với quy ước lúc chuẩn bị dữ liệu huấn luyện, đổi
    giá trị này sẽ làm ảnh đầu vào lệch so với phân phối lúc train.

    Trả về (ảnh_đã_cắt, thông_tin_box). Nếu không phát hiện được xe nào thì
    trả về (ảnh_gốc, None) để nơi gọi tự quyết định xử lý.
    """
    from ultralytics import YOLO

    yolo_weights = WEIGHTS_DIR / "yolov8n.pt"
    yolo_weights.parent.mkdir(parents=True, exist_ok=True)
    # Chỉ định đường dẫn tuyệt đối để trọng số luôn nằm 1 chỗ, không phụ
    # thuộc thư mục đang chạy lệnh (ultralytics tự tải về lần đầu)
    model = YOLO(str(yolo_weights))
    results = model.predict(img, verbose=False)[0]

    # Lấy xe có diện tích lớn nhất làm phương tiện chính của khung hình
    best = None  # (area, x1, y1, x2, y2, tên_lớp, conf)
    for box in results.boxes:
        cls_id = int(box.cls[0])
        if cls_id not in COCO_VEHICLE_CLASSES:
            continue
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        area = (x2 - x1) * (y2 - y1)
        if best is None or area > best[0]:
            best = (area, x1, y1, x2, y2, COCO_VEHICLE_CLASSES[cls_id], float(box.conf[0]))

    if best is None:
        return img, None

    _, x1, y1, x2, y2, cls_name, conf = best
    w, h = img.size
    pad_w, pad_h = (x2 - x1) * padding_frac, (y2 - y1) * padding_frac
    x1, y1 = max(0, x1 - pad_w), max(0, y1 - pad_h)
    x2, y2 = min(w, x2 + pad_w), min(h, y2 + pad_h)
    crop = img.crop((x1, y1, x2, y2))
    return crop, {"box": (round(x1), round(y1), round(x2), round(y2)), "yolo_class": cls_name, "yolo_conf": conf}


def load_style_model(model_name: str, device: str):
    """Load model phân loại kiểu dáng đã huấn luyện.

    Trả về (model, class_names). Số lớp và tên lớp đều lấy từ checkpoint,
    không hard-code, vì thứ tự lớp do ImageFolder quyết định lúc huấn luyện
    (sắp theo bảng chữ cái) và sẽ đổi nếu huấn luyện lại với tập lớp khác.
    """
    ckpt_path = WEIGHTS_DIR / f"vehicle-style-{model_name}.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"Không thấy {ckpt_path}, cần huấn luyện trước (src/ml/train_vehicle_classifier.py)"
        )
    ckpt = torch.load(ckpt_path, map_location=device)
    class_names = ckpt["class_names"]
    model = build_model(model_name, len(class_names)).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, class_names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=Path, help="Đường dẫn ảnh, không cần cắt sẵn")
    parser.add_argument(
        "--model", choices=["resnet18", "mobilenet_v3_small"], default="resnet18",
        help="Kiến trúc dùng cho phần phân loại kiểu dáng (mặc định resnet18)",
    )
    parser.add_argument(
        "--no-detect", action="store_true",
        help="Bỏ qua bước YOLO phát hiện và phân loại thô, coi ảnh đầu vào đã là "
             "1 chiếc ô tô cắt sẵn và chạy thẳng phân loại kiểu dáng",
    )
    args = parser.parse_args()

    if not args.image.exists():
        print(f"Không tìm thấy ảnh: {args.image}", file=sys.stderr)
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    img = Image.open(args.image).convert("RGB")
    print(f"Ảnh: {args.image}")

    if args.no_detect:
        crop = img
        coarse_type = "car"
        print("(--no-detect: bỏ qua YOLO, coi đây là ảnh ô tô đã cắt sẵn)")
    else:
        crop, det_info = detect_vehicle_crop(img)
        if det_info is None:
            print("[cảnh báo] Không phát hiện được xe nào trong ảnh.")
            print("\n=> Không thể phân loại.")
            return
        coarse_type = det_info["yolo_class"]
        print(f"Loại xe: {coarse_type}  (độ tin cậy {det_info['yolo_conf']:.1%}), "
              f"box {det_info['box']}")
        crop_path = args.image.with_stem(args.image.stem + "_crop")
        crop.save(crop_path)
        print(f"Đã lưu ảnh cắt: {crop_path}")

    # Bước 2 chỉ áp dụng cho ô tô con, các loại xe khác dừng ở kết quả bước 1
    if coarse_type != "car":
        print(f"\n=> Kết quả: {coarse_type}")
        return

    style_model, style_classes = load_style_model(args.model, device)
    x = build_transforms(train=False)(crop).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(style_model(x), dim=1)[0]
    idx = int(probs.argmax())
    pred, conf = style_classes[idx], probs[idx].item()

    print(f"\nModel kiểu dáng: {args.model}")
    print(f"Kiểu dáng: {pred}  (độ tin cậy {conf:.1%})")
    print("Chi tiết:")
    for i in probs.argsort(descending=True).tolist():
        print(f"  {style_classes[i]:10s} {probs[i].item():.1%}")
    print(f"\n=> Kết quả: {pred} (loại car)")


if __name__ == "__main__":
    main()
