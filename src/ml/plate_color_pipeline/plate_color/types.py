"""Result types for the plate_color pipeline."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PlateAppearance:
    """Outcome of one plate analysis pass.

    Produced by the classifier + enhancer and consumed by the OCR stage.
    All downstream tasks receive a single instance rather than raw dicts so
    that new fields can be added without breaking callers.
    """

    # Background color label (white|yellow|blue|red|unknown).
    color: str
    # Softmax-like confidence in [0, 1] for the chosen color.
    color_conf: float
    # Raw HSV histogram / saturation stats forwarded for debugging / retraining.
    color_features: dict
    # Lighting condition (normal|low_light|overexposed|low_contrast|glare|degenerate).
    lighting: str
    # CLAHE-enhanced BGR crop ready for OCR — same spatial size as the input crop.
    crop_for_ocr: np.ndarray
