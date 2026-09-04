import base64

import cv2
import numpy as np

from pipeline.onnx_pipeline import encode_crop_b64


def test_encode_crop_b64_round_trips_to_same_shape():
    crop = np.zeros((4, 8, 3), dtype=np.uint8)
    crop[:, :, 2] = 255  # red in BGR

    b64 = encode_crop_b64(crop)

    assert isinstance(b64, str) and b64
    raw = base64.b64decode(b64)
    decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape == (4, 8, 3)


def test_encode_crop_b64_empty_on_bad_input():
    assert encode_crop_b64(None) == ""
