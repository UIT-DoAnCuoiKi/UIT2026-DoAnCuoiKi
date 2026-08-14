"""Tests for plate_color.lighting.enhance — lighting enhancement stack.

Each test probes a distinct, observable behaviour (mean V shift, hue
preservation, channel equalization) rather than implementation internals,
so the suite remains valid even if internal algorithms are swapped.
"""
from __future__ import annotations

import numpy as np
import cv2
from plate_color.lighting.enhance import (clahe_v, gamma, gray_world_wb,
                                          enhance)
from tests.synth import dark_crop, bright_crop, low_contrast_crop


def _mean_v(img):
    """Return mean HSV V-channel value of a BGR image."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2].mean()


def _contrast(img):
    """Return robust contrast (p95 − p5 of V) of a BGR image."""
    v = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2]
    p5, p95 = np.percentile(v, [5, 95])
    return p95 - p5


def test_clahe_v_preserves_hue():
    """CLAHE must only touch the V channel — hue/saturation must be stable.

    CLAHE is applied inside HSV so only the brightness (V) is redistribu‐
    ted; converting back to BGR preserves the original hue exactly.
    """
    img = np.full((40, 60, 3), (30, 200, 220), np.uint8)   # yellow
    h_before = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 0]
    h_after = cv2.cvtColor(clahe_v(img), cv2.COLOR_BGR2HSV)[:, :, 0]
    assert np.abs(h_after.astype(int) - h_before.astype(int)).max() <= 2


def test_gamma_direction():
    """g > 1 must brighten, g < 1 must darken.

    The LUT maps pixel p → (p/255)^(1/g) * 255, which is a standard
    power-law (gamma) curve.  g > 1 → exponent < 1 → curve bows up →
    midtones lift.  g < 1 → exponent > 1 → curve bows down → midtones drop.
    """
    img = np.full((10, 10, 3), 100, np.uint8)
    assert _mean_v(gamma(img, 1.6)) > 100
    assert _mean_v(gamma(img, 0.6)) < 100


def test_gray_world_neutralizes_cast():
    """Gray-world WB must equalize channel means.

    The gray-world assumption treats the scene average as neutral gray, so
    scaling each channel by (global_mean / channel_mean) removes systematic
    colour casts introduced by coloured lighting or sensor bias.
    """
    img = np.full((10, 10, 3), (200, 100, 50), np.uint8)   # strong cast
    out = gray_world_wb(img)
    ch = out.reshape(-1, 3).mean(axis=0)
    assert ch.max() - ch.min() < 10                        # channels equalized


def test_enhance_low_light_brightens():
    """enhance('low_light') must raise mean brightness above the input.

    Pipeline: gamma(1.6) lifts midtones, then CLAHE_V redistributes local
    contrast.  Gray-world WB runs last but preserves overall brightness.
    """
    d = dark_crop()
    assert _mean_v(enhance(d, "low_light")) > _mean_v(d)


def test_enhance_overexposed_darkens():
    """enhance('overexposed') must reduce mean brightness below the input.

    gamma(0.7) compresses the highlights; gray-world WB (applied after) is
    only a colour-cast correction and does not reverse the darkening.
    """
    b = bright_crop()
    assert _mean_v(enhance(b, "overexposed")) < _mean_v(b)


def test_enhance_low_contrast_expands():
    """enhance('low_contrast') must not reduce the tonal range.

    CLAHE redistributes the V-channel histogram locally, guaranteeing that
    the p95−p5 contrast is at least as high as the input.
    """
    lc = low_contrast_crop()
    assert _contrast(enhance(lc, "low_contrast")) >= _contrast(lc)
