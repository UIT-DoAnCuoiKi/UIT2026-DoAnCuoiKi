from __future__ import annotations
import os
import glob

IMG_EXT = (".jpg", ".jpeg", ".png")

def validate_processed(processed_dir: str, num_classes: int = 2) -> list[str]:
    errors: list[str] = []
    for split in ("train", "val", "test"):
        img_dir = os.path.join(processed_dir, "images", split)
        lbl_dir = os.path.join(processed_dir, "labels", split)
        if not os.path.isdir(img_dir):
            continue
        img_stems = {os.path.splitext(os.path.basename(p))[0]
                     for p in glob.glob(os.path.join(img_dir, "*"))
                     if p.lower().endswith(IMG_EXT)}
        lbl_stems = {os.path.splitext(os.path.basename(p))[0]
                     for p in glob.glob(os.path.join(lbl_dir, "*.txt"))}
        for stem in img_stems - lbl_stems:
            errors.append(f"[{split}] image '{stem}' has no label")
        for stem in lbl_stems - img_stems:
            errors.append(f"[{split}] orphan label '{stem}' has no image")
        for lp in glob.glob(os.path.join(lbl_dir, "*.txt")):
            with open(lp) as f:
                lines = f.read().splitlines()
            for ln in lines:
                p = ln.split()
                if not p:
                    continue
                if len(p) < 5:
                    errors.append(f"[{split}] {os.path.basename(lp)}: line has {len(p)} fields, expected >= 5")
                    continue
                try:
                    cid = int(p[0])
                except ValueError:
                    errors.append(f"[{split}] {os.path.basename(lp)}: invalid class id '{p[0]}'")
                    continue
                if cid < 0 or cid >= num_classes:
                    errors.append(f"[{split}] {os.path.basename(lp)}: class {cid} out of range")
                try:
                    coords = [float(v) for v in p[1:5]]
                except ValueError:
                    errors.append(f"[{split}] {os.path.basename(lp)}: non-numeric coord in '{ln}'")
                    continue
                for v in coords:
                    if v < 0.0 or v > 1.0:
                        errors.append(f"[{split}] {os.path.basename(lp)}: coord {v} out of range")
    return errors

def assert_valid(processed_dir: str, num_classes: int = 2) -> None:
    errs = validate_processed(processed_dir, num_classes)
    if errs:
        raise ValueError("data-contract validation failed:\n  " + "\n  ".join(errs))
