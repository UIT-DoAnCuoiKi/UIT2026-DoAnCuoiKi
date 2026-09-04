"""Runner suy luận ALPR chạy model thật (ONNX + YOLO) — nguồn sự thật dùng chung
cho backend (`app/services/ml_inference.py`) và edge worker (`src/edge/worker.py`).

Chạy 3 model đã huấn luyện ở src/ml trên một khung ảnh BGR:

  1. Phát hiện biển số: YOLO `.pt` qua ultralytics (`PlateDetector`).
  2. OCR biển số:       CRNN `.onnx` qua onnxruntime.
  3. Kiểu dáng xe:      classifier `.onnx` qua onnxruntime (chỉ khi là "car").

Loại thô car/motorcycle/bus/truck và cắt vùng xe tái dùng
`predict_vehicle.detect_vehicle_crop` (YOLOv8n COCO). Màu biển tái dùng
`plate_color.process_plate`. Tách dòng + chuẩn hoá biển tái dùng
`pipeline.ocr.read_plate`.

`OnnxAlprPipeline.run(image_bgr)` trả **dict** trùng schema
`PipelinePayload`/`PlateItem` (bỏ khoá `file`), nên:

  - Backend: `PipelinePayload.model_validate(dict)`.
  - Edge:    `json.dumps(dict)` gửi field `payload` của `POST /captures`.

Các import nặng (torch, cv2, onnxruntime, cây src/ml) nằm trong hàm khởi tạo để
môi trường không có model vẫn import được module. Bản `.pt` cho OCR/classifier
KHÔNG có trong repo (chỉ có bản `.onnx` đã export), nên runner chạy thẳng `.onnx`
thay vì `torch.load`, dùng đúng model đã train.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Cây src/ml suy từ vị trí file: .../src/ml/pipeline/onnx_pipeline.py
_ML_DIR = Path(__file__).resolve().parents[1]

_DEFAULTS = {
    "plate_weights": _ML_DIR
    / "plate_detection_pipeline" / "output" / "plate_det_results_20260812_2212"
    / "runs" / "yolov8n_s0_640" / "weights" / "best.pt",
    "ocr_onnx": _ML_DIR / "weights" / "plate-ocr-crnn.onnx",
    "style_onnx": _ML_DIR / "weights" / "vehicle-style-resnet18.onnx",
    "style_classes": _ML_DIR / "data" / "vehicle-style-classes.json",
}


def encode_crop_b64(crop_bgr) -> str:
    """PNG-encode a BGR crop to a base64 ascii string. Returns "" on failure."""
    import base64

    import cv2

    if crop_bgr is None:
        return ""
    ok, buf = cv2.imencode(".png", crop_bgr)
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _ensure_ml_path() -> None:
    """Đưa các gói con của src/ml lên sys.path (giống e2e_pipeline_test)."""
    for p in (
        _ML_DIR,                                # pipeline/, predict_vehicle.py
        _ML_DIR / "training",                   # ocr_model.py, classifier.py
        _ML_DIR / "plate_detection_pipeline",   # gói plate_detect
        _ML_DIR / "plate_color_pipeline",       # gói plate_color
    ):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


class _OnnxCRNNRecognizer:
    """OCR biển số 1 dòng bằng CRNN `.onnx`. Cùng interface
    `recognize(image_bgr) -> (text, confidence)` với `pipeline.ocr.CRNNRecognizer`
    nên dùng chung được `read_plate` (tách dòng biển 2 hàng, chuẩn hoá). Tái dùng
    `decode_greedy` + charset từ `training/ocr_model.py` để khớp đúng bản đã train.
    """

    def __init__(self, onnx_path: str) -> None:
        import numpy as np
        import onnxruntime as ort
        import torch

        from ocr_model import IMG_HEIGHT, IMG_WIDTH, decode_greedy

        self._np = np
        self._torch = torch
        self._decode_greedy = decode_greedy
        self._h, self._w = IMG_HEIGHT, IMG_WIDTH
        self._sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self._input_name = self._sess.get_inputs()[0].name

    def recognize(self, image_bgr):
        import cv2

        np = self._np
        img = cv2.resize(image_bgr, (self._w, self._h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        x = gray[None, None, :, :]  # (1, 1, H, W)
        logits = self._sess.run(None, {self._input_name: x})[0]  # (1, T, C)
        e = np.exp(logits - logits.max(axis=2, keepdims=True))
        probs = e / e.sum(axis=2, keepdims=True)
        confidence = float(probs.max(axis=2).mean())
        text = self._decode_greedy(self._torch.from_numpy(logits))[0]
        return text, confidence


class OnnxAlprPipeline:
    """Nạp 3 model một lần rồi chạy `run(image_bgr) -> dict` cho từng khung ảnh.

    Đường dẫn model mặc định suy từ vị trí file (src/ml/weights, output detector);
    truyền tham số ctor để ghi đè (edge worker dùng đường này). Backend đọc biến
    môi trường rồi truyền vào đây."""

    def __init__(
        self,
        plate_weights: str | None = None,
        ocr_onnx: str | None = None,
        style_onnx: str | None = None,
        style_classes_path: str | None = None,
        device: str = "cpu",
        conf: float | None = None,
    ) -> None:
        _ensure_ml_path()

        import onnxruntime as ort

        from classifier import build_transforms
        from plate_detect.inference.plate_detector import PlateDetector

        plate_weights = str(plate_weights or _DEFAULTS["plate_weights"])
        ocr_onnx = str(ocr_onnx or _DEFAULTS["ocr_onnx"])
        style_onnx = str(style_onnx or _DEFAULTS["style_onnx"])
        style_classes_path = str(style_classes_path or _DEFAULTS["style_classes"])

        det_kwargs = {} if conf is None else {"conf": conf}
        self._plate_detector = PlateDetector(plate_weights, **det_kwargs)
        self._ocr = _OnnxCRNNRecognizer(ocr_onnx)

        self._style_sess = None
        self._style_input = None
        self._style_classes: list[str] = []
        if Path(style_onnx).exists() and Path(style_classes_path).exists():
            self._style_sess = ort.InferenceSession(style_onnx, providers=["CPUExecutionProvider"])
            self._style_input = self._style_sess.get_inputs()[0].name
            with open(style_classes_path, encoding="utf-8") as fh:
                self._style_classes = json.load(fh)
        self._style_transform = build_transforms(train=False)

    def run(self, image_bgr) -> dict:
        """Chạy toàn chuỗi trên 1 khung BGR, trả dict trùng schema PipelinePayload.

        Khoá cấp trên: vehicle_type, vehicle_box, vehicle_style,
        vehicle_style_conf, plates. Mỗi phần tử plates: bbox, layout, det_conf,
        plate_text, plate_valid, ocr_conf, color, color_conf, crop_proc_b64."""
        import cv2
        import numpy as np
        from PIL import Image

        from plate_color import process_plate
        from pipeline.ocr import read_plate
        from predict_vehicle import detect_vehicle_crop

        result: dict = {
            "vehicle_type": None,
            "vehicle_box": None,
            "vehicle_style": None,
            "vehicle_style_conf": None,
            "plates": [],
        }
        if image_bgr is None:
            return result

        img_pil = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))

        # --- Nhánh xe: loại thô + (nếu car) kiểu dáng ---
        crop_pil, det_info = detect_vehicle_crop(img_pil)
        if det_info is not None:
            result["vehicle_type"] = det_info["yolo_class"]
            result["vehicle_box"] = [float(v) for v in det_info["box"]]
            if det_info["yolo_class"] == "car" and self._style_sess is not None:
                x = self._style_transform(crop_pil).unsqueeze(0).numpy()
                logits = self._style_sess.run(None, {self._style_input: x})[0][0]
                e = np.exp(logits - logits.max())
                probs = e / e.sum()
                idx = int(probs.argmax())
                result["vehicle_style"] = self._style_classes[idx]
                result["vehicle_style_conf"] = float(probs[idx])

        # --- Nhánh biển số: phát hiện -> màu -> OCR, cho từng biển ---
        for det in self._plate_detector.detect(image_bgr):
            appearance = process_plate(det.crop)
            reading = read_plate(appearance.crop_for_ocr, self._ocr, layout=det.cls_name)
            result["plates"].append({
                "bbox": [float(v) for v in det.bbox_xyxy],
                "layout": det.cls_name,
                "det_conf": float(det.conf),
                "plate_text": reading.text_display,
                "plate_valid": bool(reading.valid_format),
                "ocr_conf": float(reading.confidence),
                "color": appearance.color,
                "color_conf": float(appearance.color_conf) if appearance.color_conf is not None else None,
                "crop_proc_b64": encode_crop_b64(appearance.crop_for_ocr),
            })

        return result
