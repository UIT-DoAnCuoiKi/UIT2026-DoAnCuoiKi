"""Lighting metrics and condition classifier for Vietnamese plate crops.

The pipeline converts a BGR crop to the HSV V-channel (0–255) and derives
four scalar metrics that together capture the dominant lighting pathology.
`classify_lighting` maps those metrics to a single condition label, consumed
by the enhancement stage to choose the right CLAHE / normalisation strategy.

Check order in `classify_lighting` matters — glare must precede overexposed
because a glare-heavy crop also has a high mean_v and would be
misclassified as overexposed if the mean check ran first.
"""
from __future__ import annotations

import cv2
import numpy as np

# ── thresholds ────────────────────────────────────────────────────────────────
# Fraction of pixels whose V value is clipped at ≥250 (out of 255).
# Above 10 % indicates specular reflections or direct sunlight on metal.
GLARE_FRAC = 0.10

# Mean V above 200 (≈ 78 % of full scale) → the whole plate is washed out.
OVEREXP_MEAN = 200.0

# Mean V below 60 (≈ 24 % of full scale) → underground / night parking.
LOWLIGHT_MEAN = 60.0

# p95 − p5 of V below 50 → the crop lacks the tonal range needed for OCR
# (e.g. same-colour paint or foggy/hazy capture).
LOWCONTRAST_RANGE = 50.0


def lighting_metrics(crop_bgr: np.ndarray) -> dict:
    """Compute four scalar lighting metrics from a BGR plate crop.

    Returns a dict with keys:
    - ``mean_v``   — mean brightness on the V channel.
    - ``contrast`` — p95 − p5 of V; robust to outliers, unlike std-dev.
    - ``glare``    — fraction of pixels with V ≥ 250 (clipped highlights).
    - ``shadow``   — fraction with V ≤ 10 (crushed shadows).

    All values are plain Python floats for JSON / dataclass compatibility.
    """
    v = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)[:, :, 2]
    p5, p95 = np.percentile(v, [5, 95])
    return {
        "mean_v": float(v.mean()),
        "contrast": float(p95 - p5),
        "glare": float(np.count_nonzero(v >= 250) / v.size),
        "shadow": float(np.count_nonzero(v <= 10) / v.size),
    }


def classify_lighting(crop_bgr: np.ndarray) -> str:
    """Return a single lighting-condition label for a plate crop.

    Labels (in evaluation order):
    1. ``degenerate``   — crop is too small to be a real plate (< 8 px in any dim).
    2. ``glare``        — >10 % of pixels are specularly clipped (V ≥ 250).
    3. ``overexposed``  — mean V > 200; broad highlight saturation.
    4. ``low_light``    — mean V < 60; dark environment.
    5. ``low_contrast`` — p95−p5 < 50; tonal range too narrow for OCR.
    6. ``normal``       — none of the above; standard enhancement is sufficient.

    Order is intentional: glare *before* overexposed prevents a glare crop
    (high mean_v) from being labelled 'overexposed'; similarly the two
    mean-based checks must precede the contrast check.
    """
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return "degenerate"

    m = lighting_metrics(crop_bgr)

    if m["glare"] > GLARE_FRAC:
        return "glare"
    if m["mean_v"] > OVEREXP_MEAN:
        return "overexposed"
    if m["mean_v"] < LOWLIGHT_MEAN:
        return "low_light"
    if m["contrast"] < LOWCONTRAST_RANGE:
        return "low_contrast"
    return "normal"
