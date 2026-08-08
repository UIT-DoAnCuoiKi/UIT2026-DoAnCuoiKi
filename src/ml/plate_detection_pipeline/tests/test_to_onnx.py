import numpy as np
from plate_detect.inference.plate_detector import PlateDetection
from plate_detect.export.to_onnx import detection_delta, parity_ok

def _det(x1, y1, x2, y2, conf, cid=0):
    return PlateDetection((x1, y1, x2, y2), cid, "bien_1hang", conf, np.zeros((2, 2, 3), np.uint8))

def test_identical_detections_parity_ok():
    a = [_det(0, 0, 10, 10, 0.9)]
    b = [_det(0, 0, 10, 10, 0.9)]
    assert detection_delta(a, b) == 0.0 and parity_ok(a, b)

def test_count_mismatch_breaks_parity():
    a = [_det(0, 0, 10, 10, 0.9)]
    assert not parity_ok(a, [])
