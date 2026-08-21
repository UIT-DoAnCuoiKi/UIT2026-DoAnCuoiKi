"""Chạy pipeline nhận diện bãi xe đầy đủ (xe -> kiểu dáng; biển số -> màu + OCR)
từ dòng lệnh, trên 1 ảnh hoặc 1 thư mục ảnh. Bản CLI của
src/ml/notebooks/e2e-pipeline-test.ipynb — cùng logic, không cần Jupyter.

Ngoài in kết quả ra terminal, mỗi ảnh đầu vào được lưu lại 1 bản có vẽ bounding
box (xe + biển số) kèm text nhận diện, phục vụ kiểm tra bằng mắt nhanh.

Chạy:
  python src/ml/e2e_pipeline_test.py                        # dùng testimage/ mặc định
  python src/ml/e2e_pipeline_test.py duong/dan/anh.jpg       # 1 ảnh
  python src/ml/e2e_pipeline_test.py duong/dan/thu_muc/      # thư mục ảnh, lấy ngẫu nhiên n ảnh
  python src/ml/e2e_pipeline_test.py --n-samples 5 --out-dir out/
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":  # console Windows mặc định cp1252, không in được dấu tiếng Việt
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = REPO_ROOT / "src" / "ml"

for _p in (
    ML_DIR,                                 # pipeline/, predict_vehicle.py
    ML_DIR / "training",                    # ocr_model.py, classifier.py
    ML_DIR / "plate_detection_pipeline",    # gói plate_detect
    ML_DIR / "plate_color_pipeline",        # gói plate_color
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

from predict_vehicle import detect_vehicle_crop, load_style_model  # noqa: E402
from classifier import build_transforms  # noqa: E402
from plate_detect.inference.plate_detector import PlateDetector  # noqa: E402
from plate_color import process_plate  # noqa: E402
from pipeline.ocr import CRNNRecognizer, read_plate  # noqa: E402

# --- Đường dẫn model — cùng cấu hình với notebook e2e-pipeline-test.ipynb ---
VEHICLE_STYLE_MODEL = "resnet18"  # hoặc "mobilenet_v3_small"
PLATE_DETECTOR_WEIGHTS = (
    ML_DIR / "plate_detection_pipeline" / "output" / "runs" / "detect" / "runs"
    / "yolov8n_s0_640" / "weights" / "best.pt"
)  # bản tốt nhất theo src/ml/experiments.csv (mAP50 0.9892)
PLATE_DETECTOR_BACKEND = "pt"  # chưa có bản .onnx export cho model biển số
OCR_WEIGHTS = ML_DIR / "weights" / "plate-ocr-crnn.pt"  # bản chốt, seed 42

DEFAULT_TEST_DIR = REPO_ROOT / "testimage"
DEFAULT_OUT_DIR = ML_DIR / "experiments" / "e2e_annotated"


def run_pipeline_on_image(
    image_path: Path, plate_detector: PlateDetector, ocr_recognizer: CRNNRecognizer,
    style_model, style_classes: list[str], style_transform, device: str,
) -> tuple[dict, np.ndarray]:
    """Chạy toàn bộ chuỗi trên 1 ảnh thô. Trả về (kết quả, ảnh gốc BGR)."""
    img_bgr = cv2.imread(str(image_path))
    img_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    result = {
        "file": image_path.name,
        "vehicle_type": None, "vehicle_box": None,
        "vehicle_style": None, "vehicle_style_conf": None,
        "plates": [],
    }

    # --- Nhánh xe: phát hiện thô + (nếu là car) phân loại kiểu dáng ---
    crop_pil, det_info = detect_vehicle_crop(img_pil)
    if det_info is not None:
        result["vehicle_type"] = det_info["yolo_class"]
        result["vehicle_box"] = det_info["box"]
        if det_info["yolo_class"] == "car":
            x = style_transform(crop_pil).unsqueeze(0).to(device)
            with torch.no_grad():
                probs = torch.softmax(style_model(x), dim=1)[0]
            idx = int(probs.argmax())
            result["vehicle_style"] = style_classes[idx]
            result["vehicle_style_conf"] = probs[idx].item()

    # --- Nhánh biển số: phát hiện -> màu + tăng cường -> OCR, cho từng biển ---
    for det in plate_detector.detect(img_bgr):
        appearance = process_plate(det.crop)
        reading = read_plate(appearance.crop_for_ocr, ocr_recognizer, layout=det.cls_name)
        result["plates"].append({
            "bbox": det.bbox_xyxy, "layout": det.cls_name, "det_conf": det.conf,
            "plate_text": reading.text_display, "plate_valid": reading.valid_format,
            "ocr_conf": reading.confidence,
            "color": appearance.color, "color_conf": appearance.color_conf,
        })

    return result, img_bgr


def draw_annotations(img_bgr: np.ndarray, result: dict) -> np.ndarray:
    """Vẽ bbox xe (cam) + bbox biển (xanh lá nếu khớp định dạng, đỏ nếu không)."""
    img = img_bgr.copy()
    if result["vehicle_box"]:
        x1, y1, x2, y2 = result["vehicle_box"]
        label = result["vehicle_type"] or "?"
        if result["vehicle_style"]:
            label += f" ({result['vehicle_style']})"
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 128, 0), 2)
        cv2.putText(img, label, (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 128, 0), 2)

    for plate in result["plates"]:
        x1, y1, x2, y2 = plate["bbox"]
        text = f"{plate['plate_text']} ({plate['color']})"
        color = (0, 200, 0) if plate["plate_valid"] else (0, 0, 255)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, text, (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return img


def print_result(result: dict) -> None:
    print(f"=== {result['file']} ===")
    vehicle_line = f"  Xe: {result['vehicle_type'] or '(không phát hiện)'}"
    if result["vehicle_style"]:
        vehicle_line += f" - kiểu dáng {result['vehicle_style']} ({result['vehicle_style_conf']:.1%})"
    print(vehicle_line)

    if not result["plates"]:
        print("  (không phát hiện được biển số nào)")
    for i, p in enumerate(result["plates"], 1):
        flag = "OK" if p["plate_valid"] else "!! không khớp định dạng biển VN"
        print(
            f"  Biển {i}: {p['plate_text']}  [{flag}]  "
            f"màu={p['color']} ({p['color_conf']:.1%})  "
            f"det_conf={p['det_conf']:.2f}  ocr_conf={p['ocr_conf']:.2f}  "
            f"layout={p['layout']}"
        )


def collect_images(path: Path, n_samples: int, seed: int) -> list[Path]:
    if path.is_file():
        return [path]
    images = sorted(p for p in path.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not images:
        raise FileNotFoundError(f"Không tìm thấy ảnh nào trong {path}")
    return random.Random(seed).sample(images, min(n_samples, len(images)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "input", type=Path, nargs="?", default=DEFAULT_TEST_DIR,
        help=f"Ảnh hoặc thư mục ảnh (mặc định {DEFAULT_TEST_DIR})",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT_DIR,
        help=f"Thư mục lưu ảnh đã vẽ bounding box (mặc định {DEFAULT_OUT_DIR})",
    )
    parser.add_argument("--n-samples", type=int, default=20, help="Số ảnh lấy ngẫu nhiên nếu input là thư mục")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng confidence phát hiện biển số")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Không tìm thấy: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not PLATE_DETECTOR_WEIGHTS.exists():
        print(
            f"Không thấy weight model biển số: {PLATE_DETECTOR_WEIGHTS}\n"
            "Xem src/ml/plate_detection_pipeline/output/README.MD để lấy link Drive.",
            file=sys.stderr,
        )
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    plate_detector = PlateDetector(str(PLATE_DETECTOR_WEIGHTS), backend=PLATE_DETECTOR_BACKEND, conf=args.conf)
    ocr_recognizer = CRNNRecognizer(OCR_WEIGHTS, device=device)
    style_model, style_classes = load_style_model(VEHICLE_STYLE_MODEL, device)
    style_transform = build_transforms(train=False)
    print("Đã load xong: plate detector, OCR, phân loại kiểu dáng xe.\n")

    images = collect_images(args.input, args.n_samples, args.seed)
    print(f"Chạy trên {len(images)} ảnh ({args.input}):")
    for p in images:
        print(" -", p.name)
    print()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    for image_path in images:
        result, img_bgr = run_pipeline_on_image(
            image_path, plate_detector, ocr_recognizer, style_model, style_classes, style_transform, device,
        )
        print_result(result)

        annotated = draw_annotations(img_bgr, result)
        out_path = args.out_dir / f"{image_path.stem}_annotated.png"
        cv2.imwrite(str(out_path), annotated)
        print(f"  -> đã lưu {out_path}\n")

    print(f"Xong. Ảnh đã vẽ bounding box lưu ở: {args.out_dir}")


if __name__ == "__main__":
    main()
