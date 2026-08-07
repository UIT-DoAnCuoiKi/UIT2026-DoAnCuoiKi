from __future__ import annotations
import glob
import os
from typing import Protocol

IMG_EXT = (".jpg", ".jpeg", ".png")

class DatasetAdapter(Protocol):
    def class_names(self) -> dict[int, str]: ...
    def read_raw(self, raw_dir: str) -> list[dict]: ...

class A1Adapter:
    """Kaggle duydieunguyen/licenseplates: images/<split>, labels/<split>, polygon labels."""
    def class_names(self) -> dict[int, str]:
        return {0: "bien_1hang", 1: "bien_2hang"}

    def read_raw(self, raw_dir: str) -> list[dict]:
        records = []
        for split in ("train", "val"):
            img_dir = os.path.join(raw_dir, "images", split)
            lbl_dir = os.path.join(raw_dir, "labels", split)
            if not os.path.isdir(img_dir):
                continue
            for ip in sorted(glob.glob(os.path.join(img_dir, "*"))):
                if not ip.lower().endswith(IMG_EXT):
                    continue
                stem = os.path.splitext(os.path.basename(ip))[0]
                lp = os.path.join(lbl_dir, stem + ".txt")
                objects = []
                if os.path.exists(lp):
                    with open(lp) as fh:
                        label_lines = fh.read().splitlines()
                    for ln in label_lines:
                        parts = ln.split()
                        if len(parts) >= 9 and parts[0].lstrip("-").isdigit():
                            objects.append((int(parts[0]), list(map(float, parts[1:9]))))
                records.append({"split": split, "image_path": ip, "objects": objects})
        return records
