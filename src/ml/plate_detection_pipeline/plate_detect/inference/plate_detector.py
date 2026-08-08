from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .postprocess import decode_v8, decode_v26


@dataclass
class PlateDetection:
    bbox_xyxy: tuple[int, int, int, int]
    cls_id: int
    cls_name: str
    conf: float
    crop: np.ndarray


def build_detections(boxes, classes, confs, image, names, pad: int = 4) -> list[PlateDetection]:
    H, W = image.shape[:2]
    order = np.argsort(np.asarray(confs))[::-1] if len(confs) else []
    out = []
    for i in order:
        x1, y1, x2, y2 = boxes[i]
        x1 = int(max(0, min(W, x1 - pad))); y1 = int(max(0, min(H, y1 - pad)))
        x2 = int(max(0, min(W, x2 + pad))); y2 = int(max(0, min(H, y2 + pad)))
        if x2 <= x1 or y2 <= y1:
            continue
        cid = int(classes[i])
        out.append(PlateDetection((x1, y1, x2, y2), cid,
                                  names.get(cid, str(cid)), float(confs[i]),
                                  image[y1:y2, x1:x2].copy()))
    return out


class PlateDetector:
    def __init__(self, weights: str, backend: str = "pt",
                 names: dict | None = None, conf: float = 0.25, iou: float = 0.5):
        self.weights = weights
        self.backend = backend
        self.names = names or {0: "bien_1hang", 1: "bien_2hang"}
        self.conf = conf
        self.iou = iou
        self._model = None
        self._session = None

    def detect(self, image: np.ndarray) -> list[PlateDetection]:
        if self.backend == "pt":
            return self._detect_pt(image)
        if self.backend == "onnx":
            return self._detect_onnx(image)
        raise ValueError(f"unknown backend '{self.backend}'")

    def _detect_pt(self, image: np.ndarray) -> list[PlateDetection]:
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(self.weights)
        r = self._model.predict(image, conf=self.conf, iou=self.iou, verbose=False)[0]
        b = r.boxes
        if b is None or len(b) == 0:
            return []
        boxes = b.xyxy.cpu().numpy()
        classes = b.cls.cpu().numpy().astype(int)
        confs = b.conf.cpu().numpy()
        return build_detections(boxes, classes, confs, image, self.names)

    def _detect_onnx(self, image: np.ndarray) -> list[PlateDetection]:
        import cv2
        import onnxruntime as ort
        if self._session is None:
            self._session = ort.InferenceSession(
                self.weights, providers=["CPUExecutionProvider"])
        inp_name = self._session.get_inputs()[0].name
        h, w = self._session.get_inputs()[0].shape[2:]
        h = h if isinstance(h, int) else 640
        w = w if isinstance(w, int) else 640
        blob = cv2.resize(image, (w, h))[:, :, ::-1].transpose(2, 0, 1)[None]
        blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
        raw = self._session.run(None, {inp_name: blob})[0][0]
        nc = len(self.names)
        if raw.ndim == 2 and raw.shape[1] == 6:
            boxes, scores, classes = decode_v26(raw, self.conf)
        else:
            boxes, scores, classes = decode_v8(raw, self.conf, self.iou, nc)
        sx, sy = image.shape[1] / w, image.shape[0] / h
        if len(boxes):
            boxes = boxes * np.array([sx, sy, sx, sy])
        return build_detections(boxes, classes, scores, image, self.names)
