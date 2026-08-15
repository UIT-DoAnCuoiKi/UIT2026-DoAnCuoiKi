"""Split-path plate processing pipeline.

``process_plate`` runs two independent paths on every crop:

Path A — color classification (hue-preserving):
    Apply CLAHE on the V channel only (no white balance) so that hue is
    completely untouched.  The color decision is made on this pre-WB crop.
    White balance must NOT run here: gray-world WB collapses a solid yellow
    toward neutral gray (equal channel means), which would cause a
    misclassification.  Keeping WB out of path A is what makes the color
    label trustworthy under mixed parking-lot lighting.

Path B — OCR enhancement (full stack):
    Classify the lighting condition on the raw crop, then apply the
    condition-appropriate tone correction followed by gray-world white
    balance.  WB is intentionally confined to this path so it can never
    corrupt the color decision made in path A.

The two paths share the same input ``crop_bgr`` but produce independent
outputs.  Only ``PlateAppearance.crop_for_ocr`` comes from path B.
"""
from __future__ import annotations

import numpy as np

from .types import PlateAppearance
from .color.classifier import classify_color
from .lighting.metrics import classify_lighting
from .lighting.enhance import clahe_v, enhance


def process_plate(crop_bgr: np.ndarray) -> PlateAppearance:
    """Analyse a single plate crop and return its color + lighting + OCR-ready image.

    Degenerate crops (height < 8 px or width < 8 px) are returned immediately
    with ``color="unknown"``, ``lighting="degenerate"``, and
    ``crop_for_ocr`` pointing to the *original* crop object (no copy).

    For valid crops, two isolated processing paths run:
    - Path A: ``clahe_v(crop_bgr)`` → ``classify_color`` (no WB — hue preserved).
    - Path B: ``classify_lighting(crop_bgr)`` → ``enhance(crop_bgr, condition)``
      (full stack including gray-world WB for OCR readiness).

    Args:
        crop_bgr: BGR uint8 ndarray of the plate region of interest.

    Returns:
        A ``PlateAppearance`` instance with fields populated from both paths.
    """
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return PlateAppearance("unknown", 0.0, {}, "degenerate", crop_bgr)

    # --- Path A: color classification -------------------------------------------
    # CLAHE on V only preserves hue + saturation so the yellow/white/blue
    # decision is not contaminated by gray-world WB (which would shift hue).
    # White balance is intentionally absent here — it lives only in path B.
    crop_a = clahe_v(crop_bgr)
    cr = classify_color(crop_a)

    # --- Path B: OCR enhancement ------------------------------------------------
    # Full enhance stack: tone correction appropriate to the lighting condition,
    # then gray-world WB.  WB is confined to this path to keep path A clean.
    cond = classify_lighting(crop_bgr)
    crop_b = enhance(crop_bgr, cond)

    return PlateAppearance(cr.color, cr.conf, cr.features, cond, crop_b)
