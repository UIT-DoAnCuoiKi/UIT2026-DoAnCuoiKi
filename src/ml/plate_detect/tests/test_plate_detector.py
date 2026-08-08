import numpy as np
from plate_detect.inference.plate_detector import PlateDetection, build_detections

def test_build_detections_clamps_pads_sorts():
    image = np.zeros((100, 100, 3), np.uint8)
    boxes = np.array([[10, 10, 30, 30], [-5, -5, 20, 20]], float)
    classes = np.array([0, 1])
    confs = np.array([0.6, 0.9])
    names = {0: "bien_1hang", 1: "bien_2hang"}
    dets = build_detections(boxes, classes, confs, image, names, pad=4)
    assert [d.conf for d in dets] == [0.9, 0.6]          # sorted desc
    assert dets[0].bbox_xyxy[0] >= 0 and dets[0].bbox_xyxy[1] >= 0  # clamped
    assert dets[0].cls_name == "bien_2hang"
    assert dets[0].crop.size > 0

def test_empty_boxes_give_empty_list():
    image = np.zeros((10, 10, 3), np.uint8)
    assert build_detections(np.empty((0, 4)), np.empty((0,)), np.empty((0,)), image, {}) == []
