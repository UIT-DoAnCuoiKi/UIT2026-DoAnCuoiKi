"""Tests for plate_color.lighting.metrics — lighting metrics and condition classifier."""
import numpy as np

from plate_color.lighting.metrics import classify_lighting, lighting_metrics
from tests.synth import (bright_crop, dark_crop, glare_crop,
                         low_contrast_crop, normal_crop)


def test_metrics_keys():
    m = lighting_metrics(normal_crop())
    assert set(m) == {"mean_v", "contrast", "glare", "shadow"}


def test_conditions():
    assert classify_lighting(dark_crop()) == "low_light"
    assert classify_lighting(bright_crop()) == "overexposed"
    assert classify_lighting(low_contrast_crop()) == "low_contrast"
    assert classify_lighting(glare_crop()) == "glare"
    assert classify_lighting(normal_crop()) == "normal"


def test_degenerate():
    assert classify_lighting(np.zeros((4, 4, 3), np.uint8)) == "degenerate"
