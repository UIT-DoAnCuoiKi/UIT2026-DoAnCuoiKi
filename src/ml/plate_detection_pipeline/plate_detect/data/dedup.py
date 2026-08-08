from __future__ import annotations
import cv2
import numpy as np


def ahash(image: np.ndarray) -> int:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    small = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA)
    bits = (small > small.mean()).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(b)
    return h


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def find_duplicates(
    train: dict[str, int], test: dict[str, int], threshold: int = 5
) -> list[tuple[str, str, int]]:
    dups = []
    train_items = list(train.items())
    for qn, qh in test.items():
        best_name, best_d = None, 65
        for tn, th in train_items:
            d = hamming(qh, th)
            if d < best_d:
                best_name, best_d = tn, d
        if best_name is not None and best_d <= threshold:
            dups.append((qn, best_name, best_d))
    return dups
