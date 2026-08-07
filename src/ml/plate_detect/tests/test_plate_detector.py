import numpy as np
from plate_detect.inference.plate_detector import PlateDetection, build_detections

NAMES = {0: "bien_1hang", 1: "bien_2hang"}


def test_build_sorts_by_conf_desc():
    img = np.zeros((100, 100, 3), np.uint8)
    boxes = np.array([[10, 10, 30, 20], [40, 40, 70, 60]], float)
    dets = build_detections(boxes, np.array([0, 1]), np.array([0.6, 0.9]), img, NAMES)
    assert [d.conf for d in dets] == [0.9, 0.6]
    assert dets[0].cls_name == "bien_2hang"


def test_build_clamps_and_crops():
    img = np.zeros((50, 50, 3), np.uint8)
    boxes = np.array([[-5, -5, 40, 30]], float)     # negative → clamp to 0
    dets = build_detections(boxes, np.array([0]), np.array([0.8]), img, NAMES, pad=0)
    x1, y1, x2, y2 = dets[0].bbox_xyxy
    assert x1 == 0 and y1 == 0
    assert dets[0].crop.shape[0] == (y2 - y1) and dets[0].crop.shape[1] == (x2 - x1)


def test_empty_when_no_boxes():
    img = np.zeros((10, 10, 3), np.uint8)
    dets = build_detections(np.empty((0, 4)), np.array([]), np.array([]), img, NAMES)
    assert dets == []
