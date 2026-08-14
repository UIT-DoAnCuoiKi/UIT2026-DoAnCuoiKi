"""Lighting enhancement primitives for Vietnamese plate OCR pre-processing.

The module provides low-level image operators (CLAHE, gamma, gray-world WB,
glare reduction) and a single entry point — ``enhance`` — that selects the
right operator chain based on the lighting condition label produced by
``classify_lighting`` in the metrics module.

Design rationale
----------------
All tone operations run in HSV so that colour information (hue/saturation)
is never corrupted by brightness adjustments.  The gray-world white-balance
step runs **last and unconditionally** on every condition: it fixes residual
colour casts from mixed or coloured parking-lot lighting without interfering
with the tone correction applied above it.

Dispatch table (``enhance``)
----------------------------
- ``low_light``    → gamma(1.6) then CLAHE_V   — lift midtones first so CLAHE
                     has more local structure to redistribute.
- ``low_contrast`` → CLAHE_V only              — contrast is the only issue.
- ``overexposed``  → gamma(0.7)                — compress highlights.
- ``glare``        → reduce_glare then CLAHE_V — roll back hotspots, then
                     spread remaining contrast.
- ``normal`` / ``degenerate`` → no tone change; only gray-world WB applied.
"""
from __future__ import annotations

import cv2
import numpy as np


def clahe_v(crop_bgr: np.ndarray, clip: float = 2.0, grid: int = 8) -> np.ndarray:
    """Apply CLAHE to the V (brightness) channel of a BGR plate crop.

    CLAHE (Contrast Limited Adaptive Histogram Equalisation) is applied
    inside HSV so that hue and saturation are completely untouched — only
    local contrast in the luminance dimension is adjusted.  This is critical
    for plate-colour classification downstream: boosting contrast without
    shifting hue keeps the yellow/white/blue plate distinction reliable.

    Args:
        crop_bgr: BGR uint8 image (H, W, 3).
        clip: CLAHE clip limit — caps redistribution to avoid amplifying noise.
        grid: Tile grid size in pixels; smaller tiles = more local contrast.

    Returns:
        BGR uint8 image with enhanced local contrast on V only.
    """
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    cl = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    hsv[:, :, 2] = cl.apply(hsv[:, :, 2])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def gamma(crop_bgr: np.ndarray, g: float) -> np.ndarray:
    """Apply power-law (gamma) tone mapping via a 256-entry LUT.

    The LUT maps input intensity p → (p/255)^(1/g) * 255.

    - g > 1: exponent < 1 → curve bows upward → midtones brighten.
    - g < 1: exponent > 1 → curve bows downward → midtones darken.

    Using a pre-computed LUT (vs per-pixel arithmetic) keeps this O(1)
    on the lookup table regardless of image resolution.

    Args:
        crop_bgr: BGR uint8 image.
        g: Gamma value.  g > 1 brightens; g < 1 darkens.

    Returns:
        Tone-mapped BGR uint8 image.
    """
    lut = (np.linspace(0, 1, 256) ** (1.0 / g) * 255).clip(0, 255).astype(np.uint8)
    return cv2.LUT(crop_bgr, lut)


def gray_world_wb(crop_bgr: np.ndarray) -> np.ndarray:
    """Gray-world white balance: scale each BGR channel to a neutral mean.

    The gray-world assumption holds that the average colour of a natural
    scene (or a plate surface under mixed lighting) is achromatic — i.e. the
    mean R, G, B values should all equal the overall mean.  Dividing each
    channel by its own mean and multiplying by the global mean removes
    systematic colour casts caused by coloured ambient lighting (sodium lamps,
    LEDs, sunlight at different colour temperatures) or camera AWB drift.

    This function is applied **last** in ``enhance`` so it corrects residual
    colour cast without fighting the tone-correction steps that precede it.

    Args:
        crop_bgr: BGR uint8 image.

    Returns:
        White-balanced BGR uint8 image.
    """
    out = crop_bgr.astype(np.float32)
    # means[0]=B, [1]=G, [2]=R  (BGR channel order)
    means = out.reshape(-1, 3).mean(axis=0)
    # Target: bring every channel mean to the global average
    k = float(means.mean())
    for i in range(3):
        out[:, :, i] *= k / (means[i] + 1e-6)   # 1e-6 guards against zero channels
    return np.clip(out, 0, 255).astype(np.uint8)


def reduce_glare(crop_bgr: np.ndarray) -> np.ndarray:
    """Compress specular highlights via a darkening gamma curve (g = 0.7).

    Glare regions are overexposed pixels where the sensor is clipped; a
    soft power-law compression (gamma < 1) rolls back the brightest pixels
    more aggressively than midtones, reducing visible hot-spots before CLAHE
    can redistribute what remains.

    Args:
        crop_bgr: BGR uint8 image with highlight clipping.

    Returns:
        Highlight-compressed BGR uint8 image.
    """
    return gamma(crop_bgr, 0.7)


def enhance(crop_bgr: np.ndarray, condition: str) -> np.ndarray:
    """Condition-dispatched lighting enhancement for OCR pre-processing.

    Applies the appropriate tone-correction stack for the given lighting
    condition label (as produced by ``classify_lighting``), followed
    unconditionally by gray-world white balance.

    Gray-world WB is always the **last** step because it is a colour-cast
    fix, not a tone operation; running it after tone correction avoids
    interference between the two corrections.

    Dispatch:
    - ``low_light``    — gamma(1.6) brightens, then CLAHE_V redistributes contrast.
    - ``low_contrast`` — CLAHE_V only (brightness is already fine).
    - ``overexposed``  — gamma(0.7) compresses highlights.
    - ``glare``        — reduce_glare (gamma 0.7) then CLAHE_V for local contrast.
    - ``normal`` / ``degenerate`` — no tone change; only WB applied.

    Args:
        crop_bgr: BGR uint8 plate crop.
        condition: Lighting label string from ``classify_lighting``.

    Returns:
        Enhanced BGR uint8 image ready for OCR.
    """
    out = crop_bgr
    if condition == "low_light":
        out = clahe_v(gamma(out, 1.6))
    elif condition == "low_contrast":
        out = clahe_v(out)
    elif condition == "overexposed":
        out = gamma(out, 0.7)
    elif condition == "glare":
        out = clahe_v(reduce_glare(out))
    # "normal" and "degenerate": no tone change — only WB below

    # Gray-world WB runs last and unconditionally: it corrects colour casts
    # from mixed parking-lot lighting without reversing the tone correction above.
    return gray_world_wb(out)
