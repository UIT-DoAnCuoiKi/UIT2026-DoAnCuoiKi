from __future__ import annotations
import os
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .data.bbox import polygon_to_bbox


def _crop_from_record(rec, cid):
    img = cv2.imread(rec["image_path"])
    if img is None:
        return None
    H, W = img.shape[:2]
    for c, coords in rec["objects"]:
        if c != cid:
            continue
        bb = polygon_to_bbox(coords)
        if not bb:
            continue
        xc, yc, w, h = bb
        x1 = int((xc - w / 2) * W); y1 = int((yc - h / 2) * H)
        x2 = int((xc + w / 2) * W); y2 = int((yc + h / 2) * H)
        if x2 > x1 and y2 > y1:
            return img[y1:y2, x1:x2][:, :, ::-1]   # BGR→RGB
    return None


def class_map_grid(records, class_map, out_png: str, per_class: int = 8) -> str:
    ids = sorted(class_map)
    fig, axes = plt.subplots(len(ids), per_class, figsize=(per_class * 1.6, len(ids) * 1.8))
    axes = np.atleast_2d(axes)
    for row, cid in enumerate(ids):
        picked = 0
        for rec in records:
            if picked >= per_class:
                break
            crop = _crop_from_record(rec, cid)
            if crop is not None and crop.size:
                ax = axes[row][picked]
                ax.imshow(crop); ax.axis("off")
                if picked == 0:
                    ax.set_ylabel(f"{cid}: {class_map[cid]}", rotation=0, labelpad=40)
                picked += 1
        for j in range(picked, per_class):
            axes[row][j].axis("off")
    fig.suptitle("Class-map visual verify (BSD/BSV → layout)")
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=110); plt.close(fig)
    return out_png


def annotate_and_save(detector, image_path: str, out_png: str) -> str:
    img = cv2.imread(image_path)
    for d in detector.detect(img):
        x1, y1, x2, y2 = d.bbox_xyxy
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"{d.cls_name} {d.conf:.2f}", (x1, max(0, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    cv2.imwrite(out_png, img)
    return out_png


def qualitative_grid(detector, image_paths, out_png: str, n: int = 9) -> str:
    paths = list(image_paths)[:n]
    cols = 3
    rows = (len(paths) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3))
    axes = np.atleast_1d(axes).ravel()
    for ax, pth in zip(axes, paths):
        img = cv2.imread(pth)
        for d in detector.detect(img):
            x1, y1, x2, y2 = d.bbox_xyxy
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        ax.imshow(img[:, :, ::-1]); ax.axis("off")
    for ax in axes[len(paths):]:
        ax.axis("off")
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    fig.tight_layout(); fig.savefig(out_png, dpi=110); plt.close(fig)
    return out_png
