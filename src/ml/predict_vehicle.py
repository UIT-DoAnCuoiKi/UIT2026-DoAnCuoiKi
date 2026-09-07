"""Chạy pipeline phân loại xe trên 1 ảnh, dùng để thử nhanh từ dòng lệnh.

Pipeline gồm 2 bước:
  1. Phát hiện + cắt vùng xe: YOLOv8n pretrained trên COCO, không huấn luyện
     thêm. Model được nạp 1 lần rồi cache theo instance (nạp lại từ đĩa mỗi
     lần gọi từng chiếm 88% độ trễ toàn pipeline, xem CoarseVehicleDetector).
     2 backend chọn được: "pt" (ultralytics, mặc định) hoặc "onnx"
     (onnxruntime thuần, không cần torch — dùng khi triển khai thiết bị muốn
     tránh phụ thuộc torch, vd Raspberry Pi). Nhãn lớp COCO
     (car/motorcycle/bus/truck) chỉ dùng làm loại thô dự phòng cho "bus" —
     car/motorbike/truck đã có model tự huấn luyện riêng, chính xác hơn (xem
     onnx_pipeline.py, train_vehicle_type_classifier.py).
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

# Chỉ giữ 4 lớp phương tiện trong COCO, bỏ qua người/vật thể khác trong khung hình.
# "motorbike" (không phải "motorcycle") để khớp tên lớp của model loại-xe tự huấn
# luyện (train_vehicle_type_classifier.py) và bảng ánh xạ nhóm phí backend
# (app/services/vehicle_groups.py) — trước đây lệch tên khiến mọi xe máy không
# được gán nhóm phí tự động (group_for("motorcycle") luôn trả None).
COCO_VEHICLE_CLASSES = {2: "car", 3: "motorbike", 5: "bus", 7: "truck"}
_COCO_NUM_CLASSES = 80


class CoarseVehicleDetector:
    """Định vị xe (box + nhãn COCO thô) trong 1 khung hình. 2 backend, chọn
    được qua tham số `backend`, cùng khuôn với `PlateDetector`
    (plate_detection_pipeline/plate_detect/inference/plate_detector.py):

    - `"pt"` (mặc định): `ultralytics.YOLO`, cần torch cài đặt. Ultralytics tự
      letterbox (giữ tỉ lệ khung hình + đệm) và tự NMS nội bộ.
    - `"onnx"`: `onnxruntime` thuần, KHÔNG cần torch/ultralytics cài đặt — dùng
      khi triển khai trên thiết bị muốn tránh phụ thuộc torch (vd Raspberry
      Pi, xem docs/report/chapters/05-phanloai.md mục 5.6). Tự làm letterbox
      (resize giữ tỉ lệ + đệm xám 114, đúng quy ước ultralytics) rồi giải mã
      box/NMS bằng `decode_v8` (tái dùng từ module phát hiện biển của Đức).

      QUAN TRỌNG: bước letterbox không được thay bằng squash-resize (resize
      thẳng về hình vuông, bỏ qua tỉ lệ khung hình) như `PlateDetector._detect_onnx`
      đang làm cho biển số — đo thực tế trên ảnh camera cổng thật (khung hình
      rất rộng, 2048x899) cho thấy squash-resize làm méo xe đến mức model
      KHÔNG phát hiện được xe nào (0 detection). Letterbox đúng cho kết quả
      gần như giống hệt bản pt trên cùng ảnh (car conf=0,853 so với 0,850, box
      lệch vài pixel). Biển số không gặp vấn đề này vì ảnh crop biển đã tương
      đối vuông vắn trước khi vào bước phát hiện.

    Model/session cache theo INSTANCE (nạp 1 lần, dùng lại cho mọi khung hình
    tiếp theo) — xem lý do cache ở `detect_vehicle_crop`.
    """

    def __init__(self, weights, backend: str = "pt", conf: float = 0.25,
                 iou: float = 0.5, sess_options=None):
        self.weights = str(weights)
        self.backend = backend
        self.conf = conf
        self.iou = iou
        self._sess_options = sess_options
        self._model = None
        self._session = None

    def detect(self, img: Image.Image):
        """Trả list `(x1, y1, x2, y2, cls_id, conf)` tọa độ ẢNH GỐC, chưa lọc
        theo `COCO_VEHICLE_CLASSES` (việc lọc + chọn box lớn nhất do
        `detect_vehicle_crop` đảm nhận, dùng chung cho cả 2 backend)."""
        if self.backend == "pt":
            return self._detect_pt(img)
        if self.backend == "onnx":
            return self._detect_onnx(img)
        raise ValueError(f"unknown backend '{self.backend}'")

    def _detect_pt(self, img: Image.Image):
        if self._model is None:
            from ultralytics import YOLO

            Path(self.weights).parent.mkdir(parents=True, exist_ok=True)
            # Chỉ định đường dẫn tuyệt đối để trọng số luôn nằm 1 chỗ, không
            # phụ thuộc thư mục đang chạy lệnh (ultralytics tự tải về lần đầu)
            self._model = YOLO(self.weights)
        r = self._model.predict(img, conf=self.conf, verbose=False)[0]
        return [
            (*box.xyxy[0].tolist(), int(box.cls[0]), float(box.conf[0]))
            for box in r.boxes
        ]

    def _detect_onnx(self, img: Image.Image):
        import cv2
        import numpy as np
        import onnxruntime as ort

        # Gói plate_detect (module phát hiện biển của Đức) có thể chưa nằm
        # trên sys.path nếu class này được dùng độc lập, ngoài onnx_pipeline.py
        # (nơi _ensure_ml_path() đã lo việc này).
        _plate_detect_dir = REPO_ROOT / "src" / "ml" / "plate_detection_pipeline"
        if str(_plate_detect_dir) not in sys.path:
            sys.path.insert(0, str(_plate_detect_dir))
        from plate_detect.inference.postprocess import decode_v8

        if self._session is None:
            self._session = ort.InferenceSession(
                self.weights, sess_options=self._sess_options, providers=["CPUExecutionProvider"]
            )
        inp = self._session.get_inputs()[0]
        h, w = inp.shape[2:]
        h = h if isinstance(h, int) else 640
        w = w if isinstance(w, int) else 640

        img_rgb = np.array(img)  # ảnh vào đã là PIL RGB, không cần đổi kênh màu
        ih, iw = img_rgb.shape[:2]
        scale = min(w / iw, h / ih)
        nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
        resized = cv2.resize(img_rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((h, w, 3), 114, dtype=np.uint8)  # đệm xám, đúng quy ước ultralytics
        pad_x, pad_y = (w - nw) // 2, (h - nh) // 2
        canvas[pad_y:pad_y + nh, pad_x:pad_x + nw] = resized

        blob = canvas.transpose(2, 0, 1)[None]
        blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
        raw = self._session.run(None, {inp.name: blob})[0][0]
        boxes, scores, classes = decode_v8(raw, self.conf, self.iou, _COCO_NUM_CLASSES)

        out = []
        for (x1, y1, x2, y2), cls_id, score in zip(boxes, classes, scores):
            # Un-letterbox: trừ đệm rồi chia lại tỉ lệ, về đúng tọa độ ảnh gốc
            out.append((
                (x1 - pad_x) / scale, (y1 - pad_y) / scale,
                (x2 - pad_x) / scale, (y2 - pad_y) / scale,
                int(cls_id), float(score),
            ))
        return out


# Cache theo tiến trình cho detector mặc định (backend "pt", dùng cho CLI và
# mọi nơi gọi detect_vehicle_crop() không tự truyền detector riêng). Nạp lại
# YOLO(...) từ đĩa mỗi lần gọi tốn ~135ms (đo thực tế), chiếm 88% độ trễ toàn
# pipeline khi chạy nhiều khung hình liên tiếp — cache instance 1 lần giải
# quyết đúng vấn đề này, cùng nguyên tắc với _engine trong ml_inference.py.
_default_coarse_detector: CoarseVehicleDetector | None = None


def _get_default_coarse_detector() -> CoarseVehicleDetector:
    global _default_coarse_detector
    if _default_coarse_detector is None:
        _default_coarse_detector = CoarseVehicleDetector(WEIGHTS_DIR / "yolov8n.pt", backend="pt")
    return _default_coarse_detector


def detect_vehicle_crop(img: Image.Image, padding_frac: float = 0.10, detector: CoarseVehicleDetector | None = None):
    """Phát hiện và cắt vùng xe lớn nhất trong ảnh bằng YOLOv8n pretrained.

    Biên 10% mặc định khớp với quy ước lúc chuẩn bị dữ liệu huấn luyện, đổi
    giá trị này sẽ làm ảnh đầu vào lệch so với phân phối lúc train.

    `detector`: truyền vào để dùng backend/cấu hình khác (vd `onnx` khi triển
    khai không có torch); bỏ trống thì dùng 1 detector mặc định (backend
    "pt") cache theo tiến trình, khớp hành vi trước đây.

    Trả về (ảnh_đã_cắt, thông_tin_box). Nếu không phát hiện được xe nào thì
    trả về (ảnh_gốc, None) để nơi gọi tự quyết định xử lý.
    """
    detector = detector or _get_default_coarse_detector()

    # Lấy xe có diện tích lớn nhất làm phương tiện chính của khung hình
    best = None  # (area, x1, y1, x2, y2, tên_lớp, conf)
    for x1, y1, x2, y2, cls_id, conf in detector.detect(img):
        if cls_id not in COCO_VEHICLE_CLASSES:
            continue
        area = (x2 - x1) * (y2 - y1)
        if best is None or area > best[0]:
            best = (area, x1, y1, x2, y2, COCO_VEHICLE_CLASSES[cls_id], conf)

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
