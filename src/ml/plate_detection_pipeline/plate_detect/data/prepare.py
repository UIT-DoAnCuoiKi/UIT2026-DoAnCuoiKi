from __future__ import annotations
import os
import shutil
from collections import Counter
import cv2
import yaml
from ..config import Config
from .adapters import A1Adapter
from .bbox import polygon_to_bbox
from .class_map import infer_layout_map, verify_class_map
from .split import stratified_split
from .dedup import ahash, find_duplicates
from .validate import validate_processed


def _majority_class(objects: list) -> int:
    if not objects:
        return 0
    return Counter(cid for cid, _ in objects).most_common(1)[0][0]


def _write_pair(processed_dir, split, stem, src_img, bbox_lines):
    img_out = os.path.join(processed_dir, "images", split)
    lbl_out = os.path.join(processed_dir, "labels", split)
    os.makedirs(img_out, exist_ok=True)
    os.makedirs(lbl_out, exist_ok=True)
    shutil.copy(src_img, os.path.join(img_out, stem + ".jpg"))
    with open(os.path.join(lbl_out, stem + ".txt"), "w") as f:
        f.write("\n".join(bbox_lines) + ("\n" if bbox_lines else ""))


def prepare(cfg: Config, dedup_threshold: int = 5, drop_dups: bool = False) -> dict:
    adapter = A1Adapter()
    records = adapter.read_raw(cfg.raw_dir)

    # class-map gate from polygon aspect ratios vs yaml names (BSD/BSV)
    objects_by_class: dict[int, list[float]] = {}
    for r in records:
        for cid, coords in r["objects"]:
            bb = polygon_to_bbox(coords)
            if bb:
                _, _, w, h = bb
                objects_by_class.setdefault(cid, []).append(w / h if h else 0.0)
    class_map = verify_class_map(infer_layout_map(objects_by_class), adapter.class_names())

    # keep raw train intact; re-split raw val into val+test, stratified by MAJORITY class
    train_recs = [r for r in records if r["split"] == "train"]
    val_pool = [r for r in records if r["split"] == "val"]
    pool_items = [r["image_path"] for r in val_pool]
    pool_labels = [_majority_class(r["objects"]) for r in val_pool]
    split_map = stratified_split(pool_items, pool_labels, cfg.split_ratios, seed=42)

    # NOTE: raw train is assigned first and is NOT in split_ratios, so it is never re-split.
    assign = {"train": train_recs}
    by_path = {r["image_path"]: r for r in val_pool}
    for name, paths in split_map.items():
        assign[name] = [by_path[p] for p in paths]

    # dedup BEFORE writing so dropped items never reach processed/ (train↔test and train↔val)
    def hashes(recs):
        d = {}
        for r in recs:
            img = cv2.imread(r["image_path"])
            if img is not None:
                d[r["image_path"]] = ahash(img)
        return d
    h_train = hashes(assign["train"])
    dup_tt = find_duplicates(h_train, hashes(assign["test"]), threshold=dedup_threshold)
    dup_tv = find_duplicates(h_train, hashes(assign["val"]), threshold=dedup_threshold)
    if drop_dups:
        drop = {q for q, _, _ in dup_tt} | {q for q, _, _ in dup_tv}
        assign["test"] = [r for r in assign["test"] if r["image_path"] not in drop]
        assign["val"] = [r for r in assign["val"] if r["image_path"] not in drop]

    # write processed
    if os.path.isdir(cfg.processed_dir):
        shutil.rmtree(cfg.processed_dir)
    os.makedirs(cfg.split_dir, exist_ok=True)
    counts = {}
    for split, recs in assign.items():
        stems = []
        for r in recs:
            stem = os.path.splitext(os.path.basename(r["image_path"]))[0]
            lines = []
            for cid, coords in r["objects"]:
                bb = polygon_to_bbox(coords)
                if bb:
                    lines.append(f"{cid} " + " ".join(f"{v:.6f}" for v in bb))
            _write_pair(cfg.processed_dir, split, stem, r["image_path"], lines)
            stems.append(stem)
        counts[split] = len(recs)
        with open(os.path.join(cfg.split_dir, f"{split}.txt"), "w") as f:
            f.write("\n".join(stems) + ("\n" if stems else ""))

    # dataset yaml
    os.makedirs(os.path.dirname(cfg.dataset_yaml) or ".", exist_ok=True)
    with open(cfg.dataset_yaml, "w") as f:
        yaml.safe_dump({
            "path": os.path.abspath(cfg.processed_dir),
            "train": "images/train", "val": "images/val", "test": "images/test",
            "names": {int(k): v for k, v in class_map.items()},
        }, f, sort_keys=False)

    # pHash near-duplicate report, used in the report chapter
    report = os.path.join(cfg.processed_dir, "phash_report.txt")
    with open(report, "w") as f:
        f.write(f"# pHash near-duplicate report (Hamming <= {dedup_threshold})\n")
        f.write(f"train_vs_test: {len(dup_tt)} pairs\n")
        for q, t, d in dup_tt:
            f.write(f"  {os.path.basename(q)} ~ {os.path.basename(t)} (d={d})\n")
        f.write(f"train_vs_val: {len(dup_tv)} pairs\n")
        for q, t, d in dup_tv:
            f.write(f"  {os.path.basename(q)} ~ {os.path.basename(t)} (d={d})\n")

    errs = validate_processed(cfg.processed_dir, cfg.num_classes)
    if errs:
        raise ValueError("prepare produced invalid dataset:\n  " + "\n  ".join(errs))

    return {"counts": counts, "dup_train_test": len(dup_tt),
            "dup_train_val": len(dup_tv), "class_map": class_map,
            "phash_report": report}
