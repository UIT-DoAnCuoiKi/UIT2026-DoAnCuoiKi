from __future__ import annotations
import numpy as np


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    xx1 = np.maximum(box[0], boxes[:, 0]); yy1 = np.maximum(box[1], boxes[:, 1])
    xx2 = np.minimum(box[2], boxes[:, 2]); yy2 = np.minimum(box[3], boxes[:, 3])
    w = np.clip(xx2 - xx1, 0, None); h = np.clip(yy2 - yy1, 0, None)
    inter = w * h
    area = (box[2] - box[0]) * (box[3] - box[1])
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / (area + areas - inter + 1e-9)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    idx = scores.argsort()[::-1]
    keep = []
    while len(idx):
        i = idx[0]; keep.append(int(i))
        if len(idx) == 1:
            break
        ious = _iou(boxes[i], boxes[idx[1:]])
        idx = idx[1:][ious <= iou_thr]
    return keep


def decode_v26(raw: np.ndarray, conf: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw = np.asarray(raw, float)
    m = raw[:, 4] >= conf
    r = raw[m]
    return r[:, :4], r[:, 4], r[:, 5].astype(int)


def decode_v8(raw: np.ndarray, conf: float, iou: float, nc: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw = np.asarray(raw, float)
    # assumes a non-square head; if M happens to equal 4+nc the transpose is ambiguous
    # (an inherent YOLOv8 head-format limitation, not specific to this code)
    if raw.shape[0] == 4 + nc:
        raw = raw.T                       # (M, 4+nc)
    xywh, cls = raw[:, :4], raw[:, 4:4 + nc]
    scores = cls.max(axis=1); classes = cls.argmax(axis=1)
    m = scores >= conf
    xywh, scores, classes = xywh[m], scores[m], classes[m]
    xyxy = np.stack([xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2,
                     xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2], axis=1)
    keep_all = []
    for c in np.unique(classes):
        cm = np.where(classes == c)[0]
        k = nms(xyxy[cm], scores[cm], iou)
        keep_all.extend(cm[k].tolist())
    keep_all = np.array(keep_all, int)
    return xyxy[keep_all], scores[keep_all], classes[keep_all]
