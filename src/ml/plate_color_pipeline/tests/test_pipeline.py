import numpy as np
from plate_color import process_plate, PlateAppearance
from plate_color.color.classifier import classify_color
from plate_color.lighting.enhance import gray_world_wb
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
    # WB collapses a solid yellow toward gray -> would misclassify,
    # but process_plate classifies on the pre-WB (hue-preserving) path.
    yellow = plate_swatch(YELLOW_BG, DARK)
    assert process_plate(yellow).color == "yellow"
    assert classify_color(gray_world_wb(solid(YELLOW_BG))).color != "yellow"


def test_deterministic():
    crop = plate_swatch(YELLOW_BG, DARK)
    a, b = process_plate(crop), process_plate(crop)
    assert a.color == b.color and a.color_conf == b.color_conf
    assert np.array_equal(a.crop_for_ocr, b.crop_for_ocr)
