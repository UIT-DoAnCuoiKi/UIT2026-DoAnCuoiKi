"""Synthetic plate-crop generators for lighting-condition tests.

Each helper returns a BGR uint8 ndarray shaped (H, W, 3).  The pixel values
are chosen so that `classify_lighting` maps each crop to the intended bucket —
see the threshold comments in `plate_color.lighting.metrics` for the exact
decision boundaries these values are designed to exercise.
"""
from __future__ import annotations

import cv2
import numpy as np


def solid(bgr, size=(80, 200)):
    """Return a flat-colour image of the given size (H, W).

    `bgr` is a 3-tuple in BGR order.  Using `np.empty` + slice-assign
    is slightly faster than `np.full` for large images.
    """
    h, w = size
    img = np.empty((h, w, 3), np.uint8)
    img[:] = bgr
    return img


def plate_swatch(bg_bgr, text_bgr, size=(80, 200)):
    """Render a fake plate string over a solid background.

    Useful for testing the colour classifier where text contrast matters;
    not used directly by the lighting tests but included for completeness.
    """
    img = solid(bg_bgr, size)
    cv2.putText(img, "51A-123", (8, size[0] // 2 + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_bgr, 3)
    return img


def dark_crop(size=(80, 200)):
    """V ≈ 40 on a 0-255 scale → well below LOWLIGHT_MEAN (60), → 'low_light'."""
    return solid((40, 40, 40), size)


def bright_crop(size=(80, 200)):
    """V ≈ 230 → well above OVEREXP_MEAN (200), no glare fraction → 'overexposed'."""
    return solid((230, 230, 230), size)


def low_contrast_crop(size=(80, 200)):
    """Two adjacent grey bands (128 and 140): p95-p5 ≈ 12 → below LOWCONTRAST_RANGE (50).

    Mean V ≈ 134, which is between LOWLIGHT_MEAN and OVEREXP_MEAN, so the
    low_contrast branch is reached before returning 'normal'.
    """
    img = solid((128, 128, 128), size)
    img[:, : size[1] // 2] = 140
    return img


def glare_crop(size=(80, 200)):
    """A dark background with a bright saturated patch covering ~15 % of pixels.

    The patch has V=255 ≥ 250, pushing glare fraction above GLARE_FRAC (0.10).
    The base (90,90,90) keeps mean_v low so only the glare check fires.
    """
    img = solid((90, 90, 90), size)
    img[10:50, 10:70] = 255           # ~15% of pixels clipped
    return img


def normal_crop(size=(80, 200)):
    """A smooth horizontal gradient from V≈60 to V≈200.

    mean_v ≈ 130 (between thresholds), contrast ≈ 140 (above LOWCONTRAST_RANGE),
    glare fraction ≈ 0 → 'normal'.
    """
    h, w = size
    row = np.linspace(60, 200, w).astype(np.uint8)
    gray = np.repeat(row[None, :], h, axis=0)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
