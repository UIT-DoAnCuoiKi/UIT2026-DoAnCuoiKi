import numpy as np
from plate_detect.inference.postprocess import nms, decode_v26, decode_v8

def test_nms_suppresses_overlap():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], float)
    scores = np.array([0.9, 0.8, 0.7])
    keep = nms(boxes, scores, iou_thr=0.5)
    assert 0 in keep and 2 in keep and 1 not in keep

def test_decode_v26_filters_by_conf():
    raw = np.array([[0, 0, 10, 10, 0.9, 0], [0, 0, 5, 5, 0.1, 1]], float)  # (N,6)
    boxes, scores, classes = decode_v26(raw, conf=0.5)
    assert len(scores) == 1 and classes[0] == 0

def test_decode_v8_transposes_and_nms():
    # (4+nc, M) with nc=2, M=2; two overlapping high-conf boxes same class → 1 kept
    raw = np.array([
        [5, 5],        # xc
        [5, 5],        # yc
        [10, 10],      # w
        [10, 10],      # h
        [0.9, 0.85],   # class0 score
        [0.0, 0.0],    # class1 score
    ], float)
    boxes, scores, classes = decode_v8(raw, conf=0.5, iou=0.5, nc=2)
    assert len(scores) == 1 and classes[0] == 0
