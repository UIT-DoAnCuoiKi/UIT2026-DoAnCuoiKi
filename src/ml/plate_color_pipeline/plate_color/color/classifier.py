"""HSV colour classifier for Vietnamese licence-plate crops.

Design rationale — area-dominance vs. brightest-pixel heuristic
----------------------------------------------------------------
An earlier prototype in ``docs/research/tools/color_check.py`` assumed the
plate background is the *brightest* pixel cluster.  That assumption is wrong
for VN blue and red plates, which have *light text on a dark coloured
background*: the bright pixels are the white/yellow text, not the plate.

The fix used here is **area dominance**: we count every pixel that falls into
one of four colour buckets (white, red, yellow, blue), then pick the *majority*
bucket as the plate colour.  On a white-background plate the large white area
wins easily; on a blue-background plate the many blue pixels outvote the
handful of light-text pixels.  No assumption about which colour is brighter is
made — only which colour occupies more area.

Two safety gates prevent low-quality predictions from reaching callers:
  1. ``MIN_CONSIDERED_FRAC`` gate — if too few pixels are classifiable at all
     (e.g. a mostly dark/shadow crop) we cannot form a reliable count.
  2. ``CONF_FLOOR`` gate — if the winning bucket does not have a clear majority
     of classifiable pixels (e.g. a 50/50 white+yellow split) we return
     ``unknown`` rather than guess.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from . import thresholds as T


@dataclass
class ColorResult:
    """Result of ``classify_color``.

    Attributes:
        color: Predicted plate background colour — one of ``"white"``,
            ``"yellow"``, ``"blue"``, ``"red"``, or ``"unknown"``.
        conf:  Winner's share of classifiable pixels (0.0–1.0).
            Always ``0.0`` when *color* is ``"unknown"`` due to size or
            coverage failure; may be non-zero for a confidence-floor unknown.
        features: Diagnostic dict with ``"counts"`` (per-colour pixel counts)
            and ``"considered_frac"`` (classifiable pixels / total pixels).
    """

    color: str
    conf: float
    features: dict


def classify_color(crop_bgr: np.ndarray) -> ColorResult:
    """Classify the background colour of a licence-plate crop.

    Parameters
    ----------
    crop_bgr:
        BGR uint8 image of a plate crop (any reasonable aspect ratio).

    Returns
    -------
    ColorResult
        ``color`` is ``"unknown"`` when:

        * the crop is smaller than 8×8 pixels (degenerate input), OR
        * the fraction of classifiable pixels is below ``MIN_CONSIDERED_FRAC``
          (e.g. a nearly-black crop where nothing is bright or saturated), OR
        * the winner's share of classifiable pixels is below ``CONF_FLOOR``
          (ambiguous colour distribution — better to abstain than guess wrong).
    """
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return ColorResult("unknown", 0.0, {})

    # Thu hẹp về đúng vùng nền biển trước khi đếm màu: crop từ PlateDetector có
    # thêm biên (pad=4) quanh bbox YOLO, và rìa crop nhỏ dễ dính quang sai màu/
    # nén JPEG — cả hai có thể lệch hue khỏi nền biển thật, gây nhận nhầm màu.
    # Dùng Otsu + contour lớn nhất (cùng kỹ thuật deskew() trong pipeline/ocr.py)
    # để tìm vùng nền biển thật, không đoán 1 tỉ lệ % cố định. Không tìm được
    # contour đủ tin cậy thì lùi về dùng nguyên crop, không cố ép.
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) >= T.COLOR_MIN_CONTOUR_AREA_FRAC * mask.size:
            x, y, cw, ch = cv2.boundingRect(largest)
            if cw >= 4 and ch >= 4:
                crop_bgr = crop_bgr[y:y + ch, x:x + cw]

    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    H = hsv[:, :, 0].astype(int)   # 0–179; cast to int so comparisons are safe
    S = hsv[:, :, 1]
    V = hsv[:, :, 2]

    total = crop_bgr.shape[0] * crop_bgr.shape[1]  # dùng kích thước sau khi cắt viền, không phải crop gốc

    # Saturation mask — only chromatic (coloured) pixels are tested against hue bands.
    sat = S >= T.SAT_MIN_FOR_HUE

    # Count pixels in each colour bucket.
    # Area dominance: we count *all* pixels of each colour, not just the brightest.
    # On a blue plate the many dark-blue background pixels outvote the few white
    # text pixels, correctly identifying the plate colour as blue.
    counts = {
        "white":  int(np.count_nonzero((S < T.WHITE_SAT_MAX) & (V >= T.WHITE_VAL_MIN))),
        # Red wraps around the HSV hue cylinder — two arcs capture it.
        "red":    int(np.count_nonzero(sat & ((H < T.HUE_RED_HI) | (H >= T.HUE_RED_WRAP)))),
        "yellow": int(np.count_nonzero(sat & (H >= T.HUE_YELLOW_LO) & (H < T.HUE_YELLOW_HI))),
        "blue":   int(np.count_nonzero(sat & (H >= T.HUE_BLUE_LO)  & (H < T.HUE_BLUE_HI))),
    }

    considered = sum(counts.values())
    features = {"counts": counts, "considered_frac": considered / total}

    # Gate 1: too few classifiable pixels → crop is mostly shadow/noise, abstain.
    if considered < T.MIN_CONSIDERED_FRAC * total:
        return ColorResult("unknown", 0.0, features)

    color = max(counts, key=counts.__getitem__)
    conf = counts[color] / considered

    # Gate 2: winner does not have a clear majority → result would be unreliable.
    if conf < T.CONF_FLOOR:
        return ColorResult("unknown", conf, features)

    return ColorResult(color, conf, features)
