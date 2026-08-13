# Plate-Region Detection (A1, YOLO26n vs YOLOv8n) — Redo-Clean Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `plate_detect` package clean from the reviewed design so it prepares the A1 dataset, trains + reliably compares YOLO26n vs YOLOv8n locally (OS-independent), and exports weights + ONNX + a `PlateDetector` API for the downstream ALPR pipeline.

**Architecture:** A pip-installable package (`src/ml/plate_detect/`) with focused stages — data prep (adapter → poly→bbox → majority-class stratified split → pHash dedup train↔test **and** train↔val → data-contract validate), training (model-registry wrapper over Ultralytics, multi-seed + imgsz ablation), evaluation (multi-seed mean±std + bootstrap CI + params/FLOPs/size + latency model-only vs end-to-end), ONNX export (parity-checked), and a backend-swappable inference API. Everything runs local on any OS; a thin notebook **or** the CLI drives it; device is auto-detected. A synthetic-fixture smoke test exercises the whole pipeline on CPU before any real GPU run.

**Tech Stack:** Python 3.11+, Ultralytics 8.4.37 (YOLO26 + YOLOv8), OpenCV, NumPy, PyYAML, ONNX Runtime, pytest, matplotlib (figures).

**Provenance note (for the executor):** A prior implementation of the unchanged modules exists in git at commit `8f44bbf` (deleted by `8934ba9 "clean up"`). All code needed is inline in this plan; `8f44bbf` is only a cross-check reference. This redo bakes in the design review's fixes — do **not** restore the old code wholesale (its `cli.py` train/eval/export were Colab stubs, its `prepare.py` stratified on the first object and deduped train↔test only).

## Global Constraints

- **Ultralytics pinned `ultralytics==8.4.37`** (first version bundling YOLO26; old `detect-yolov8.ipynb` pinned `8.3.0` which lacks YOLO26). Identical env for both models.
- **Runs local, OS-independent** (Windows/Mac/Linux). Package never hardcodes paths or environment: paths come from `Config`, device from `torch.cuda.is_available()`. No Colab/Drive/runtime-download assumptions in code.
- **Package `plate_detect`, installed `pip install -e src/ml/plate_detect`.** All logic in the package; notebook/CLI stay thin.
- **Two classes, fixed mapping `0: bien_1hang`, `1: bien_2hang`.** A1 `dataset.yaml` names are `['BSD','BSV']` (abbreviations) — BSD→`bien_1hang` (long/1-row), BSV→`bien_2hang` (square/2-row); the class-map gate must verify this before training. Axis-aligned bbox only (no OBB/seg); deskew is a later ALPR stage.
- **Data already local** at `data/raw/kaggle_vn_plate_segment` (4578 images; W 335–4032 / H 255–3024 px; 2 classes; objects: class 0 BSD = 1641 **minority**, class 1 BSV = 3559). No test split on disk → derived by splitting the raw `val`.
- **Reliability: ≥3 training seeds per model (default `[0,1,2]`); report mean ± std and bootstrap 95% CI.** With S=3 this is **descriptive only** — never claim statistical significance / paired tests at n=3.
- **imgsz ablation:** baseline `imgsz=640` for the full multi-seed matrix; plus one ablation run per model at `imgsz=960` (single seed) to quantify the small-object leverage.
- **Fixed hyperparameters for a fair comparison:** `epochs=100, batch=16, patience=20, deterministic=True`; identical augmentation for both models.
- **Success gate:** mAP@0.5 ≥ 0.90 on the A1 test split; always also report mAP@0.5:0.95.
- **Weights (`*.pt`, `*.onnx`) tracked via git-lfs.** Never commit A1 images (license "Unknown"); tests use synthetic fixtures only.
- **Results ledger:** append to `src/ml/experiments.csv` (schema `date,model,dataset,hyperparams,mAP50,mAP50-95,precision,recall,weights`).
- **Report figures** go to `docs/report/figures/`.
- **Branch `feat/plate-detect-a1`.** End every commit message with a trailing `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` line.

---

## File Structure

```
src/ml/plate_detect/
  pyproject.toml                       # T1
  .gitignore .gitattributes            # T1 (git-lfs for weights)
  plate_detect/
    __init__.py                        # T1
    config.py                          # T1  Config dataclass + yaml load/merge
    data/
      __init__.py
      bbox.py                          # T2  polygon_to_bbox
      split.py                         # T3  stratified deterministic split
      dedup.py                         # T4  perceptual-hash near-dup
      validate.py                      # T5  data-contract checks
      adapters.py                      # T6  DatasetAdapter Protocol + A1Adapter
      class_map.py                     # T6  infer/verify class-id ↔ layout (BSD/BSV)
      fixtures.py                      # T7  synthetic mini-dataset generator
      prepare.py                       # T8  orchestrator raw→processed (REVIEW fixes)
    train/
      __init__.py
      registry.py                      # T9  MODEL_REGISTRY
      trainer.py                       # T9  build_train_args + run_train (imgsz)
    inference/
      __init__.py
      postprocess.py                   # T10 nms + decode_v8 + decode_v26
      plate_detector.py                # T11 PlateDetection + PlateDetector (pt|onnx)
    export/
      __init__.py
      to_onnx.py                       # T12 export + parity
    eval/
      __init__.py
      metrics.py                       # T13 bootstrap_ci + latency + model_stats
      evaluate.py                      # T14 run_eval + aggregate + table + figures
    figures.py                         # T14/T17 qualitative/low-light/timestamp-FP + class-map grid
    cli.py                             # T15 argparse subcommands, local, --dry-run
  configs/
    default.yaml                       # T1
    a1_det.yaml                        # written by prepare (T8)
    split/                             # manifests written by prepare (T8)
  tests/
    conftest.py                        # T7
    test_config.py                     # T1
    test_bbox.py                       # T2
    test_split.py                      # T3
    test_dedup.py                      # T4
    test_validate.py                   # T5
    test_adapters.py test_class_map.py # T6
    test_fixtures.py                   # T7
    test_prepare.py                    # T8
    test_registry.py test_trainer.py   # T9
    test_postprocess.py                # T10
    test_plate_detector.py             # T11
    test_to_onnx.py                    # T12
    test_metrics.py                    # T13
    test_evaluate.py                   # T14
    test_cli.py                        # T15
    test_pipeline_smoke.py             # T16 (slow)
  notebooks/
    train-plate-det.ipynb              # T17 (thin local driver)
  weights/                             # git-lfs (produced at runtime, T18)
```

---

### Task 1: Package scaffold, Config, git-lfs

**Files:**
- Create: `src/ml/plate_detect/pyproject.toml`
- Create: `src/ml/plate_detect/.gitignore`
- Create: `src/ml/plate_detect/.gitattributes`
- Create: `src/ml/plate_detect/plate_detect/__init__.py`
- Create: `src/ml/plate_detect/plate_detect/config.py`
- Create: `src/ml/plate_detect/configs/default.yaml`
- Test: `src/ml/plate_detect/tests/test_config.py`

**Interfaces:**
- Produces: `Config` dataclass fields `raw_dir, processed_dir, dataset_yaml, split_dir, imgsz, epochs, batch, patience, seeds, class_names, conf, iou, split_ratios`; classmethod `Config.load(path: str | None = None, **overrides) -> Config`; property `Config.num_classes -> int`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_config.py
from plate_detect.config import Config

def test_defaults():
    c = Config()
    assert c.imgsz == 640 and c.epochs == 100 and c.batch == 16 and c.patience == 20
    assert c.seeds == [0, 1, 2]
    assert c.class_names == {0: "bien_1hang", 1: "bien_2hang"}
    assert c.num_classes == 2
    assert c.split_ratios == {"val": 0.5, "test": 0.5}

def test_load_yaml_then_kwargs_override(tmp_path):
    y = tmp_path / "cfg.yaml"
    y.write_text("epochs: 3\nbatch: 2\n")
    c = Config.load(str(y), batch=8)
    assert c.epochs == 3      # from yaml
    assert c.batch == 8       # kwarg wins over yaml
    assert c.imgsz == 640     # default retained
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect'`.

- [ ] **Step 3: Write the scaffold + implementation**

```toml
# src/ml/plate_detect/pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "plate_detect"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "ultralytics==8.4.37",
    "opencv-python-headless",
    "numpy",
    "pyyaml",
    "onnxruntime",
    "matplotlib",
]

[project.optional-dependencies]
dev = ["pytest"]

[project.scripts]
plate_detect = "plate_detect.cli:main"

[tool.setuptools.packages.find]
include = ["plate_detect*"]

[tool.pytest.ini_options]
markers = ["slow: end-to-end tests that train a tiny model"]
```

```gitignore
# src/ml/plate_detect/.gitignore
*.egg-info/
__pycache__/
*.pyc
.pytest_cache/
runs/
# Ultralytics COCO base weights auto-download into CWD; they are NOT our detector.
# Ignore stray model binaries EXCEPT the ones we publish under weights/ via git-lfs.
*.pt
!weights/*.pt
*.onnx
!weights/*.onnx
```

```gitattributes
# src/ml/plate_detect/.gitattributes
*.pt filter=lfs diff=lfs merge=lfs -text
*.onnx filter=lfs diff=lfs merge=lfs -text
```

```python
# src/ml/plate_detect/plate_detect/__init__.py
__all__ = ["config"]
```

```python
# src/ml/plate_detect/plate_detect/config.py
from __future__ import annotations
from dataclasses import dataclass, field
import yaml


@dataclass
class Config:
    raw_dir: str = "data/raw/kaggle_vn_plate_segment"
    processed_dir: str = "data/processed/a1_det"
    dataset_yaml: str = "src/ml/plate_detect/configs/a1_det.yaml"
    split_dir: str = "src/ml/plate_detect/configs/split"
    imgsz: int = 640
    epochs: int = 100
    batch: int = 16
    patience: int = 20
    seeds: list[int] = field(default_factory=lambda: [0, 1, 2])
    class_names: dict[int, str] = field(
        default_factory=lambda: {0: "bien_1hang", 1: "bien_2hang"}
    )
    conf: float = 0.25
    iou: float = 0.5
    split_ratios: dict[str, float] = field(
        default_factory=lambda: {"val": 0.5, "test": 0.5}
    )

    @property
    def num_classes(self) -> int:
        return len(self.class_names)

    @classmethod
    def load(cls, path: str | None = None, **overrides) -> "Config":
        data: dict = {}
        if path:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)
```

```yaml
# src/ml/plate_detect/configs/default.yaml
imgsz: 640
epochs: 100
batch: 16
patience: 20
seeds: [0, 1, 2]
conf: 0.25
iou: 0.5
```

Also create empty `src/ml/plate_detect/plate_detect/data/__init__.py`, `.../train/__init__.py`, `.../inference/__init__.py`, `.../export/__init__.py`, `.../eval/__init__.py`.

- [ ] **Step 4: Install editable + run test to verify it passes**

Run: `pip install -e src/ml/plate_detect && cd src/ml/plate_detect && python -m pytest tests/test_config.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/pyproject.toml src/ml/plate_detect/.gitignore src/ml/plate_detect/.gitattributes src/ml/plate_detect/plate_detect src/ml/plate_detect/configs/default.yaml src/ml/plate_detect/tests/test_config.py
git commit -m "feat(plate_detect): package scaffold, Config, git-lfs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: polygon → bbox

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/bbox.py`
- Test: `src/ml/plate_detect/tests/test_bbox.py`

**Interfaces:**
- Produces: `polygon_to_bbox(coords: list[float]) -> tuple[float,float,float,float] | None` — takes 8 normalized polygon coords `[x1,y1,...,x4,y4]`, returns YOLO `(xc, yc, w, h)` clamped to `[0,1]`, or `None` for degenerate boxes.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_bbox.py
from plate_detect.data.bbox import polygon_to_bbox

def test_square_polygon_to_center_wh():
    xc, yc, w, h = polygon_to_bbox([0.2, 0.2, 0.6, 0.2, 0.6, 0.8, 0.2, 0.8])
    assert abs(xc - 0.4) < 1e-9 and abs(yc - 0.5) < 1e-9
    assert abs(w - 0.4) < 1e-9 and abs(h - 0.6) < 1e-9

def test_clamps_out_of_range():
    xc, yc, w, h = polygon_to_bbox([-0.1, 0.0, 1.2, 0.0, 1.2, 0.5, -0.1, 0.5])
    assert 0.0 <= xc <= 1.0 and w <= 1.0

def test_degenerate_returns_none():
    assert polygon_to_bbox([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_bbox.py -q`
Expected: FAIL — `ModuleNotFoundError` / `No module named 'plate_detect.data.bbox'`.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/data/bbox.py
from __future__ import annotations


def polygon_to_bbox(coords: list[float]) -> tuple[float, float, float, float] | None:
    xs = [min(1.0, max(0.0, v)) for v in coords[0::2]]
    ys = [min(1.0, max(0.0, v)) for v in coords[1::2]]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None
    return ((x1 + x2) / 2, (y1 + y2) / 2, w, h)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_bbox.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/bbox.py src/ml/plate_detect/tests/test_bbox.py
git commit -m "feat(plate_detect): polygon_to_bbox with clamp + degenerate drop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Stratified deterministic split

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/split.py`
- Test: `src/ml/plate_detect/tests/test_split.py`

**Interfaces:**
- Produces: `stratified_split(items: list[str], labels: list[int], ratios: dict[str,float], seed: int = 42) -> dict[str, list[str]]` — deterministic, per-label stratified; bucket names are the `ratios` keys; buckets disjoint and cover all items; raises `ValueError` if ratios don't sum to 1.0.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_split.py
import pytest
from plate_detect.data.split import stratified_split

def test_deterministic_and_disjoint():
    items = [f"img_{i}" for i in range(20)]
    labels = [i % 2 for i in range(20)]
    a = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    b = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    assert a == b                                  # deterministic
    assert set(a["val"]) | set(a["test"]) == set(items)
    assert set(a["val"]) & set(a["test"]) == set()  # disjoint

def test_stratifies_each_label():
    items = [f"img_{i}" for i in range(20)]
    labels = [i % 2 for i in range(20)]           # 10 of each label
    out = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=1)
    # each label split ~50/50 → 5 of each label per bucket
    for bucket in ("val", "test"):
        got = [int(n.split("_")[1]) % 2 for n in out[bucket]]
        assert got.count(0) == 5 and got.count(1) == 5

def test_bad_ratios_raise():
    with pytest.raises(ValueError):
        stratified_split(["a"], [0], {"val": 0.4, "test": 0.4}, seed=0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_split.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/data/split.py
"""Stratified deterministic splitting of items into named buckets."""
from __future__ import annotations
import random
from collections import defaultdict


def stratified_split(
    items: list[str], labels: list[int], ratios: dict[str, float], seed: int = 42
) -> dict[str, list[str]]:
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {sum(ratios.values())}")
    rng = random.Random(seed)
    by_label: dict[int, list[str]] = defaultdict(list)
    for it, lb in zip(items, labels):
        by_label[lb].append(it)
    names = list(ratios.keys())
    out: dict[str, list[str]] = {n: [] for n in names}
    for lb in sorted(by_label):
        group = sorted(by_label[lb])   # stable pre-shuffle
        rng.shuffle(group)
        n = len(group)
        cuts, acc = [], 0.0
        for name in names[:-1]:
            acc += ratios[name]
            cuts.append(round(acc * n))
        start = 0
        for name, end in zip(names, cuts + [n]):
            out[name].extend(group[start:end])
            start = end
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_split.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/split.py src/ml/plate_detect/tests/test_split.py
git commit -m "feat(plate_detect): deterministic stratified split

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Perceptual-hash dedup

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/dedup.py`
- Test: `src/ml/plate_detect/tests/test_dedup.py`

**Interfaces:**
- Produces: `ahash(image: np.ndarray) -> int` (8×8 average hash); `hamming(a: int, b: int) -> int`; `find_duplicates(train: dict[str,int], test: dict[str,int], threshold: int = 5) -> list[tuple[str,str,int]]` — for each item in the second dict, its nearest train match within `threshold` (query_name, train_name, distance). Generic: called once for train↔test and once for train↔val in T8.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_dedup.py
import numpy as np
from plate_detect.data.dedup import ahash, hamming, find_duplicates

def test_ahash_identical_zero_distance():
    img = (np.random.default_rng(0).random((40, 60, 3)) * 255).astype("uint8")
    assert hamming(ahash(img), ahash(img.copy())) == 0

def test_find_duplicates_matches_near_dupes():
    img = (np.random.default_rng(1).random((40, 60, 3)) * 255).astype("uint8")
    h = ahash(img)
    train = {"t0.jpg": h}
    test = {"q0.jpg": h, "q1.jpg": h ^ 0b111111}   # q1 far (6 bits)
    dups = find_duplicates(train, test, threshold=5)
    names = [d[0] for d in dups]
    assert "q0.jpg" in names and "q1.jpg" not in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_dedup.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/data/dedup.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_dedup.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/dedup.py src/ml/plate_detect/tests/test_dedup.py
git commit -m "feat(plate_detect): perceptual-hash near-dup detection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Data-contract validation

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/validate.py`
- Test: `src/ml/plate_detect/tests/test_validate.py`

**Interfaces:**
- Produces: `validate_processed(processed_dir: str, num_classes: int = 2) -> list[str]` (returns error strings, empty if clean); `assert_valid(processed_dir: str, num_classes: int = 2) -> None` (raises `ValueError` on any error). Checks: every image has a label, no orphan labels, class id in `[0, num_classes)`, bbox coords in `[0,1]`, ≥5 fields per line.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_validate.py
import os
from plate_detect.data.validate import validate_processed, assert_valid
import pytest

def _write(root, split, stem, img=True, label="0 0.5 0.5 0.2 0.2"):
    os.makedirs(os.path.join(root, "images", split), exist_ok=True)
    os.makedirs(os.path.join(root, "labels", split), exist_ok=True)
    if img:
        open(os.path.join(root, "images", split, stem + ".jpg"), "wb").close()
    if label is not None:
        with open(os.path.join(root, "labels", split, stem + ".txt"), "w") as f:
            f.write(label + "\n")

def test_clean_dataset_has_no_errors(tmp_path):
    _write(str(tmp_path), "train", "a")
    assert validate_processed(str(tmp_path)) == []

def test_flags_orphan_and_out_of_range(tmp_path):
    _write(str(tmp_path), "train", "a", img=False)          # orphan label
    _write(str(tmp_path), "val", "b", label="9 0.5 0.5 0.1 0.1")  # bad class
    _write(str(tmp_path), "test", "c", label="0 1.4 0.5 0.1 0.1") # coord > 1
    errs = validate_processed(str(tmp_path))
    assert any("orphan" in e for e in errs)
    assert any("out of range" in e for e in errs)
    with pytest.raises(ValueError):
        assert_valid(str(tmp_path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_validate.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/data/validate.py
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
                    errors.append(f"[{split}] {os.path.basename(lp)}: {len(p)} fields, expected >= 5")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_validate.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/validate.py src/ml/plate_detect/tests/test_validate.py
git commit -m "feat(plate_detect): data-contract validation (fail loud)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: A1 adapter + class-map verify (BSD/BSV gate)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/adapters.py`
- Create: `src/ml/plate_detect/plate_detect/data/class_map.py`
- Test: `src/ml/plate_detect/tests/test_adapters.py`
- Test: `src/ml/plate_detect/tests/test_class_map.py`

**Interfaces:**
- Produces: `DatasetAdapter` Protocol `{class_names() -> dict[int,str]; read_raw(raw_dir) -> list[dict]}`; `A1Adapter` reading `images/<split>` + `labels/<split>` polygon labels → records `[{"split","image_path","objects":[(cls:int,[8 coords])]}]`.
- Produces: `infer_layout_map(objects_by_class: dict[int, list[float]]) -> dict[int,str]` (aspect-ratio → layout; widest = `bien_1hang`); `verify_class_map(inferred: dict[int,str], yaml_names: dict[int,str] | None) -> dict[int,str]` (raises `ValueError` on BSD/BSV mismatch).

- [ ] **Step 1: Write the failing tests**

```python
# src/ml/plate_detect/tests/test_class_map.py
import pytest
from plate_detect.data.class_map import infer_layout_map, verify_class_map

def test_widest_class_is_1row():
    # class 0 mean aspect ~4 (long/1-row), class 1 ~1.3 (square/2-row)
    m = infer_layout_map({0: [4.0, 3.8, 4.2], 1: [1.3, 1.2, 1.4]})
    assert m == {0: "bien_1hang", 1: "bien_2hang"}

def test_verify_accepts_matching_bsd_bsv():
    inferred = {0: "bien_1hang", 1: "bien_2hang"}
    assert verify_class_map(inferred, {0: "BSD", 1: "BSV"}) == inferred

def test_verify_raises_on_conflict():
    inferred = {0: "bien_2hang", 1: "bien_1hang"}   # inverted vs yaml
    with pytest.raises(ValueError):
        verify_class_map(inferred, {0: "BSD", 1: "BSV"})
```

```python
# src/ml/plate_detect/tests/test_adapters.py
from plate_detect.data.adapters import A1Adapter
from plate_detect.data.fixtures import make_raw_fixture  # created in T7

def test_reads_polygon_records(tmp_path):
    make_raw_fixture(str(tmp_path), n_per_split=4, seed=0)
    recs = A1Adapter().read_raw(str(tmp_path))
    assert len(recs) == 8                       # 4 train + 4 val
    r = recs[0]
    assert set(r) == {"split", "image_path", "objects"}
    cls, coords = r["objects"][0]
    assert isinstance(cls, int) and len(coords) == 8
```

> Note: `test_adapters.py` depends on `fixtures.py` (T7). Implement `adapters.py` + `class_map.py` now; run `test_class_map.py` here, and `test_adapters.py` passes after T7. (If executing strictly in order, mark `test_adapters.py` xfail until T7, or run it at the end of T7.)

- [ ] **Step 2: Run class-map test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_class_map.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/data/adapters.py
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
                        for ln in fh.read().splitlines():
                            parts = ln.split()
                            if len(parts) >= 9 and parts[0].lstrip("-").isdigit():
                                objects.append((int(parts[0]), list(map(float, parts[1:9]))))
                records.append({"split": split, "image_path": ip, "objects": objects})
        return records
```

```python
# src/ml/plate_detect/plate_detect/data/class_map.py
from __future__ import annotations
from statistics import median


def infer_layout_map(objects_by_class: dict[int, list[float]]) -> dict[int, str]:
    med = {cid: median(ars) for cid, ars in objects_by_class.items()}
    wide_id = max(med, key=med.get)   # highest aspect ratio == 1-row (long plate)
    return {cid: ("bien_1hang" if cid == wide_id else "bien_2hang") for cid in med}


def verify_class_map(inferred: dict[int, str], yaml_names: dict[int, str] | None) -> dict[int, str]:
    if yaml_names is not None:
        for cid, name in inferred.items():
            yn = str(yaml_names.get(cid, "")).lower()
            is_1 = any(k in yn for k in ("1hang", "dai", "long", "lpd", "bsd"))
            is_2 = any(k in yn for k in ("2hang", "vuong", "square", "lpv", "bsv"))
            if is_1 and name != "bien_1hang":
                raise ValueError(f"class {cid}: yaml '{yn}' vs inferred '{name}'")
            if is_2 and name != "bien_2hang":
                raise ValueError(f"class {cid}: yaml '{yn}' vs inferred '{name}'")
    return inferred
```

- [ ] **Step 4: Run class-map test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_class_map.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/adapters.py src/ml/plate_detect/plate_detect/data/class_map.py src/ml/plate_detect/tests/test_class_map.py src/ml/plate_detect/tests/test_adapters.py
git commit -m "feat(plate_detect): A1 adapter + class-map verify (BSD/BSV gate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Synthetic fixtures + conftest

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/fixtures.py`
- Create: `src/ml/plate_detect/tests/conftest.py`
- Test: `src/ml/plate_detect/tests/test_fixtures.py`

**Interfaces:**
- Produces: `make_raw_fixture(root: str, n_per_split: int = 10, seed: int = 0) -> None` — writes an A1-raw-shaped synthetic dataset (`images/{train,val}`, `labels/{train,val}` with 4-corner polygon labels; class 0 = wide/1-row, class 1 = square/2-row). Fixture `raw_fixture` (conftest) returns the raw root path.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_fixtures.py
import os
from plate_detect.data.fixtures import make_raw_fixture

def test_makes_paired_polygon_dataset(tmp_path):
    make_raw_fixture(str(tmp_path), n_per_split=6, seed=0)
    for split in ("train", "val"):
        imgs = os.listdir(os.path.join(tmp_path, "images", split))
        lbls = os.listdir(os.path.join(tmp_path, "labels", split))
        assert len(imgs) == 6 and len(lbls) == 6
    # a label line has class + 8 polygon coords
    lp = os.path.join(tmp_path, "labels", "train", os.listdir(os.path.join(tmp_path, "labels", "train"))[0])
    parts = open(lp).read().split()
    assert len(parts) == 9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_fixtures.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/data/fixtures.py
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
```

```python
# src/ml/plate_detect/tests/conftest.py
import pytest
from plate_detect.data.fixtures import make_raw_fixture


@pytest.fixture
def raw_fixture(tmp_path):
    root = tmp_path / "raw"
    make_raw_fixture(str(root), n_per_split=10, seed=0)
    return root
```

- [ ] **Step 4: Run tests to verify they pass (fixtures + adapters from T6)**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_fixtures.py tests/test_adapters.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/fixtures.py src/ml/plate_detect/tests/conftest.py src/ml/plate_detect/tests/test_fixtures.py
git commit -m "feat(plate_detect): synthetic raw fixtures + conftest

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Prepare orchestrator (REVIEW fixes: majority-class stratify, train↔val dedup, pHash report)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/prepare.py`
- Test: `src/ml/plate_detect/tests/test_prepare.py`

**Interfaces:**
- Consumes: `A1Adapter`, `polygon_to_bbox`, `infer_layout_map`+`verify_class_map`, `stratified_split`, `ahash`+`find_duplicates`, `validate_processed`.
- Produces: `prepare(cfg: Config, dedup_threshold: int = 5, drop_dups: bool = False) -> dict` returning `{"counts": {split:int}, "dup_train_test": int, "dup_train_val": int, "class_map": dict, "phash_report": str}`. Writes `processed_dir/images|labels/{train,val,test}`, `cfg.dataset_yaml`, `cfg.split_dir/{train,val,test}.txt`, and a pHash report at `processed_dir/phash_report.txt`. **Stratifies the val→val+test split by each image's majority class**; **dedups train↔test AND train↔val**.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_prepare.py
import os
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.prepare import prepare

def _cfg(tmp_path):
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=10, seed=0)
    return Config(
        raw_dir=str(raw), processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"), split_dir=str(tmp_path / "split"),
    )

def test_prepare_produces_three_splits_and_yaml(tmp_path):
    cfg = _cfg(tmp_path)
    out = prepare(cfg)
    # raw train kept (10); raw val (10) → val+test ~5/5
    assert out["counts"]["train"] == 10
    assert out["counts"]["val"] + out["counts"]["test"] == 10
    assert os.path.exists(cfg.dataset_yaml)
    for split in ("train", "val", "test"):
        assert os.path.exists(os.path.join(cfg.split_dir, f"{split}.txt"))
    # labels are YOLO bbox now (5 fields), not polygons (9)
    lbl = os.path.join(cfg.processed_dir, "labels", "train")
    first = os.path.join(lbl, sorted(os.listdir(lbl))[0])
    assert len(open(first).read().split()) == 5

def test_prepare_reports_both_dedup_directions_and_writes_report(tmp_path):
    cfg = _cfg(tmp_path)
    out = prepare(cfg)
    assert "dup_train_test" in out and "dup_train_val" in out
    assert os.path.exists(out["phash_report"])
    body = open(out["phash_report"]).read()
    assert "train_vs_test" in body and "train_vs_val" in body

def test_prepare_stratifies_by_majority_class(tmp_path, monkeypatch):
    # capture the labels passed to stratified_split → must be per-image majority class
    import plate_detect.data.prepare as P
    seen = {}
    real = P.stratified_split
    def spy(items, labels, ratios, seed=42):
        seen["labels"] = list(labels)
        return real(items, labels, ratios, seed)
    monkeypatch.setattr(P, "stratified_split", spy)
    prepare(_cfg(tmp_path))
    # fixture alternates class per image → labels are 0/1 (not all 0)
    assert set(seen["labels"]) == {0, 1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_prepare.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/data/prepare.py
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

    # pHash report → report chapter
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_prepare.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/prepare.py src/ml/plate_detect/tests/test_prepare.py
git commit -m "feat(plate_detect): prepare orchestrator with majority-class stratify + train-val/test pHash dedup + report

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Model registry + trainer (imgsz-aware run naming)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/train/registry.py`
- Create: `src/ml/plate_detect/plate_detect/train/trainer.py`
- Test: `src/ml/plate_detect/tests/test_registry.py`
- Test: `src/ml/plate_detect/tests/test_trainer.py`

**Interfaces:**
- Produces: `MODEL_REGISTRY: dict[str,str]` (`{"yolov8n":"yolov8n.pt","yolo26n":"yolo26n.pt"}`); `resolve(key: str) -> str` (raises `KeyError` on unknown).
- Produces: `run_name(model_key: str, seed: int, imgsz: int) -> str` = `"{model_key}_s{seed}_{imgsz}"`; `build_train_args(cfg, data_yaml, seed, project, name, imgsz) -> dict`; `run_train(model_key, cfg, data_yaml, seed, project, imgsz=None) -> str` (returns Ultralytics `save_dir`). `imgsz=None` uses `cfg.imgsz`.

- [ ] **Step 1: Write the failing tests**

```python
# src/ml/plate_detect/tests/test_registry.py
import pytest
from plate_detect.train.registry import MODEL_REGISTRY, resolve

def test_known_models():
    assert set(MODEL_REGISTRY) == {"yolov8n", "yolo26n"}
    assert resolve("yolo26n") == "yolo26n.pt"

def test_unknown_raises():
    with pytest.raises(KeyError):
        resolve("nope")
```

```python
# src/ml/plate_detect/tests/test_trainer.py
from plate_detect.config import Config
from plate_detect.train.trainer import run_name, build_train_args

def test_run_name_includes_seed_and_imgsz():
    assert run_name("yolo26n", 2, 960) == "yolo26n_s2_960"

def test_build_train_args_fixed_for_fair_comparison():
    cfg = Config()
    a = build_train_args(cfg, "a1_det.yaml", seed=1, project="runs", name="r", imgsz=640)
    assert a["seed"] == 1 and a["deterministic"] is True
    assert a["imgsz"] == 640 and a["epochs"] == 100 and a["batch"] == 16
    assert a["data"] == "a1_det.yaml" and a["name"] == "r"

def test_build_train_args_imgsz_override():
    a = build_train_args(Config(), "a1.yaml", seed=0, project="p", name="n", imgsz=960)
    assert a["imgsz"] == 960
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_registry.py tests/test_trainer.py -q`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/train/registry.py
from __future__ import annotations

MODEL_REGISTRY: dict[str, str] = {
    "yolov8n": "yolov8n.pt",
    "yolo26n": "yolo26n.pt",
}


def resolve(key: str) -> str:
    if key not in MODEL_REGISTRY:
        raise KeyError(f"unknown model '{key}'; valid: {sorted(MODEL_REGISTRY)}")
    return MODEL_REGISTRY[key]
```

```python
# src/ml/plate_detect/plate_detect/train/trainer.py
from __future__ import annotations
from ..config import Config
from .registry import resolve


def run_name(model_key: str, seed: int, imgsz: int) -> str:
    return f"{model_key}_s{seed}_{imgsz}"


def build_train_args(cfg: Config, data_yaml: str, seed: int,
                     project: str, name: str, imgsz: int) -> dict:
    """Ultralytics train() kwargs — fixed across both models for a fair comparison;
    A1-tuned augmentation (mild brightness for ~8% dark images, mild skew for gate camera)."""
    return {
        "data": data_yaml,
        "imgsz": imgsz,
        "epochs": cfg.epochs,
        "batch": cfg.batch,
        "patience": cfg.patience,
        "seed": seed,
        "deterministic": True,
        "hsv_v": 0.5,
        "hsv_s": 0.7,
        "degrees": 5.0,
        "perspective": 0.0005,
        "close_mosaic": 10,
        "project": project,
        "name": name,
        "exist_ok": True,
        "verbose": False,
    }


def run_train(model_key: str, cfg: Config, data_yaml: str, seed: int,
              project: str, imgsz: int | None = None) -> str:
    from ultralytics import YOLO
    imgsz = cfg.imgsz if imgsz is None else imgsz
    name = run_name(model_key, seed, imgsz)
    model = YOLO(resolve(model_key))
    results = model.train(**build_train_args(cfg, data_yaml, seed, project, name, imgsz))
    return str(results.save_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_registry.py tests/test_trainer.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/train src/ml/plate_detect/tests/test_registry.py src/ml/plate_detect/tests/test_trainer.py
git commit -m "feat(plate_detect): model registry + imgsz-aware trainer wrapper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Family-aware postprocess (v8 NMS vs v26 NMS-free)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/inference/postprocess.py`
- Test: `src/ml/plate_detect/tests/test_postprocess.py`

**Interfaces:**
- Produces: `nms(boxes, scores, iou_thr) -> list[int]`; `decode_v26(raw, conf) -> (boxes_xyxy, scores, classes)` for `(N,6)` NMS-free output; `decode_v8(raw, conf, iou, nc) -> (boxes_xyxy, scores, classes)` for `(4+nc, M)` / `(M, 4+nc)` output with per-class NMS.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_postprocess.py
import numpy as np
from plate_detect.inference.postprocess import nms, decode_v26, decode_v8

def test_nms_suppresses_overlap():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], float)
    scores = np.array([0.9, 0.8, 0.7])
    keep = nms(boxes, scores, iou_thr=0.5)
    assert 0 in keep and 2 in keep and 1 not in keep

def test_decode_v26_filters_by_conf():
    raw = np.array([[0, 0, 10, 10, 0.9, 0], [0, 0, 5, 5, 0.1, 1]], float)  # (N,6)
    boxes, scores, classes = decode_v26(raw, conf=0.5)
    assert len(scores) == 1 and classes[0] == 0

def test_decode_v8_transposes_and_nms():
    # (4+nc, M) with nc=2, M=2; two overlapping high-conf boxes same class → 1 kept
    raw = np.array([
        [5, 5],        # xc
        [5, 5],        # yc
        [10, 10],      # w
        [10, 10],      # h
        [0.9, 0.85],   # class0 score
        [0.0, 0.0],    # class1 score
    ], float)
    boxes, scores, classes = decode_v8(raw, conf=0.5, iou=0.5, nc=2)
    assert len(scores) == 1 and classes[0] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_postprocess.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/inference/postprocess.py
from __future__ import annotations
import numpy as np


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    xx1 = np.maximum(box[0], boxes[:, 0]); yy1 = np.maximum(box[1], boxes[:, 1])
    xx2 = np.minimum(box[2], boxes[:, 2]); yy2 = np.minimum(box[3], boxes[:, 3])
    w = np.clip(xx2 - xx1, 0, None); h = np.clip(yy2 - yy1, 0, None)
    inter = w * h
    area = (box[2] - box[0]) * (box[3] - box[1])
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / (area + areas - inter + 1e-9)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    idx = scores.argsort()[::-1]
    keep = []
    while len(idx):
        i = idx[0]; keep.append(int(i))
        if len(idx) == 1:
            break
        ious = _iou(boxes[i], boxes[idx[1:]])
        idx = idx[1:][ious <= iou_thr]
    return keep


def decode_v26(raw: np.ndarray, conf: float):
    raw = np.asarray(raw, float)
    m = raw[:, 4] >= conf
    r = raw[m]
    return r[:, :4], r[:, 4], r[:, 5].astype(int)


def decode_v8(raw: np.ndarray, conf: float, iou: float, nc: int):
    raw = np.asarray(raw, float)
    if raw.shape[0] == 4 + nc:          # (4+nc, M) → (M, 4+nc)
        raw = raw.T
    xywh, cls = raw[:, :4], raw[:, 4:4 + nc]
    scores = cls.max(axis=1); classes = cls.argmax(axis=1)
    m = scores >= conf
    xywh, scores, classes = xywh[m], scores[m], classes[m]
    xyxy = np.stack([xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2,
                     xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2], axis=1)
    keep_all = []
    for c in np.unique(classes):
        cm = np.where(classes == c)[0]
        k = nms(xyxy[cm], scores[cm], iou)
        keep_all.extend(cm[k].tolist())
    keep_all = np.array(keep_all, int)
    return xyxy[keep_all], scores[keep_all], classes[keep_all]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_postprocess.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/inference/postprocess.py src/ml/plate_detect/tests/test_postprocess.py
git commit -m "feat(plate_detect): family-aware postprocess (v8 NMS, v26 NMS-free)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: PlateDetector API (pt|onnx backends)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/inference/plate_detector.py`
- Test: `src/ml/plate_detect/tests/test_plate_detector.py`

**Interfaces:**
- Produces: `@dataclass PlateDetection{bbox_xyxy: tuple[int,int,int,int]; cls_id: int; cls_name: str; conf: float; crop: np.ndarray}`; `build_detections(boxes, classes, confs, image, names, pad=4) -> list[PlateDetection]` (clamps to image, pads crop, drops empty, sorts by conf desc); `PlateDetector(weights, backend="pt"|"onnx", names=None, conf=0.25, iou=0.5)` with `.detect(image) -> list[PlateDetection]`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_plate_detector.py
import numpy as np
from plate_detect.inference.plate_detector import PlateDetection, build_detections

def test_build_detections_clamps_pads_sorts():
    image = np.zeros((100, 100, 3), np.uint8)
    boxes = np.array([[10, 10, 30, 30], [-5, -5, 20, 20]], float)
    classes = np.array([0, 1])
    confs = np.array([0.6, 0.9])
    names = {0: "bien_1hang", 1: "bien_2hang"}
    dets = build_detections(boxes, classes, confs, image, names, pad=4)
    assert [d.conf for d in dets] == [0.9, 0.6]          # sorted desc
    assert dets[0].bbox_xyxy[0] >= 0 and dets[0].bbox_xyxy[1] >= 0  # clamped
    assert dets[0].cls_name == "bien_2hang"
    assert dets[0].crop.size > 0

def test_empty_boxes_give_empty_list():
    image = np.zeros((10, 10, 3), np.uint8)
    assert build_detections(np.empty((0, 4)), np.empty((0,)), np.empty((0,)), image, {}) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_plate_detector.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/inference/plate_detector.py
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .postprocess import decode_v8, decode_v26


@dataclass
class PlateDetection:
    bbox_xyxy: tuple[int, int, int, int]
    cls_id: int
    cls_name: str
    conf: float
    crop: np.ndarray


def build_detections(boxes, classes, confs, image, names, pad: int = 4) -> list[PlateDetection]:
    H, W = image.shape[:2]
    order = np.argsort(np.asarray(confs))[::-1] if len(confs) else []
    out = []
    for i in order:
        x1, y1, x2, y2 = boxes[i]
        x1 = int(max(0, min(W, x1 - pad))); y1 = int(max(0, min(H, y1 - pad)))
        x2 = int(max(0, min(W, x2 + pad))); y2 = int(max(0, min(H, y2 + pad)))
        if x2 <= x1 or y2 <= y1:
            continue
        cid = int(classes[i])
        out.append(PlateDetection((x1, y1, x2, y2), cid,
                                  names.get(cid, str(cid)), float(confs[i]),
                                  image[y1:y2, x1:x2].copy()))
    return out


class PlateDetector:
    def __init__(self, weights: str, backend: str = "pt",
                 names: dict | None = None, conf: float = 0.25, iou: float = 0.5):
        self.weights = weights
        self.backend = backend
        self.names = names or {0: "bien_1hang", 1: "bien_2hang"}
        self.conf = conf
        self.iou = iou
        self._model = None
        self._session = None

    def detect(self, image: np.ndarray) -> list[PlateDetection]:
        if self.backend == "pt":
            return self._detect_pt(image)
        if self.backend == "onnx":
            return self._detect_onnx(image)
        raise ValueError(f"unknown backend '{self.backend}'")

    def _detect_pt(self, image: np.ndarray) -> list[PlateDetection]:
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(self.weights)
        r = self._model.predict(image, conf=self.conf, iou=self.iou, verbose=False)[0]
        b = r.boxes
        if b is None or len(b) == 0:
            return []
        boxes = b.xyxy.cpu().numpy()
        classes = b.cls.cpu().numpy().astype(int)
        confs = b.conf.cpu().numpy()
        return build_detections(boxes, classes, confs, image, self.names)

    def _detect_onnx(self, image: np.ndarray) -> list[PlateDetection]:
        import cv2
        import onnxruntime as ort
        if self._session is None:
            self._session = ort.InferenceSession(
                self.weights, providers=["CPUExecutionProvider"])
        inp_name = self._session.get_inputs()[0].name
        h, w = self._session.get_inputs()[0].shape[2:]
        h = h if isinstance(h, int) else 640
        w = w if isinstance(w, int) else 640
        blob = cv2.resize(image, (w, h))[:, :, ::-1].transpose(2, 0, 1)[None]
        blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
        raw = self._session.run(None, {inp_name: blob})[0][0]
        nc = len(self.names)
        if raw.ndim == 2 and raw.shape[1] == 6:
            boxes, scores, classes = decode_v26(raw, self.conf)
        else:
            boxes, scores, classes = decode_v8(raw, self.conf, self.iou, nc)
        sx, sy = image.shape[1] / w, image.shape[0] / h
        if len(boxes):
            boxes = boxes * np.array([sx, sy, sx, sy])
        return build_detections(boxes, classes, scores, image, self.names)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_plate_detector.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/inference/plate_detector.py src/ml/plate_detect/tests/test_plate_detector.py
git commit -m "feat(plate_detect): PlateDetector API (pt|onnx backends)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: ONNX export + parity check

**Files:**
- Create: `src/ml/plate_detect/plate_detect/export/to_onnx.py`
- Test: `src/ml/plate_detect/tests/test_to_onnx.py`

**Interfaces:**
- Produces: `detection_delta(a: list[PlateDetection], b: list[PlateDetection]) -> float` (count diff + mean center distance/1000); `parity_ok(a, b, tol=0.02) -> bool`; `export(weights_pt: str, out_onnx: str, imgsz: int = 640) -> str` (Ultralytics ONNX export, opset 12; returns out path).

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_to_onnx.py
import numpy as np
from plate_detect.inference.plate_detector import PlateDetection
from plate_detect.export.to_onnx import detection_delta, parity_ok

def _det(x1, y1, x2, y2, conf, cid=0):
    return PlateDetection((x1, y1, x2, y2), cid, "bien_1hang", conf, np.zeros((2, 2, 3), np.uint8))

def test_identical_detections_parity_ok():
    a = [_det(0, 0, 10, 10, 0.9)]
    b = [_det(0, 0, 10, 10, 0.9)]
    assert detection_delta(a, b) == 0.0 and parity_ok(a, b)

def test_count_mismatch_breaks_parity():
    a = [_det(0, 0, 10, 10, 0.9)]
    assert not parity_ok(a, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_to_onnx.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/export/to_onnx.py
from __future__ import annotations
import numpy as np


def _center(d):
    x1, y1, x2, y2 = d.bbox_xyxy
    return np.array([(x1 + x2) / 2, (y1 + y2) / 2], float)


def detection_delta(a, b) -> float:
    delta = float(abs(len(a) - len(b)))
    n = min(len(a), len(b))
    if n:
        a_s = sorted(a, key=lambda d: d.conf, reverse=True)
        b_s = sorted(b, key=lambda d: d.conf, reverse=True)
        dists = [np.linalg.norm(_center(a_s[i]) - _center(b_s[i])) for i in range(n)]
        delta += float(np.mean(dists)) / 1000.0
    return delta


def parity_ok(a, b, tol: float = 0.02) -> bool:
    return detection_delta(a, b) <= tol


def export(weights_pt: str, out_onnx: str, imgsz: int = 640) -> str:
    from ultralytics import YOLO
    import shutil
    model = YOLO(weights_pt)
    produced = model.export(format="onnx", imgsz=imgsz, opset=12)
    if produced is None:
        raise RuntimeError("Ultralytics export returned None — check weights path / format")
    if str(produced) != out_onnx:
        shutil.copy(str(produced), out_onnx)
    return out_onnx
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_to_onnx.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/export/to_onnx.py src/ml/plate_detect/tests/test_to_onnx.py
git commit -m "feat(plate_detect): ONNX export + detection parity check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Metrics — bootstrap CI, latency, model stats

**Files:**
- Create: `src/ml/plate_detect/plate_detect/eval/metrics.py`
- Test: `src/ml/plate_detect/tests/test_metrics.py`

**Interfaces:**
- Produces: `bootstrap_ci(values: list[float], n_boot=1000, seed=0, alpha=0.05) -> (mean, lo, hi)`; `measure_latency(fn, inp, warmup=5, runs=20) -> float` (median seconds); `model_stats(weights_pt: str) -> {"params_M","flops_G","size_MB"}` (hardware-independent primaries per design §9.6). Latency model-only vs end-to-end is produced by calling `measure_latency` on two callables built in `evaluate`/`cli` (raw-forward vs `PlateDetector.detect`).

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_metrics.py
from plate_detect.eval.metrics import bootstrap_ci, measure_latency, model_stats

def test_bootstrap_ci_orders_and_brackets_mean():
    mean, lo, hi = bootstrap_ci([0.90, 0.91, 0.89, 0.92, 0.88], n_boot=500, seed=0)
    assert lo <= mean <= hi
    assert abs(mean - 0.90) < 0.01

def test_measure_latency_returns_positive_median():
    calls = {"n": 0}
    def fn(_):
        calls["n"] += 1
    t = measure_latency(fn, None, warmup=2, runs=5)
    assert t >= 0.0 and calls["n"] == 7        # warmup + runs

def test_model_stats_reads_size_and_calls_yolo(tmp_path, monkeypatch):
    w = tmp_path / "m.pt"; w.write_bytes(b"0" * 2_000_000)   # ~2 MB
    class FakeModel:
        def info(self, verbose=False):
            return (100, 3_000_000, 0, 8.1)                  # layers, params, grads, GFLOPs
    monkeypatch.setattr("plate_detect.eval.metrics._load_yolo", lambda p: FakeModel())
    s = model_stats(str(w))
    assert round(s["params_M"], 1) == 3.0
    assert round(s["flops_G"], 1) == 8.1
    assert round(s["size_MB"], 1) == 2.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_metrics.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/eval/metrics.py
from __future__ import annotations
import os
import time
import numpy as np


def bootstrap_ci(values, n_boot: int = 1000, seed: int = 0, alpha: float = 0.05):
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(arr)
    boot = np.array([arr[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(arr.mean()), float(lo), float(hi)


def measure_latency(fn, inp, warmup: int = 5, runs: int = 20) -> float:
    for _ in range(warmup):
        fn(inp)
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(inp)
        times.append(time.perf_counter() - t0)
    return float(np.median(times))


def _load_yolo(weights_pt: str):
    from ultralytics import YOLO
    return YOLO(weights_pt)


def model_stats(weights_pt: str) -> dict:
    """Hardware-independent primaries: params (M), FLOPs (G), file size (MB)."""
    m = _load_yolo(weights_pt)
    info = m.info(verbose=False)      # (layers, params, gradients, gflops)
    params = float(info[1]) if info else 0.0
    flops = float(info[3]) if info and len(info) > 3 else 0.0
    return {
        "params_M": params / 1e6,
        "flops_G": flops,
        "size_MB": os.path.getsize(weights_pt) / 1e6,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_metrics.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/eval/metrics.py src/ml/plate_detect/tests/test_metrics.py
git commit -m "feat(plate_detect): metrics — bootstrap CI, latency, model stats

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Evaluate — run_eval, seed aggregation, experiments ledger, comparison table

**Files:**
- Create: `src/ml/plate_detect/plate_detect/eval/evaluate.py`
- Test: `src/ml/plate_detect/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `bootstrap_ci` (T13); Ultralytics `YOLO.val`.
- Produces:
  - `run_eval(weights_pt: str, data_yaml: str, imgsz: int, conf: float, iou: float) -> dict` with keys `map50, map5095, precision, recall, per_class_ap` (list). Runs `YOLO(weights).val(split="test", ...)`.
  - `aggregate_seeds(runs: list[dict]) -> dict[str, tuple[float,float]]` → per-metric `(mean, population_std)` (single seed → std 0.0).
  - `append_experiment(csv_path, model, dataset, hyperparams, m: dict, weights: str) -> None` (header schema `date,model,dataset,hyperparams,mAP50,mAP50-95,precision,recall,weights`; metric keys `map50,map5095,precision,recall`, 4-dp).
  - `comparison_table(rows: list[dict]) -> str` (markdown). Each row dict: `model, imgsz, map50_mean, map50_std, map5095_mean, map5095_ci(tuple), precision, recall, params_M, flops_G, size_MB, lat_model_ms, lat_e2e_ms, fps`.

> **Bootstrap scope (honest):** the CI is computed over the **per-seed** test mAP@0.5:0.95 values (S=3) — i.e. seed-level, matching the review's "descriptive only at n=3" (G2). True per-image resampling (design §9.2, B≈1000 over test images) needs saved per-image TP/FP and is an **optional stretch** — leave a `# TODO(optional): per-image bootstrap from saved preds` marker in `cmd_eval`, do not block on it. Report the CI as descriptive, never as a significance test.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_evaluate.py
import os
from plate_detect.eval.evaluate import aggregate_seeds, append_experiment, comparison_table

def test_aggregate_seeds_mean_and_std():
    runs = [{"map50": 0.90, "map5095": 0.60}, {"map50": 0.92, "map5095": 0.62}]
    agg = aggregate_seeds(runs)
    assert abs(agg["map50"][0] - 0.91) < 1e-9
    assert agg["map50"][1] > 0.0

def test_append_experiment_writes_header_then_row(tmp_path):
    csv = tmp_path / "experiments.csv"
    m = {"map50": 0.9123, "map5095": 0.6001, "precision": 0.9, "recall": 0.88}
    append_experiment(str(csv), "yolo26n", "A1", "imgsz=640", m, "weights/yolo26n.pt")
    lines = open(csv).read().splitlines()
    assert lines[0].startswith("date,model,dataset,hyperparams")
    assert "yolo26n" in lines[1] and "0.9123" in lines[1]

def test_comparison_table_has_headers_and_ci():
    rows = [{
        "model": "yolo26n", "imgsz": 640, "map50_mean": 0.98, "map50_std": 0.004,
        "map5095_mean": 0.71, "map5095_ci": (0.69, 0.73), "precision": 0.95,
        "recall": 0.93, "params_M": 3.0, "flops_G": 8.1, "size_MB": 6.2,
        "lat_model_ms": 12.0, "lat_e2e_ms": 13.0, "fps": 76.9,
    }]
    md = comparison_table(rows)
    assert "| model | imgsz |" in md
    assert "yolo26n" in md and "0.69" in md and "0.73" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_evaluate.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/eval/evaluate.py
from __future__ import annotations
import os
import csv
import datetime
import statistics

_HEADER = ["date", "model", "dataset", "hyperparams",
           "mAP50", "mAP50-95", "precision", "recall", "weights"]


def run_eval(weights_pt: str, data_yaml: str, imgsz: int,
             conf: float, iou: float) -> dict:
    from ultralytics import YOLO
    res = YOLO(weights_pt).val(data=data_yaml, split="test", imgsz=imgsz,
                               conf=conf, iou=iou, verbose=False)
    box = res.box
    return {
        "map50": float(box.map50),
        "map5095": float(box.map),
        "precision": float(box.mp),
        "recall": float(box.mr),
        "per_class_ap": [float(x) for x in getattr(box, "maps", [])],
    }


def aggregate_seeds(runs: list[dict]) -> dict[str, tuple[float, float]]:
    if not runs:
        return {}
    out = {}
    for k in runs[0]:
        if isinstance(runs[0][k], (int, float)):
            vals = [r[k] for r in runs]
            out[k] = (statistics.mean(vals), statistics.pstdev(vals))
    return out


def append_experiment(csv_path: str, model: str, dataset: str,
                      hyperparams: str, m: dict, weights: str) -> None:
    exists = os.path.exists(csv_path)
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(_HEADER)
        w.writerow([
            datetime.date.today().isoformat(), model, dataset, hyperparams,
            f"{m['map50']:.4f}", f"{m['map5095']:.4f}",
            f"{m['precision']:.4f}", f"{m['recall']:.4f}", weights,
        ])


def comparison_table(rows: list[dict]) -> str:
    head = ("| model | imgsz | mAP@0.5 (mean±std) | mAP@0.5:0.95 [95% CI] | P | R "
            "| params(M) | FLOPs(G) | size(MB) | lat_model(ms) | lat_e2e(ms) | FPS |")
    sep = "|" + "---|" * 12
    lines = [head, sep]
    for r in rows:
        lo, hi = r["map5095_ci"]
        lines.append(
            f"| {r['model']} | {r['imgsz']} "
            f"| {r['map50_mean']:.4f}±{r['map50_std']:.4f} "
            f"| {r['map5095_mean']:.4f} [{lo:.2f}, {hi:.2f}] "
            f"| {r['precision']:.3f} | {r['recall']:.3f} "
            f"| {r['params_M']:.2f} | {r['flops_G']:.2f} | {r['size_MB']:.2f} "
            f"| {r['lat_model_ms']:.1f} | {r['lat_e2e_ms']:.1f} | {r['fps']:.1f} |"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_evaluate.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/eval/evaluate.py src/ml/plate_detect/tests/test_evaluate.py
git commit -m "feat(plate_detect): evaluate — run_eval, seed aggregation, ledger, comparison table

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: CLI — local prepare/train/eval/export/check (+ imgsz ablation, --dry-run)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/cli.py`
- Test: `src/ml/plate_detect/tests/test_cli.py`

**Interfaces:**
- Consumes: `prepare` (T8), `validate_processed` (T5), `run_train` (T9), `run_eval`+`aggregate_seeds`+`append_experiment`+`comparison_table` (T14), `bootstrap_ci`+`model_stats`+`measure_latency` (T13), `export`+`parity_ok` (T12), `PlateDetector` (T11).
- Produces: `main(argv: list[str] | None = None) -> int` with subcommands `prepare|train|eval|export|check`. Helper functions (testable seams): `cmd_train(cfg, project, models, imgsz, seeds) -> list[str]`; `cmd_eval(cfg, project, models, imgszs, csv_path, table_path, weights_dir, sample_image) -> str`; `cmd_export(cfg, weights_pt, out_onnx, imgsz) -> str`. Global flags follow the subcommand.
- **imgsz ablation:** `plate_detect train` runs the full seed matrix at `cfg.imgsz` (640); `plate_detect train --imgsz 960 --seeds 0` adds the single-seed ablation. `plate_detect eval --imgsz 640,960` aggregates both into one comparison table.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_cli.py
import os
import plate_detect.cli as C
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture

def _common(tmp_path):
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=8, seed=0)
    return ["--raw-dir", str(raw), "--processed-dir", str(tmp_path / "proc"),
            "--dataset-yaml", str(tmp_path / "a1.yaml"), "--split-dir", str(tmp_path / "split")]

def test_dry_run_no_compute(capsys, tmp_path):
    rc = C.main(["prepare", "--dry-run"] + _common(tmp_path))
    assert rc == 0
    assert "[dry-run]" in capsys.readouterr().out
    assert not os.path.exists(tmp_path / "proc")     # nothing prepared

def test_prepare_then_check(tmp_path):
    common = _common(tmp_path)
    assert C.main(["prepare"] + common) == 0
    assert C.main(["check"] + common) == 0            # data-contract OK

def test_train_dispatches_per_model_and_seed(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(C, "run_train",
                        lambda mk, cfg, y, seed, project, imgsz=None: calls.append((mk, seed, imgsz)) or f"{project}/{mk}_s{seed}_{imgsz}")
    cfg = Config(dataset_yaml=str(tmp_path / "a1.yaml"))
    dirs = C.cmd_train(cfg, project=str(tmp_path / "runs"),
                       models=["yolov8n", "yolo26n"], imgsz=640, seeds=[0, 1])
    assert len(calls) == 4 and ("yolo26n", 1, 640) in calls
    assert len(dirs) == 4

def test_export_calls_export_and_parity(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "export", lambda pt, out, imgsz=640: out)
    cfg = Config()
    out = C.cmd_export(cfg, weights_pt=str(tmp_path / "best.pt"),
                       out_onnx=str(tmp_path / "m.onnx"), imgsz=640)
    assert out.endswith("m.onnx")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_cli.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/ml/plate_detect/plate_detect/cli.py
from __future__ import annotations
import argparse
import glob
import os
import sys
import cv2
from .config import Config
from .data.prepare import prepare
from .data.validate import validate_processed
from .train.registry import MODEL_REGISTRY
from .train.trainer import run_train, run_name
from .eval.evaluate import run_eval, aggregate_seeds, append_experiment, comparison_table
from .eval.metrics import bootstrap_ci, model_stats, measure_latency
from .export.to_onnx import export, parity_ok
from .inference.plate_detector import PlateDetector


def _cfg_from_args(a) -> Config:
    over = {}
    for k in ("raw_dir", "processed_dir", "dataset_yaml", "split_dir", "imgsz"):
        v = getattr(a, k, None)
        if v is not None:
            over[k] = v
    return Config.load(getattr(a, "config", None), **over)


def cmd_train(cfg: Config, project: str, models: list[str], imgsz: int,
              seeds: list[int]) -> list[str]:
    dirs = []
    for mk in models:
        for seed in seeds:
            dirs.append(run_train(mk, cfg, cfg.dataset_yaml, seed, project, imgsz=imgsz))
    return dirs


def _best_paths(project: str, model: str, imgsz: int, seeds: list[int]) -> list[str]:
    out = []
    for seed in seeds:
        p = os.path.join(project, run_name(model, seed, imgsz), "weights", "best.pt")
        if os.path.exists(p):
            out.append(p)
    return out


def _latency_onnx(onnx_path: str, image, names: dict, conf: float, iou: float):
    """Model-only (network forward) vs end-to-end (forward + decode/NMS) on ONNX."""
    import numpy as np
    import onnxruntime as ort
    det = PlateDetector(onnx_path, backend="onnx", names=names, conf=conf, iou=iou)
    det.detect(image)                       # warm the session
    sess = det._session
    iname = sess.get_inputs()[0].name
    h, w = sess.get_inputs()[0].shape[2:]
    h = h if isinstance(h, int) else 640
    w = w if isinstance(w, int) else 640
    blob = cv2.resize(image, (w, h))[:, :, ::-1].transpose(2, 0, 1)[None]
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    lat_model = measure_latency(lambda b: sess.run(None, {iname: b}), blob)
    lat_e2e = measure_latency(det.detect, image)
    fps = 1.0 / lat_e2e if lat_e2e > 0 else 0.0
    return lat_model * 1000.0, lat_e2e * 1000.0, fps


def cmd_eval(cfg: Config, project: str, models: list[str], imgszs: list[int],
             csv_path: str, table_path: str, weights_dir: str, sample_image: str) -> str:
    img = cv2.imread(sample_image) if sample_image and os.path.exists(sample_image) else None
    rows = []
    for mk in models:
        for imgsz in imgszs:
            bests = _best_paths(project, mk, imgsz, cfg.seeds)
            if not bests:
                continue
            per_seed = [run_eval(b, cfg.dataset_yaml, imgsz, cfg.conf, cfg.iou) for b in bests]
            agg = aggregate_seeds(per_seed)
            _, lo, hi = bootstrap_ci([r["map5095"] for r in per_seed])
            best_pt = bests[0]
            stats = model_stats(best_pt)
            onnx_path = os.path.join(weights_dir, f"{mk}_a1_{imgsz}.onnx")
            if img is not None and os.path.exists(onnx_path):
                lat_model, lat_e2e, fps = _latency_onnx(onnx_path, img, cfg.class_names, cfg.conf, cfg.iou)
            else:
                lat_model = lat_e2e = fps = 0.0
            append_experiment(csv_path, mk, "A1",
                              f"imgsz={imgsz};epochs={cfg.epochs};seeds={cfg.seeds}",
                              {"map50": agg["map50"][0], "map5095": agg["map5095"][0],
                               "precision": agg["precision"][0], "recall": agg["recall"][0]},
                              best_pt)
            rows.append({
                "model": mk, "imgsz": imgsz,
                "map50_mean": agg["map50"][0], "map50_std": agg["map50"][1],
                "map5095_mean": agg["map5095"][0], "map5095_ci": (lo, hi),
                "precision": agg["precision"][0], "recall": agg["recall"][0],
                "params_M": stats["params_M"], "flops_G": stats["flops_G"],
                "size_MB": stats["size_MB"], "lat_model_ms": lat_model,
                "lat_e2e_ms": lat_e2e, "fps": fps,
            })
    md = comparison_table(rows)
    os.makedirs(os.path.dirname(table_path) or ".", exist_ok=True)
    with open(table_path, "w") as f:
        f.write(md + "\n")
    return md


def cmd_export(cfg: Config, weights_pt: str, out_onnx: str, imgsz: int) -> str:
    os.makedirs(os.path.dirname(out_onnx) or ".", exist_ok=True)
    export(weights_pt, out_onnx, imgsz=imgsz)
    return out_onnx


def _int_list(s: str) -> list[int]:
    return [int(x) for x in str(s).split(",") if str(x).strip() != ""]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(
        prog="plate_detect",
        epilog="Global flags follow the subcommand, e.g. plate_detect train --imgsz 960 --seeds 0",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "train", "eval", "export", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("--config")
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--raw-dir", dest="raw_dir")
        sp.add_argument("--processed-dir", dest="processed_dir")
        sp.add_argument("--dataset-yaml", dest="dataset_yaml")
        sp.add_argument("--split-dir", dest="split_dir")
        sp.add_argument("--project", default="runs")
        sp.add_argument("--imgsz", type=int)
        sp.add_argument("--imgszs", default="640")            # eval: comma list
        sp.add_argument("--seeds")                            # comma list; default cfg.seeds
        sp.add_argument("--models", default=",".join(MODEL_REGISTRY))
        sp.add_argument("--weights")                          # export: best.pt
        sp.add_argument("--out")                              # export: out.onnx
        sp.add_argument("--weights-dir", dest="weights_dir", default="weights")
        sp.add_argument("--csv", default="src/ml/experiments.csv")
        sp.add_argument("--table", default="docs/report/figures/plate_det_comparison.md")
        sp.add_argument("--sample-image", dest="sample_image", default="")

    a = p.parse_args(argv)
    cfg = _cfg_from_args(a)
    models = [m for m in a.models.split(",") if m]
    seeds = _int_list(a.seeds) if a.seeds else cfg.seeds

    if a.dry_run:
        print(f"[dry-run] cmd={a.cmd} raw={cfg.raw_dir} processed={cfg.processed_dir} "
              f"models={models} seeds={seeds} imgsz={a.imgsz or cfg.imgsz}")
        return 0

    if a.cmd == "prepare":
        print(f"prepared: {prepare(cfg)}")
        return 0
    if a.cmd == "check":
        errs = validate_processed(cfg.processed_dir, cfg.num_classes)
        if errs:
            print("INVALID:\n  " + "\n  ".join(errs)); return 1
        print("data-contract OK"); return 0
    if a.cmd == "train":
        dirs = cmd_train(cfg, a.project, models, a.imgsz or cfg.imgsz, seeds)
        print("trained:\n  " + "\n  ".join(dirs)); return 0
    if a.cmd == "eval":
        md = cmd_eval(cfg, a.project, models, _int_list(a.imgszs),
                      a.csv, a.table, a.weights_dir, a.sample_image)
        print(md); return 0
    if a.cmd == "export":
        out = cmd_export(cfg, a.weights, a.out, a.imgsz or cfg.imgsz)
        print(f"exported: {out}"); return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_cli.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/cli.py src/ml/plate_detect/tests/test_cli.py
git commit -m "feat(plate_detect): local CLI prepare/train/eval/export/check with imgsz ablation + dry-run

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: End-to-end pipeline smoke test (slow, CPU)

**Files:**
- Create: `src/ml/plate_detect/tests/test_pipeline_smoke.py`

**Interfaces:**
- Consumes: `make_raw_fixture`, `prepare`, `run_train`, `PlateDetector`, `export`, `run_eval`.
- This is the **gate before any real GPU run** (design §10): full wiring on synthetic fixtures, 1 tiny epoch, CPU, a few minutes.

- [ ] **Step 1: Write the test (this task's deliverable is the test itself)**

```python
# src/ml/plate_detect/tests/test_pipeline_smoke.py
import os
import cv2
import pytest
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.prepare import prepare

pytestmark = pytest.mark.slow


def test_full_pipeline_cpu(tmp_path):
    # 1. fixtures → prepare (exercises class-map gate, split, dedup both directions, validate)
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=8, seed=0)
    cfg = Config(
        raw_dir=str(raw), processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"), split_dir=str(tmp_path / "split"),
        imgsz=64, epochs=1, batch=2,
    )
    summary = prepare(cfg)
    assert summary["counts"]["train"] == 8
    assert "dup_train_test" in summary and "dup_train_val" in summary
    assert os.path.exists(summary["phash_report"])

    # 2. train 1 epoch on CPU (downloads yolov8n.pt on first run)
    from plate_detect.train.trainer import run_train
    run_dir = run_train("yolov8n", cfg, cfg.dataset_yaml, seed=0,
                        project=str(tmp_path / "runs"), imgsz=64)
    best = os.path.join(run_dir, "weights", "best.pt")
    assert os.path.exists(best)

    # 3. inference via PlateDetector (pt backend) — must not crash
    from plate_detect.inference.plate_detector import PlateDetector
    val_imgs = sorted((tmp_path / "proc" / "images" / "val").glob("*.jpg"))
    assert val_imgs, "prepare() produced no val images — check split logic"
    img = cv2.imread(val_imgs[0].as_posix())
    assert img is not None
    assert isinstance(PlateDetector(best, backend="pt", conf=0.01).detect(img), list)

    # 4. export ONNX + exercise the onnx backend seam (family dispatch + rescale)
    from plate_detect.export.to_onnx import export
    onnx_path = export(best, str(tmp_path / "model.onnx"), imgsz=64)
    assert os.path.exists(onnx_path)
    onnx_dets = PlateDetector(onnx_path, backend="onnx", conf=0.01).detect(img)
    assert isinstance(onnx_dets, list)

    # 5. run_eval on the test split returns the expected metric keys
    from plate_detect.eval.evaluate import run_eval
    m = run_eval(best, cfg.dataset_yaml, imgsz=64, conf=0.01, iou=0.5)
    assert {"map50", "map5095", "precision", "recall"} <= set(m)
```

- [ ] **Step 2: Run the smoke test (slow) to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_pipeline_smoke.py -m slow -q`
Expected: PASS (1 passed) in a few minutes on CPU (first run downloads `yolov8n.pt`).

- [ ] **Step 3: Run the full fast suite to confirm nothing regressed**

Run: `cd src/ml/plate_detect && python -m pytest -q -m "not slow"`
Expected: all fast tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/ml/plate_detect/tests/test_pipeline_smoke.py
git commit -m "test(plate_detect): end-to-end pipeline smoke test (CPU gate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: Report figures + class-map visual + thin local notebook

**Files:**
- Create: `src/ml/plate_detect/plate_detect/figures.py`
- Create: `src/ml/plate_detect/notebooks/train-plate-det.ipynb`
- Test: `src/ml/plate_detect/tests/test_figures.py`

**Interfaces:**
- Produces: `class_map_grid(records: list[dict], class_map: dict[int,str], out_png: str, per_class: int = 8) -> str` (renders ≥`per_class` crops per class — the design §6.2 **visual** confirmation of BSD/BSV); `qualitative_grid(detector, image_paths: list[str], out_png: str, n: int = 9) -> str` (draws detections on samples); `annotate_and_save(detector, image_path, out_png) -> str` (single image with boxes, used for low-light + timestamp-FP figures).

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_figures.py
import os
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.adapters import A1Adapter
from plate_detect.figures import class_map_grid

def test_class_map_grid_writes_png(tmp_path):
    make_raw_fixture(str(tmp_path / "raw"), n_per_split=8, seed=0)
    recs = A1Adapter().read_raw(str(tmp_path / "raw"))
    out = class_map_grid(recs, {0: "bien_1hang", 1: "bien_2hang"},
                         str(tmp_path / "class_map.png"), per_class=4)
    assert os.path.exists(out) and os.path.getsize(out) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_figures.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement figures.py**

```python
# src/ml/plate_detect/plate_detect/figures.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && python -m pytest tests/test_figures.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Create the thin local notebook**

Run this script once (it writes the notebook with `nbformat`; the notebook only orchestrates the CLI — all logic stays in the package):

```python
# run: python - <<'PY'
import nbformat as nbf
nb = nbf.v4.new_notebook()
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
nb.cells = [
    md("# Plate detection — A1 (YOLO26n vs YOLOv8n)\n"
       "Thin **local** driver (OS-independent). All logic lives in `plate_detect`; "
       "this notebook only calls the CLI. Select any local Python kernel with a GPU for full runs."),
    code("!pip install -e .  # from src/ml/plate_detect (or: pip install -e src/ml/plate_detect)"),
    code("import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"),
    md("## 1. Prepare (class-map gate → split → dedup train↔test & train↔val → validate)"),
    code("!plate_detect prepare"),
    code("!plate_detect check"),
    md("## 2. Train — full matrix @640 (both models × seeds 0,1,2)"),
    code("!plate_detect train --imgsz 640 --seeds 0,1,2 --project runs"),
    md("## 3. imgsz ablation @960 (single seed, both models)"),
    code("!plate_detect train --imgsz 960 --seeds 0 --project runs"),
    md("## 4. Export best → ONNX (per model & imgsz), parity-checked"),
    code("# example; repeat per model/imgsz best run:\n"
         "!plate_detect export --weights runs/yolo26n_s0_640/weights/best.pt --out weights/yolo26n_a1_640.onnx --imgsz 640"),
    md("## 5. Evaluate on A1 test → comparison table + experiments.csv"),
    code("!plate_detect eval --imgszs 640,960 --project runs --weights-dir weights "
         "--sample-image data/processed/a1_det/images/test/$(ls data/processed/a1_det/images/test | head -1)"),
]
nbf.write(nb, "src/ml/plate_detect/notebooks/train-plate-det.ipynb")
print("wrote notebook")
PY
```

Verify it is valid: `python -c "import nbformat; nbformat.read('src/ml/plate_detect/notebooks/train-plate-det.ipynb', as_version=4); print('ok')"`
Expected: `ok`.

- [ ] **Step 6: Commit**

```bash
git add src/ml/plate_detect/plate_detect/figures.py src/ml/plate_detect/tests/test_figures.py src/ml/plate_detect/notebooks/train-plate-det.ipynb
git commit -m "feat(plate_detect): report figures, class-map visual verify, thin local notebook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 18: Real training run on A1 + deliverables (compute — needs local GPU)

**Files:**
- Modify (append rows): `src/ml/experiments.csv`
- Create (git-lfs): `src/ml/plate_detect/weights/{yolov8n,yolo26n}_a1_640.onnx`, best `*.pt` per model
- Create: `docs/report/figures/plate_det_comparison.md`, `docs/report/figures/plate_det_qualitative.png`, `docs/report/figures/plate_det_lowlight.png`, `docs/report/figures/plate_det_timestamp_fp.png`, `docs/report/figures/plate_det_class_map.png`

**This task is compute, not code.** It produces the design §14 deliverables. Do **not** start until every prior task's tests pass and the smoke test is green (verification-before-completion). Requires a local machine with a CUDA GPU; on CPU-only, reduce to `--seeds 0` and skip the 100-epoch matrix (results won't meet the mAP gate but validate the flow).

- [ ] **Step 1: Gate — full test suite + smoke green**

Run: `pip install -e src/ml/plate_detect && cd src/ml/plate_detect && python -m pytest -q && python -m pytest -q -m slow`
Expected: all PASS. Do not proceed otherwise.

- [ ] **Step 2: Prepare real A1 + confirm class-map gate + record split/pHash**

Run: `cd <repo root> && plate_detect prepare && plate_detect check`
Expected: `data-contract OK`; note the printed `class_map` = `{0: bien_1hang, 1: bien_2hang}` (BSD/BSV verified); `configs/split/*.txt` + `data/processed/a1_det/phash_report.txt` written. Commit the split manifests + pHash report (never the A1 images):
```bash
git add src/ml/plate_detect/configs/a1_det.yaml src/ml/plate_detect/configs/split
git commit -m "chore(plate_detect): A1 split manifests + dataset yaml (class-map verified)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 3: Train the full matrix (2 models × seeds 0,1,2 @640) + ablation (@960, seed 0)**

Run:
```bash
plate_detect train --imgsz 640 --seeds 0,1,2 --project runs
plate_detect train --imgsz 960 --seeds 0   --project runs
```
Expected: `runs/{yolov8n,yolo26n}_s{0,1,2}_640/weights/best.pt` and `..._s0_960/weights/best.pt` exist.

- [ ] **Step 4: Export best per model/imgsz → ONNX (parity-checked)**

Run (pick the best seed per model by val mAP from the run summaries):
```bash
plate_detect export --weights runs/yolov8n_s0_640/weights/best.pt --out src/ml/plate_detect/weights/yolov8n_a1_640.onnx --imgsz 640
plate_detect export --weights runs/yolo26n_s0_640/weights/best.pt --out src/ml/plate_detect/weights/yolo26n_a1_640.onnx --imgsz 640
```
Also copy the chosen best `*.pt` into `weights/` (git-lfs).

- [ ] **Step 5: Evaluate on A1 test → comparison table + ledger**

Run:
```bash
plate_detect eval --imgszs 640,960 --project runs --weights-dir src/ml/plate_detect/weights \
  --sample-image "$(ls data/processed/a1_det/images/test/*.jpg | head -1)" \
  --csv src/ml/experiments.csv --table docs/report/figures/plate_det_comparison.md
```
Expected: `docs/report/figures/plate_det_comparison.md` written; rows appended to `src/ml/experiments.csv`. **Check the success gate: mAP@0.5 ≥ 0.90.** If a model misses it, note per-class AP (watch minority **class 0 BSD**) and consider the imgsz=960 result / augmentation before iterating.

- [ ] **Step 6: Generate report figures**

Run this script (qualitative + low-light + timestamp-FP + class-map visual):
```python
# run from repo root: python - <<'PY'
import glob
from plate_detect.inference.plate_detector import PlateDetector
from plate_detect.data.adapters import A1Adapter
from plate_detect.figures import class_map_grid, qualitative_grid, annotate_and_save

best = "src/ml/plate_detect/weights/yolo26n_a1_640.onnx"
det = PlateDetector(best, backend="onnx", conf=0.25)
test = sorted(glob.glob("data/processed/a1_det/images/test/*.jpg"))
qualitative_grid(det, test, "docs/report/figures/plate_det_qualitative.png", n=9)
# low-light: pick darker frames (lowest mean intensity)
import cv2, numpy as np
dark = sorted(test, key=lambda p: cv2.imread(p).mean())[:9]
qualitative_grid(det, dark, "docs/report/figures/plate_det_lowlight.png", n=9)
# timestamp false-positive check (DVR burn-in top strip): annotate a few full frames
annotate_and_save(det, test[0], "docs/report/figures/plate_det_timestamp_fp.png")
# class-map visual verify (BSD/BSV)
recs = A1Adapter().read_raw("data/raw/kaggle_vn_plate_segment")
class_map_grid(recs, {0: "bien_1hang", 1: "bien_2hang"}, "docs/report/figures/plate_det_class_map.png", per_class=8)
print("figures written")
PY
```

- [ ] **Step 7: Commit deliverables (weights via git-lfs)**

```bash
git lfs track "*.pt" "*.onnx"   # confirm .gitattributes already covers this
git add src/ml/plate_detect/weights docs/report/figures/plate_det_*.md docs/report/figures/plate_det_*.png src/ml/experiments.csv
git commit -m "feat(plate_detect): A1 detector deliverables — weights, ONNX, comparison table, figures

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 8: Update the Week-3 report chapter**

Cross-reference the comparison table + figures + pHash report into the Week-3 detection chapter (use the `thesis-writer` skill). Report mAP@0.5:0.95 mean±std + bootstrap CI as **descriptive** (S=3 — no significance claim); include params/FLOPs/size + latency model-only vs e2e (where YOLO26 NMS-free wins) + the imgsz 640-vs-960 result.

---

## Self-Review (completed while writing)

**Spec coverage vs design §14 deliverables:**
- Package + CLI (`prepare|train|eval|export|check`) → T1–T15 ✓
- class-map verified (yaml + visual) + split manifests + pHash report → T6 (gate), T8 (manifests + report), T17 (visual grid), T18 §2 ✓
- 2 models × S≥3 seeds trained, weights git-lfs → T9, T18 §3/§7 ✓
- Comparison table (mean±std + CI + params/FLOPs/size + latency×2 + FPS + imgsz) → T13, T14, T15, T18 §5 ✓
- mAP@0.5 ≥ 0.90 + mAP@0.5:0.95 → T14 `run_eval`, T18 §5 gate ✓
- ONNX FP32 parity + `PlateDetector` pt|onnx → T11, T12, T18 §4 ✓
- Test suite (unit + smoke + data-contract) + notebook → T1–T16, T17 ✓
- Figures (qualitative + low-light + timestamp-FP) + experiments.csv → T17, T18 §5/§6 ✓

**Review-fix coverage:** F1 local/OS-independent → Global Constraints + T15 + T17 ✓ · G1 imgsz ablation → T9/T14/T15/T18 ✓ · G2 S=3 descriptive → Global Constraints + T18 §8 ✓ · G3 dedup train↔val → T8 ✓ · G4 majority-class stratify → T8 ✓ · BSD/BSV verify → T6/T17 ✓

**Type consistency:** `run_train(..., imgsz=None)` and `run_name(model_key, seed, imgsz)` used consistently in T9/T15/T16. `run_eval` returns `{map50,map5095,precision,recall,per_class_ap}`; `aggregate_seeds`/`append_experiment` consume `map50,map5095,precision,recall`; `comparison_table` row keys match what `cmd_eval` builds (T14/T15). `PlateDetection` fields identical across T11/T12/T17.

**No placeholders:** every code step contains complete code; every run step has an exact command + expected output.
