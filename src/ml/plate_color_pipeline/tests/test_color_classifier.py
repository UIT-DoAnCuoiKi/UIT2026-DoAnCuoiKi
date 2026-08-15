import numpy as np
from plate_color.color.classifier import classify_color, ColorResult
from tests.synth import plate_swatch, solid

WHITE_BG = (235, 235, 235); DARK = (20, 20, 20)
YELLOW_BG = (30, 200, 220)
BLUE_BG = (200, 60, 20); LIGHT = (240, 240, 240)
RED_BG = (30, 30, 200)


def test_white_dark_text():
    assert classify_color(plate_swatch(WHITE_BG, DARK)).color == "white"


def test_yellow_dark_text():
    assert classify_color(plate_swatch(YELLOW_BG, DARK)).color == "yellow"


def test_blue_light_text():          # light-on-dark: prototype failed here
    assert classify_color(plate_swatch(BLUE_BG, LIGHT)).color == "blue"


def test_red_light_text():           # light-on-dark: prototype failed here
    assert classify_color(plate_swatch(RED_BG, LIGHT)).color == "red"


def test_conf_in_range():
    r = classify_color(plate_swatch(YELLOW_BG, DARK))
    assert isinstance(r, ColorResult)
    assert 0.0 <= r.conf <= 1.0


def test_degenerate_returns_unknown():
    assert classify_color(np.zeros((4, 4, 3), np.uint8)).color == "unknown"


def test_dark_crop_unknown():        # mostly-dark, nothing classifiable
    assert classify_color(solid((10, 10, 10))).color == "unknown"
