from __future__ import annotations
import os
import random
import cv2
import numpy as np


def make_raw_fixture(root: str, n_per_split: int = 10, seed: int = 0) -> None:
    """Write an A1-raw-shaped synthetic dataset (polygon 4-corner labels)."""
    rng = random.Random(seed)
    for split in ("train", "val"):
        img_dir = os.path.join(root, "images", split)
        lbl_dir = os.path.join(root, "labels", split)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)
        for i in range(n_per_split):
            H, W = 480, 640
            img = np.full((H, W, 3), 90, np.uint8)
            cls = i % 2  # alternate 1-row / 2-row
            pw = rng.uniform(0.28, 0.36) * W
            ph = (pw / rng.uniform(3.5, 4.5)) if cls == 0 else (pw / rng.uniform(1.2, 1.5))
            cx = rng.uniform(0.35, 0.65) * W
            cy = rng.uniform(0.35, 0.65) * H
            x1, y1 = int(cx - pw / 2), int(cy - ph / 2)
            x2, y2 = int(cx + pw / 2), int(cy + ph / 2)
            cv2.rectangle(img, (x1, y1), (x2, y2), (235, 235, 235), -1)
            cv2.imwrite(os.path.join(img_dir, f"{split}_{i}.jpg"), img)
            def c(v, m):
                return max(0.0, min(1.0, v / m))
            corners = [c(x1, W), c(y1, H), c(x2, W), c(y1, H),
                       c(x2, W), c(y2, H), c(x1, W), c(y2, H)]
            line = str(cls) + " " + " ".join(f"{v:.6f}" for v in corners)
            with open(os.path.join(lbl_dir, f"{split}_{i}.txt"), "w") as f:
                f.write(line + "\n")
