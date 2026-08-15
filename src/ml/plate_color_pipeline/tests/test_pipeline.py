import numpy as np
from plate_color import process_plate, PlateAppearance
from plate_color.color.classifier import classify_color
from plate_color.lighting.enhance import clahe_v, gray_world_wb
from tests.synth import plate_swatch, dark_crop, solid

YELLOW_BG = (30, 200, 220); DARK = (20, 20, 20)


def test_returns_plate_appearance():
    a = process_plate(plate_swatch(YELLOW_BG, DARK))
    assert isinstance(a, PlateAppearance)
    assert a.color == "yellow"
    assert a.crop_for_ocr.shape == plate_swatch(YELLOW_BG, DARK).shape


def test_lighting_label_flows_through():
    assert process_plate(dark_crop()).lighting == "low_light"


def test_degenerate_input():
    tiny = np.zeros((4, 4, 3), np.uint8)
    a = process_plate(tiny)
    assert a.color == "unknown"
    assert a.lighting == "degenerate"
    assert a.crop_for_ocr is tiny            # original returned untouched


def test_wb_isolated_from_color():
    """Color is stable on path A regardless of WB; WB alone would flip it.

    Positive direction: both clahe_v (path A) and process_plate must classify
    a yellow crop as 'yellow' — proving path A produces the correct label.
    Negative direction: prepending gray-world WB collapses the hue toward gray,
    confirming WB would corrupt the color decision if it ran on path A.
    """
    yellow = solid(YELLOW_BG)
    # Positive: path-A classification and process_plate both give "yellow".
    assert classify_color(clahe_v(yellow)).color == "yellow"
    assert process_plate(yellow).color == "yellow"
    # Negative: WB on its own shifts hue enough to break yellow detection.
    assert classify_color(gray_world_wb(yellow)).color != "yellow"


def test_deterministic():
    crop = plate_swatch(YELLOW_BG, DARK)
    a, b = process_plate(crop), process_plate(crop)
    assert a.color == b.color and a.color_conf == b.color_conf
    assert np.array_equal(a.crop_for_ocr, b.crop_for_ocr)
