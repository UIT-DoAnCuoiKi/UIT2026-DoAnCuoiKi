import numpy as np
from plate_detect.inference.plate_detector import PlateDetection
from plate_detect.export.to_onnx import detection_delta, parity_ok


def _det(cx, conf):
    return PlateDetection((cx, 10, cx + 20, 30), 0, "bien_1hang", conf, np.zeros((1, 1, 3), np.uint8))


def test_identical_zero_delta():
    a = [_det(10, 0.9), _det(50, 0.8)]
    b = [_det(10, 0.9), _det(50, 0.8)]
    assert detection_delta(a, b) == 0.0
    assert parity_ok(a, b)


def test_count_mismatch_fails_parity():
    a = [_det(10, 0.9), _det(50, 0.8)]
    b = [_det(10, 0.9)]
    assert detection_delta(a, b) >= 1.0
    assert not parity_ok(a, b)
