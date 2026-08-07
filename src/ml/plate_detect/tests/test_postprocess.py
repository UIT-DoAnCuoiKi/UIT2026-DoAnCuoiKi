import numpy as np
from plate_detect.inference.postprocess import nms, decode_v26, decode_v8

def test_nms_removes_overlap():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], float)
    scores = np.array([0.9, 0.8, 0.7])
    keep = nms(boxes, scores, iou_thr=0.5)
    assert 0 in keep and 2 in keep and 1 not in keep

def test_decode_v26_filters_conf_no_nms():
    raw = np.array([[0, 0, 10, 10, 0.9, 0],
                    [1, 1, 11, 11, 0.8, 0],     # overlaps but kept (NMS-free)
                    [0, 0, 5, 5, 0.1, 1]], float)
    boxes, scores, classes = decode_v26(raw, conf=0.25)
    assert len(boxes) == 2
    assert set(scores.round(1)) == {0.9, 0.8}

def test_decode_v8_conf_and_nms():
    # 2 classes; head shape (4+2, M) = (6, 3)
    xywh = np.array([[5, 5, 10, 10], [5.5, 5.5, 10, 10], [80, 80, 6, 6]]).T   # (4,3)
    cls_scores = np.array([[0.9, 0.85, 0.1], [0.0, 0.0, 0.7]])                # (2,3)
    raw = np.vstack([xywh, cls_scores])                                       # (6,3)
    boxes, scores, classes = decode_v8(raw, conf=0.25, iou=0.5, nc=2)
    assert len(boxes) == 2            # the 0.85 box suppressed by NMS with 0.9
    assert 0 in classes and 1 in classes
