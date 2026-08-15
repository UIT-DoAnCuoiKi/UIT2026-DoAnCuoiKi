import numpy as np
from plate_color import PlateAppearance


def test_plate_appearance_fields():
    a = PlateAppearance("white", 0.9, {"k": 1}, "normal", np.zeros((4, 4, 3), np.uint8))
    assert a.color == "white"
    assert a.color_conf == 0.9
    assert a.lighting == "normal"
    assert a.crop_for_ocr.shape == (4, 4, 3)
