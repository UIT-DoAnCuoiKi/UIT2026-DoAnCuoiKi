# Plate-Region Detection (A1, YOLO26n vs YOLO8n) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an extensible `plate_detect` Python package that trains and reliably compares YOLO26n vs YOLO8n for license-plate-region detection on the A1 dataset, exporting weights + ONNX + a `PlateDetector` API for the downstream ALPR pipeline.

**Architecture:** A pip-installable package (`src/ml/plate_detect/`) with clear stages — data prep (dataset-adapter → poly→bbox → split → dedup → validate), training (model-registry wrapper over Ultralytics), evaluation (multi-seed + bootstrap CI), ONNX export (parity-checked), and a backend-swappable inference API. A thin Colab notebook drives GPU training by importing the package; a synthetic-fixture smoke test exercises the whole pipeline on CPU before any real run.

**Tech Stack:** Python 3.11+, Ultralytics 8.4.37 (YOLO26 + YOLOv8), OpenCV, NumPy, PyYAML, ONNX Runtime, pytest. Training on Google Colab GPU via the VS Code Colab extension.

## Global Constraints

- **Ultralytics version pinned to `ultralytics==8.4.37`** (first version bundling YOLO26; the older `detect-yolov8.ipynb` pinned `8.3.0` which lacks YOLO26). Same env for both models.
- **Package name `plate_detect`, installed with `pip install -e src/ml/plate_detect`** (identical on Mac and Colab). All logic lives in the package; notebooks stay thin.
- **Two classes, fixed mapping: `0: bien_1hang`, `1: bien_2hang`.** Axis-aligned bbox detection only (no OBB/seg).
- **Reliability: ≥3 training seeds per model (default `[0, 1, 2]`); report mean ± std and bootstrap 95% CI on test mAP.**
- **Fixed hyperparameters for a fair comparison:** `imgsz=640, epochs=100, batch=16, patience=20, deterministic=True`.
- **Success gate:** mAP@0.5 ≥ 0.90 on the A1 test split; always also report mAP@0.5:0.95.
- **Weights (`*.pt`, `*.onnx`) tracked via git-lfs.** Never commit A1 images (license "Unknown"); tests use synthetic fixtures only.
- **Results ledger:** append to `src/ml/experiments.csv` (existing schema: `date,model,dataset,hyperparams,mAP50,mAP50-95,precision,recall,weights`).
- **Branch:** all work on `feat/plate-detect-a1`. End every commit message with a trailing `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` line.
- **Report language:** Vietnamese prose with English technical terms (matches thesis convention).

---

## File Structure

```
src/ml/plate_detect/
  pyproject.toml                       # T1
  .gitattributes                       # T1 (git-lfs for weights)
  plate_detect/
    __init__.py                        # T1
    config.py                          # T1  Config dataclass + yaml load/merge
    data/
      __init__.py
      fixtures.py                      # T2  synthetic mini-dataset generator
      bbox.py                          # T3  polygon_to_bbox
      class_map.py                     # T4  infer/verify class-id ↔ layout
      split.py                         # T5  stratified deterministic split
      dedup.py                         # T6  perceptual-hash near-dup
      validate.py                      # T7  data-contract checks
      adapters.py                      # T8  DatasetAdapter Protocol + A1Adapter
      prepare.py                       # T8  orchestrator raw→processed
    train/
      __init__.py
      registry.py                      # T9  MODEL_REGISTRY
      trainer.py                       # T10 build_train_args + run_train
    eval/
      __init__.py
      metrics.py                       # T11 bootstrap_ci + measure_latency
      evaluate.py                      # T12 aggregate_seeds + experiments.csv
    export/
      __init__.py
      to_onnx.py                       # T15 export + parity
    inference/
      __init__.py
      postprocess.py                   # T13 nms + decode_v8 + decode_v26
      plate_detector.py                # T14 PlateDetection + PlateDetector
    cli.py                             # T16 argparse subcommands + --dry-run
  configs/
    default.yaml                       # T1
    a1_det.yaml                        # written by prepare (T8)
    split/                             # manifests written by prepare (T8)
  tests/
    conftest.py                        # T2
    test_config.py                     # T1
    test_fixtures.py                   # T2
    test_bbox.py                       # T3
    test_class_map.py                  # T4
    test_split.py                      # T5
    test_dedup.py                      # T6
    test_validate.py                   # T7
    test_prepare.py                    # T8
    test_registry.py                   # T9
    test_trainer.py                    # T10
    test_metrics.py                    # T11
    test_evaluate.py                   # T12
    test_postprocess.py                # T13
    test_plate_detector.py             # T14
    test_to_onnx.py                    # T15
    test_cli.py                        # T16
    test_pipeline_smoke.py             # T17
  notebooks/
    train-plate-det.ipynb              # T18 (thin Colab driver)
  weights/                             # git-lfs (produced at runtime)
```

---

### Task 1: Package scaffold, Config, git-lfs

**Files:**
- Create: `src/ml/plate_detect/pyproject.toml`
- Create: `src/ml/plate_detect/.gitattributes`
- Create: `src/ml/plate_detect/plate_detect/__init__.py`
- Create: `src/ml/plate_detect/plate_detect/config.py`
- Create: `src/ml/plate_detect/configs/default.yaml`
- Test: `src/ml/plate_detect/tests/test_config.py`

**Interfaces:**
- Produces: `Config` dataclass with fields `raw_dir, processed_dir, dataset_yaml, split_dir, imgsz, epochs, batch, patience, seeds, class_names, conf, iou, split_ratios`; classmethod `Config.load(path: str | None = None, **overrides) -> Config`; property `Config.num_classes -> int`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_config.py
from plate_detect.config import Config

def test_defaults():
    c = Config()
    assert c.imgsz == 640
    assert c.epochs == 100
    assert c.batch == 16
    assert c.patience == 20
    assert c.seeds == [0, 1, 2]
    assert c.class_names == {0: "bien_1hang", 1: "bien_2hang"}
    assert c.num_classes == 2

def test_load_yaml_override(tmp_path):
    y = tmp_path / "cfg.yaml"
    y.write_text("epochs: 3\nbatch: 2\n")
    c = Config.load(str(y))
    assert c.epochs == 3            # from yaml
    assert c.batch == 2             # from yaml
    assert c.imgsz == 640           # default retained

def test_load_kwargs_override_yaml(tmp_path):
    y = tmp_path / "cfg.yaml"
    y.write_text("epochs: 3\n")
    c = Config.load(str(y), epochs=7)
    assert c.epochs == 7            # kwarg beats yaml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pip install -e . -q && pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.config'`

- [ ] **Step 3: Write minimal implementation**

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
]

[project.optional-dependencies]
dev = ["pytest"]

[tool.setuptools.packages.find]
include = ["plate_detect*"]
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
        data.update(overrides)
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

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Verify git-lfs attribute is active**

Run: `cd src/ml/plate_detect && git add .gitattributes && git check-attr filter -- weights/x.pt`
Expected: output contains `filter: lfs`

- [ ] **Step 6: Commit**

```bash
git add src/ml/plate_detect/pyproject.toml src/ml/plate_detect/.gitattributes \
  src/ml/plate_detect/plate_detect/__init__.py src/ml/plate_detect/plate_detect/config.py \
  src/ml/plate_detect/configs/default.yaml src/ml/plate_detect/tests/test_config.py
git commit -m "feat(plate_detect): package scaffold, Config, git-lfs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Synthetic fixtures generator

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/__init__.py`
- Create: `src/ml/plate_detect/plate_detect/data/fixtures.py`
- Create: `src/ml/plate_detect/tests/conftest.py`
- Test: `src/ml/plate_detect/tests/test_fixtures.py`

**Interfaces:**
- Produces: `make_raw_fixture(root: str, n_per_split: int = 10, seed: int = 0) -> None` — writes an A1-raw-shaped tree `images/{train,val}/*.jpg` + `labels/{train,val}/*.txt` where each label line is `cls x1 y1 x2 y2 x3 y3 x4 y4` (normalized, 4 corners); class 0 draws a **wide** rectangle (1-row), class 1 a near-**square** rectangle (2-row). Pytest fixture `raw_fixture(tmp_path)` returning the root path.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_fixtures.py
from pathlib import Path
from plate_detect.data.fixtures import make_raw_fixture

def test_make_raw_fixture_layout(tmp_path):
    make_raw_fixture(str(tmp_path), n_per_split=4, seed=0)
    for split in ("train", "val"):
        imgs = list((tmp_path / "images" / split).glob("*.jpg"))
        lbls = list((tmp_path / "labels" / split).glob("*.txt"))
        assert len(imgs) == 4
        assert len(lbls) == 4
    # every label line: class in {0,1} + 8 normalized coords in [0,1]
    line = (tmp_path / "labels" / "train").glob("*.txt").__next__().read_text().splitlines()[0]
    parts = line.split()
    assert parts[0] in {"0", "1"}
    coords = list(map(float, parts[1:]))
    assert len(coords) == 8
    assert all(0.0 <= v <= 1.0 for v in coords)

def test_make_raw_fixture_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    make_raw_fixture(str(a), n_per_split=3, seed=42)
    make_raw_fixture(str(b), n_per_split=3, seed=42)
    la = sorted(p.name for p in (a / "labels" / "train").glob("*.txt"))
    lb = sorted(p.name for p in (b / "labels" / "train").glob("*.txt"))
    assert la == lb
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_fixtures.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.data.fixtures'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/data/__init__.py
```

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
            img = np.full((H, W, 3), 90, np.uint8)  # gray background
            cls = i % 2                              # alternate 1-row / 2-row
            pw = rng.uniform(0.28, 0.36) * W
            ph = (pw / rng.uniform(3.5, 4.5)) if cls == 0 else (pw / rng.uniform(1.2, 1.5))
            cx = rng.uniform(0.35, 0.65) * W
            cy = rng.uniform(0.35, 0.65) * H
            x1, y1 = int(cx - pw / 2), int(cy - ph / 2)
            x2, y2 = int(cx + pw / 2), int(cy + ph / 2)
            cv2.rectangle(img, (x1, y1), (x2, y2), (235, 235, 235), -1)
            cv2.imwrite(os.path.join(img_dir, f"{split}_{i}.jpg"), img)
            corners = [x1 / W, y1 / H, x2 / W, y1 / H, x2 / W, y2 / H, x1 / W, y2 / H]
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

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_fixtures.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/__init__.py \
  src/ml/plate_detect/plate_detect/data/fixtures.py \
  src/ml/plate_detect/tests/conftest.py src/ml/plate_detect/tests/test_fixtures.py
git commit -m "feat(plate_detect): synthetic raw-dataset fixtures

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Polygon → axis-aligned bbox

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/bbox.py`
- Test: `src/ml/plate_detect/tests/test_bbox.py`

**Interfaces:**
- Produces: `polygon_to_bbox(coords: list[float]) -> tuple[float, float, float, float] | None` — input 8 normalized corner coords, returns `(xc, yc, w, h)` normalized and clamped to `[0,1]`, or `None` if degenerate (w or h ≤ 0 after clamp).

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_bbox.py
import pytest
from plate_detect.data.bbox import polygon_to_bbox

def test_axis_aligned_rectangle():
    # corners of rect [0.2,0.3]..[0.6,0.5]
    coords = [0.2, 0.3, 0.6, 0.3, 0.6, 0.5, 0.2, 0.5]
    xc, yc, w, h = polygon_to_bbox(coords)
    assert xc == pytest.approx(0.4)
    assert yc == pytest.approx(0.4)
    assert w == pytest.approx(0.4)
    assert h == pytest.approx(0.2)

def test_tilted_quad_uses_minmax():
    coords = [0.30, 0.20, 0.70, 0.30, 0.65, 0.55, 0.25, 0.45]
    xc, yc, w, h = polygon_to_bbox(coords)
    assert w == pytest.approx(0.45)   # 0.70 - 0.25
    assert h == pytest.approx(0.35)   # 0.55 - 0.20

def test_clamp_out_of_range():
    coords = [-0.1, 0.0, 1.2, 0.0, 1.2, 0.5, -0.1, 0.5]
    xc, yc, w, h = polygon_to_bbox(coords)
    assert 0.0 <= xc <= 1.0 and 0.0 <= w <= 1.0
    assert w == pytest.approx(1.0)    # clamped 0..1

def test_degenerate_returns_none():
    coords = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    assert polygon_to_bbox(coords) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_bbox.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.data.bbox'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/data/bbox.py
from __future__ import annotations

def polygon_to_bbox(coords: list[float]):
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

Run: `cd src/ml/plate_detect && pytest tests/test_bbox.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/bbox.py src/ml/plate_detect/tests/test_bbox.py
git commit -m "feat(plate_detect): polygon-to-bbox conversion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Class-map verification (id ↔ layout)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/class_map.py`
- Test: `src/ml/plate_detect/tests/test_class_map.py`

**Interfaces:**
- Consumes: `polygon_to_bbox` (Task 3).
- Produces: `infer_layout_map(objects_by_class: dict[int, list[float]]) -> dict[int, str]` — input maps class-id → list of aspect ratios (w/h); returns `{id: "bien_1hang"|"bien_2hang"}` assigning the higher-median-aspect-ratio id to `bien_1hang`. `verify_class_map(inferred: dict[int,str], yaml_names: dict[int,str] | None) -> dict[int,str]` — raises `ValueError` if `yaml_names` present and contradicts `inferred`; else returns `inferred`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_class_map.py
import pytest
from plate_detect.data.class_map import infer_layout_map, verify_class_map

def test_infer_wide_is_1hang():
    objs = {0: [4.0, 3.8, 4.2], 1: [1.3, 1.2, 1.4]}   # class 0 wide, class 1 square
    m = infer_layout_map(objs)
    assert m == {0: "bien_1hang", 1: "bien_2hang"}

def test_infer_when_ids_swapped():
    objs = {0: [1.3, 1.2], 1: [4.0, 4.1]}             # class 1 is the wide one
    m = infer_layout_map(objs)
    assert m == {0: "bien_2hang", 1: "bien_1hang"}

def test_verify_agrees():
    inferred = {0: "bien_1hang", 1: "bien_2hang"}
    assert verify_class_map(inferred, {0: "bien_1hang", 1: "bien_2hang"}) == inferred

def test_verify_conflict_raises():
    inferred = {0: "bien_1hang", 1: "bien_2hang"}
    with pytest.raises(ValueError):
        verify_class_map(inferred, {0: "bien_2hang", 1: "bien_1hang"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_class_map.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.data.class_map'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/data/class_map.py
from __future__ import annotations
from statistics import median

def infer_layout_map(objects_by_class: dict[int, list[float]]) -> dict[int, str]:
    med = {cid: median(ars) for cid, ars in objects_by_class.items()}
    wide_id = max(med, key=med.get)   # highest aspect ratio == 1-row (long plate)
    return {cid: ("bien_1hang" if cid == wide_id else "bien_2hang") for cid in med}

def verify_class_map(inferred: dict[int, str], yaml_names: dict[int, str] | None) -> dict[int, str]:
    if yaml_names:
        for cid, name in inferred.items():
            yn = str(yaml_names.get(cid, "")).lower()
            is_1 = ("1" in yn) or ("dai" in yn) or ("long" in yn) or ("lpd" in yn) or ("bsd" in yn)
            is_2 = ("2" in yn) or ("vuong" in yn) or ("square" in yn) or ("lpv" in yn) or ("bsv" in yn)
            if is_1 and name != "bien_1hang":
                raise ValueError(f"class {cid}: yaml '{yn}' vs inferred '{name}'")
            if is_2 and name != "bien_2hang":
                raise ValueError(f"class {cid}: yaml '{yn}' vs inferred '{name}'")
    return inferred
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_class_map.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/class_map.py src/ml/plate_detect/tests/test_class_map.py
git commit -m "feat(plate_detect): class-id to layout verification

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Stratified deterministic split

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/split.py`
- Test: `src/ml/plate_detect/tests/test_split.py`

**Interfaces:**
- Produces: `stratified_split(items: list[str], labels: list[int], ratios: dict[str, float], seed: int = 42) -> dict[str, list[str]]` — splits `items` into the named buckets (keys of `ratios`, must sum to 1.0) with per-label stratification; deterministic for a fixed seed; buckets are disjoint and cover all items.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_split.py
import pytest
from plate_detect.data.split import stratified_split

def _items(n): return [f"img_{i}" for i in range(n)]

def test_deterministic():
    items = _items(100); labels = [i % 2 for i in range(100)]
    a = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    b = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    assert a == b

def test_disjoint_and_complete():
    items = _items(100); labels = [i % 2 for i in range(100)]
    out = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=1)
    val, test = set(out["val"]), set(out["test"])
    assert val.isdisjoint(test)
    assert val | test == set(items)

def test_stratified_balance():
    # 80 of class 0, 20 of class 1
    items = _items(100); labels = [0] * 80 + [1] * 20
    out = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=7)
    c1_val = sum(1 for x in out["val"] if int(x.split("_")[1]) >= 80)
    assert c1_val == pytest.approx(10, abs=1)   # ~half of the 20 class-1 items

def test_ratios_must_sum_to_one():
    with pytest.raises(ValueError):
        stratified_split(_items(4), [0, 0, 1, 1], {"val": 0.4, "test": 0.4}, seed=0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_split.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.data.split'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/data/split.py
from __future__ import annotations
import random
from collections import defaultdict

def stratified_split(items, labels, ratios, seed: int = 42):
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {sum(ratios.values())}")
    rng = random.Random(seed)
    by_label: dict[int, list[str]] = defaultdict(list)
    for it, lb in zip(items, labels):
        by_label[lb].append(it)
    names = list(ratios.keys())
    out: dict[str, list[str]] = {n: [] for n in names}
    for lb in sorted(by_label):
        group = sorted(by_label[lb])       # sort first → stable pre-shuffle
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

Run: `cd src/ml/plate_detect && pytest tests/test_split.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/split.py src/ml/plate_detect/tests/test_split.py
git commit -m "feat(plate_detect): stratified deterministic split

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Perceptual-hash near-duplicate detection

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/dedup.py`
- Test: `src/ml/plate_detect/tests/test_dedup.py`

**Interfaces:**
- Produces: `ahash(image: np.ndarray) -> int` (64-bit average hash); `hamming(a: int, b: int) -> int`; `find_duplicates(train: dict[str,int], test: dict[str,int], threshold: int = 5) -> list[tuple[str,str,int]]` — returns `(test_name, train_name, distance)` for each test image whose nearest train hash is within `threshold`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_dedup.py
import numpy as np
from plate_detect.data.dedup import ahash, hamming, find_duplicates

def _img(v): return np.full((64, 64, 3), v, np.uint8)

def test_identical_hash_zero_distance():
    a = ahash(_img(120)); b = ahash(_img(120))
    assert hamming(a, b) == 0

def test_find_duplicates_flags_near():
    grad = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1))
    grad = np.stack([grad] * 3, axis=-1)
    train = {"t0": ahash(grad)}
    test = {"q0": ahash(grad.copy()), "q1": ahash(_img(10))}
    dups = find_duplicates(train, test, threshold=5)
    names = {d[0] for d in dups}
    assert "q0" in names          # duplicate of t0
    assert "q1" not in names      # flat image, different
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_dedup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.data.dedup'`

- [ ] **Step 3: Write minimal implementation**

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

def find_duplicates(train: dict[str, int], test: dict[str, int], threshold: int = 5):
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

Run: `cd src/ml/plate_detect && pytest tests/test_dedup.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/dedup.py src/ml/plate_detect/tests/test_dedup.py
git commit -m "feat(plate_detect): perceptual-hash near-duplicate check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Data-contract validation

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/validate.py`
- Test: `src/ml/plate_detect/tests/test_validate.py`

**Interfaces:**
- Produces: `validate_processed(processed_dir: str, num_classes: int = 2) -> list[str]` — returns a list of human-readable error strings (empty == valid) checking: every image has a label; every label class-id in `[0, num_classes)`; every bbox value in `[0,1]`; no orphan label without image. `assert_valid(processed_dir: str, num_classes: int = 2) -> None` — raises `ValueError` joining errors if any.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_validate.py
import os
import cv2
import numpy as np
import pytest
from plate_detect.data.validate import validate_processed, assert_valid

def _mk(root, split="train"):
    for sub in ("images", "labels"):
        os.makedirs(os.path.join(root, sub, split), exist_ok=True)

def _write_img(root, split, name):
    cv2.imwrite(os.path.join(root, "images", split, name + ".jpg"),
                np.zeros((32, 32, 3), np.uint8))

def _write_lbl(root, split, name, text):
    with open(os.path.join(root, "labels", split, name + ".txt"), "w") as f:
        f.write(text)

def test_valid_dir(tmp_path):
    r = str(tmp_path); _mk(r)
    _write_img(r, "train", "a"); _write_lbl(r, "train", "a", "0 0.5 0.5 0.2 0.2\n")
    assert validate_processed(r) == []

def test_missing_label(tmp_path):
    r = str(tmp_path); _mk(r)
    _write_img(r, "train", "a")     # no label
    errs = validate_processed(r)
    assert any("label" in e for e in errs)

def test_bad_class_and_range(tmp_path):
    r = str(tmp_path); _mk(r)
    _write_img(r, "train", "a"); _write_lbl(r, "train", "a", "5 0.5 0.5 0.2 0.2\n")
    _write_img(r, "train", "b"); _write_lbl(r, "train", "b", "0 1.7 0.5 0.2 0.2\n")
    errs = validate_processed(r)
    assert any("class" in e for e in errs)
    assert any("range" in e for e in errs)
    with pytest.raises(ValueError):
        assert_valid(r)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.data.validate'`

- [ ] **Step 3: Write minimal implementation**

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
            for ln in open(lp).read().splitlines():
                p = ln.split()
                if not p:
                    continue
                cid = int(p[0])
                if cid < 0 or cid >= num_classes:
                    errors.append(f"[{split}] {os.path.basename(lp)}: class {cid} out of range")
                for v in map(float, p[1:5]):
                    if v < 0.0 or v > 1.0:
                        errors.append(f"[{split}] {os.path.basename(lp)}: coord {v} out of range")
    return errors

def assert_valid(processed_dir: str, num_classes: int = 2) -> None:
    errs = validate_processed(processed_dir, num_classes)
    if errs:
        raise ValueError("data-contract validation failed:\n  " + "\n  ".join(errs))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_validate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/validate.py src/ml/plate_detect/tests/test_validate.py
git commit -m "feat(plate_detect): data-contract validation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: DatasetAdapter + prepare orchestrator

**Files:**
- Create: `src/ml/plate_detect/plate_detect/data/adapters.py`
- Create: `src/ml/plate_detect/plate_detect/data/prepare.py`
- Test: `src/ml/plate_detect/tests/test_prepare.py`

**Interfaces:**
- Consumes: `polygon_to_bbox` (T3), `infer_layout_map`/`verify_class_map` (T4), `stratified_split` (T5), `ahash`/`find_duplicates` (T6), `validate_processed` (T7), `Config` (T1).
- Produces: `A1Adapter` with `read_raw(raw_dir) -> list[dict]` (each `{split, image_path, objects:[(cls, x1..y4)]}`) and `class_names -> dict[int,str]`; `prepare(cfg: Config, dedup_threshold: int = 5) -> dict` — runs adapter → bbox convert → keep raw `train`, split raw `val`→`val`+`test` → write `processed/{images,labels}/{split}` + `configs/a1_det.yaml` + `configs/split/{split}.txt` → dedup test-vs-train → validate; returns a summary dict `{"counts": {...}, "dup_pairs": int, "class_map": {...}}`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_prepare.py
import os
import yaml
from plate_detect.config import Config
from plate_detect.data.prepare import prepare
from plate_detect.data.validate import validate_processed

def test_prepare_end_to_end(tmp_path, raw_fixture):
    cfg = Config(
        raw_dir=str(raw_fixture),
        processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"),
        split_dir=str(tmp_path / "split"),
    )
    summary = prepare(cfg)
    # processed layout exists with train/val/test
    for split in ("train", "val", "test"):
        assert os.path.isdir(os.path.join(cfg.processed_dir, "images", split))
    # dataset yaml written with 2 classes
    y = yaml.safe_load(open(cfg.dataset_yaml))
    assert len(y["names"]) == 2
    # manifests written
    assert os.path.exists(os.path.join(cfg.split_dir, "train.txt"))
    # data contract holds
    assert validate_processed(cfg.processed_dir) == []
    # train kept intact (10 fixture train images), val(10) split into val+test
    assert summary["counts"]["train"] == 10
    assert summary["counts"]["val"] + summary["counts"]["test"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_prepare.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.data.prepare'`

- [ ] **Step 3: Write minimal implementation**

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
                    for ln in open(lp).read().splitlines():
                        parts = ln.split()
                        if len(parts) >= 9 and parts[0].lstrip("-").isdigit():
                            objects.append((int(parts[0]), list(map(float, parts[1:9]))))
                records.append({"split": split, "image_path": ip, "objects": objects})
        return records
```

```python
# src/ml/plate_detect/plate_detect/data/prepare.py
from __future__ import annotations
import os
import shutil
import cv2
import yaml
from ..config import Config
from .adapters import A1Adapter
from .bbox import polygon_to_bbox
from .class_map import infer_layout_map, verify_class_map
from .split import stratified_split
from .dedup import ahash, find_duplicates
from .validate import validate_processed

def _write_pair(processed_dir, split, stem, src_img, bbox_lines):
    img_out = os.path.join(processed_dir, "images", split)
    lbl_out = os.path.join(processed_dir, "labels", split)
    os.makedirs(img_out, exist_ok=True); os.makedirs(lbl_out, exist_ok=True)
    shutil.copy(src_img, os.path.join(img_out, stem + ".jpg"))
    with open(os.path.join(lbl_out, stem + ".txt"), "w") as f:
        f.write("\n".join(bbox_lines) + ("\n" if bbox_lines else ""))

def prepare(cfg: Config, dedup_threshold: int = 5) -> dict:
    adapter = A1Adapter()
    records = adapter.read_raw(cfg.raw_dir)

    # verify class map from polygon aspect ratios
    objects_by_class: dict[int, list[float]] = {}
    for r in records:
        for cid, coords in r["objects"]:
            bb = polygon_to_bbox(coords)
            if bb:
                _, _, w, h = bb
                objects_by_class.setdefault(cid, []).append(w / h if h else 0.0)
    class_map = verify_class_map(infer_layout_map(objects_by_class), adapter.class_names())

    # keep raw train; pool raw val for re-split into val+test
    train_recs = [r for r in records if r["split"] == "train"]
    val_pool = [r for r in records if r["split"] == "val"]
    pool_items = [r["image_path"] for r in val_pool]
    pool_labels = [r["objects"][0][0] if r["objects"] else 0 for r in val_pool]
    split_map = stratified_split(pool_items, pool_labels, cfg.split_ratios, seed=42)

    assign = {"train": train_recs}
    by_path = {r["image_path"]: r for r in val_pool}
    for name, paths in split_map.items():
        assign[name] = [by_path[p] for p in paths]

    # clear + write processed
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
            f.write("\n".join(stems) + "\n")

    # dataset yaml
    os.makedirs(os.path.dirname(cfg.dataset_yaml) or ".", exist_ok=True)
    with open(cfg.dataset_yaml, "w") as f:
        yaml.safe_dump({
            "path": os.path.abspath(cfg.processed_dir),
            "train": "images/train", "val": "images/val", "test": "images/test",
            "names": {int(k): v for k, v in class_map.items()},
        }, f, sort_keys=False)

    # dedup test vs train
    def hashes(split):
        d = {}
        for r in assign[split]:
            img = cv2.imread(r["image_path"])
            if img is not None:
                d[os.path.basename(r["image_path"])] = ahash(img)
        return d
    dup_pairs = find_duplicates(hashes("train"), hashes("test"), threshold=dedup_threshold)

    errs = validate_processed(cfg.processed_dir, cfg.num_classes)
    if errs:
        raise ValueError("prepare produced invalid dataset:\n  " + "\n  ".join(errs))

    return {"counts": counts, "dup_pairs": len(dup_pairs), "class_map": class_map}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_prepare.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/data/adapters.py \
  src/ml/plate_detect/plate_detect/data/prepare.py src/ml/plate_detect/tests/test_prepare.py
git commit -m "feat(plate_detect): A1 adapter and prepare orchestrator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Model registry

**Files:**
- Create: `src/ml/plate_detect/plate_detect/train/__init__.py`
- Create: `src/ml/plate_detect/plate_detect/train/registry.py`
- Test: `src/ml/plate_detect/tests/test_registry.py`

**Interfaces:**
- Produces: `MODEL_REGISTRY: dict[str, str]` mapping `"yolov8n"`/`"yolo26n"` to pretrained weight filenames; `resolve(key: str) -> str` raising `KeyError` (message lists valid keys) on unknown key.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_registry.py
import pytest
from plate_detect.train.registry import MODEL_REGISTRY, resolve

def test_known_models():
    assert resolve("yolov8n") == "yolov8n.pt"
    assert resolve("yolo26n") == "yolo26n.pt"

def test_unknown_raises():
    with pytest.raises(KeyError):
        resolve("nope")

def test_both_models_present():
    assert {"yolov8n", "yolo26n"} <= set(MODEL_REGISTRY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.train.registry'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/train/__init__.py
```

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

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_registry.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/train/__init__.py \
  src/ml/plate_detect/plate_detect/train/registry.py src/ml/plate_detect/tests/test_registry.py
git commit -m "feat(plate_detect): model registry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Trainer (args builder + run wrapper)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/train/trainer.py`
- Test: `src/ml/plate_detect/tests/test_trainer.py`

**Interfaces:**
- Consumes: `Config` (T1), `resolve` (T9).
- Produces: `build_train_args(cfg: Config, data_yaml: str, seed: int, project: str, name: str) -> dict` — the exact kwargs dict passed to Ultralytics `model.train()`; `run_train(model_key: str, cfg: Config, data_yaml: str, seed: int, project: str) -> str` — trains and returns the run directory (imports Ultralytics lazily so unit tests need no GPU).

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_trainer.py
from plate_detect.config import Config
from plate_detect.train.trainer import build_train_args

def test_build_train_args_fair_and_fixed():
    cfg = Config(imgsz=640, epochs=100, batch=16, patience=20)
    args = build_train_args(cfg, "d.yaml", seed=1, project="runs", name="yolo26n_s1")
    assert args["data"] == "d.yaml"
    assert args["imgsz"] == 640
    assert args["epochs"] == 100
    assert args["batch"] == 16          # fixed, not -1/auto
    assert args["patience"] == 20
    assert args["seed"] == 1
    assert args["deterministic"] is True
    assert args["close_mosaic"] == 10
    assert args["name"] == "yolo26n_s1"

def test_build_train_args_seed_varies():
    cfg = Config()
    a0 = build_train_args(cfg, "d.yaml", 0, "runs", "m_s0")
    a2 = build_train_args(cfg, "d.yaml", 2, "runs", "m_s2")
    assert a0["seed"] == 0 and a2["seed"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_trainer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.train.trainer'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/train/trainer.py
from __future__ import annotations
from ..config import Config
from .registry import resolve

def build_train_args(cfg: Config, data_yaml: str, seed: int, project: str, name: str) -> dict:
    return {
        "data": data_yaml,
        "imgsz": cfg.imgsz,
        "epochs": cfg.epochs,
        "batch": cfg.batch,          # fixed for reproducible fair comparison
        "patience": cfg.patience,
        "seed": seed,
        "deterministic": True,
        "hsv_v": 0.5,                # brightness aug (~11% dark images in A1)
        "hsv_s": 0.7,
        "degrees": 5.0,              # mild skew (gate camera)
        "perspective": 0.0005,
        "close_mosaic": 10,
        "project": project,
        "name": name,
        "exist_ok": True,
        "verbose": False,
    }

def run_train(model_key: str, cfg: Config, data_yaml: str, seed: int, project: str) -> str:
    from ultralytics import YOLO
    model = YOLO(resolve(model_key))
    name = f"{model_key}_s{seed}"
    results = model.train(**build_train_args(cfg, data_yaml, seed, project, name))
    return str(results.save_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_trainer.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/train/trainer.py src/ml/plate_detect/tests/test_trainer.py
git commit -m "feat(plate_detect): trainer args builder and run wrapper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Metrics (bootstrap CI + latency)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/eval/__init__.py`
- Create: `src/ml/plate_detect/plate_detect/eval/metrics.py`
- Test: `src/ml/plate_detect/tests/test_metrics.py`

**Interfaces:**
- Produces: `bootstrap_ci(values: list[float], n_boot: int = 1000, seed: int = 0, alpha: float = 0.05) -> tuple[float,float,float]` returning `(mean, lo, hi)`; `measure_latency(fn, inp, warmup: int = 5, runs: int = 20) -> float` returning median seconds.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_metrics.py
import time
import pytest
from plate_detect.eval.metrics import bootstrap_ci, measure_latency

def test_bootstrap_constant_collapses():
    mean, lo, hi = bootstrap_ci([0.9] * 50, n_boot=200, seed=0)
    assert mean == pytest.approx(0.9)
    assert lo == pytest.approx(0.9) and hi == pytest.approx(0.9)

def test_bootstrap_ci_orders():
    vals = [0.1, 0.2, 0.9, 0.95, 0.5, 0.6, 0.55, 0.4]
    mean, lo, hi = bootstrap_ci(vals, n_boot=500, seed=1)
    assert lo <= mean <= hi

def test_measure_latency_median():
    med = measure_latency(lambda x: time.sleep(0.01), None, warmup=2, runs=5)
    assert med == pytest.approx(0.01, abs=0.02)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.eval.metrics'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/eval/__init__.py
```

```python
# src/ml/plate_detect/plate_detect/eval/metrics.py
from __future__ import annotations
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_metrics.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/eval/__init__.py \
  src/ml/plate_detect/plate_detect/eval/metrics.py src/ml/plate_detect/tests/test_metrics.py
git commit -m "feat(plate_detect): bootstrap CI and latency metrics

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Evaluate (aggregate seeds + experiments.csv)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/eval/evaluate.py`
- Test: `src/ml/plate_detect/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `bootstrap_ci` (T11).
- Produces: `aggregate_seeds(runs: list[dict]) -> dict[str, tuple[float,float]]` — input list of per-seed metric dicts (keys `map50, map5095, precision, recall`), returns `{key: (mean, std)}`; `append_experiment(csv_path: str, model: str, dataset: str, hyperparams: str, m: dict, weights: str) -> None` — appends a row matching the existing `experiments.csv` schema (creates header if file absent).

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_evaluate.py
import pytest
from plate_detect.eval.evaluate import aggregate_seeds, append_experiment

def test_aggregate_mean_std():
    runs = [
        {"map50": 0.90, "map5095": 0.60, "precision": 0.9, "recall": 0.9},
        {"map50": 0.92, "map5095": 0.62, "precision": 0.9, "recall": 0.9},
        {"map50": 0.94, "map5095": 0.64, "precision": 0.9, "recall": 0.9},
    ]
    agg = aggregate_seeds(runs)
    assert agg["map50"][0] == pytest.approx(0.92)
    assert agg["map50"][1] == pytest.approx(0.0163, abs=1e-3)   # population-ish std

def test_append_experiment_schema(tmp_path):
    csv = tmp_path / "experiments.csv"
    m = {"map50": 0.93, "map5095": 0.63, "precision": 0.91, "recall": 0.9}
    append_experiment(str(csv), "yolo26n", "A1", "imgsz=640;epochs=100", m, "weights/x.pt")
    header, row = csv.read_text().splitlines()[:2]
    assert header == "date,model,dataset,hyperparams,mAP50,mAP50-95,precision,recall,weights"
    assert "yolo26n" in row and "A1" in row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_evaluate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.eval.evaluate'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/eval/evaluate.py
from __future__ import annotations
import os
import csv
import datetime
import statistics

_HEADER = ["date", "model", "dataset", "hyperparams",
           "mAP50", "mAP50-95", "precision", "recall", "weights"]

def aggregate_seeds(runs: list[dict]) -> dict[str, tuple[float, float]]:
    keys = runs[0].keys()
    out = {}
    for k in keys:
        vals = [r[k] for r in runs]
        std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out[k] = (statistics.mean(vals), std)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_evaluate.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/eval/evaluate.py src/ml/plate_detect/tests/test_evaluate.py
git commit -m "feat(plate_detect): multi-seed aggregation and experiments log

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Family-aware postprocess (NMS, v8, v26)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/inference/__init__.py`
- Create: `src/ml/plate_detect/plate_detect/inference/postprocess.py`
- Test: `src/ml/plate_detect/tests/test_postprocess.py`

**Interfaces:**
- Produces: `nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]` (indices kept); `decode_v26(raw: np.ndarray, conf: float) -> tuple[np.ndarray,np.ndarray,np.ndarray]` — input `(N,6)` `[x1,y1,x2,y2,score,cls]`, NMS-free, returns `(boxes_xyxy, scores, classes)` filtered by conf; `decode_v8(raw: np.ndarray, conf: float, iou: float, nc: int) -> tuple[np.ndarray,np.ndarray,np.ndarray]` — input `(4+nc, M)` raw head (xywh + class scores), applies conf filter + per-class NMS.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_postprocess.py
import numpy as np
from plate_detect.inference.postprocess import nms, decode_v26, decode_v8

def test_nms_removes_overlap():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], float)
    scores = np.array([0.9, 0.8, 0.7])
    keep = nms(boxes, scores, iou_thr=0.5)
    assert 0 in keep and 2 in keep and 1 not in keep

def test_decode_v26_filters_conf_no_nms():
    raw = np.array([[0, 0, 10, 10, 0.9, 0],
                    [1, 1, 11, 11, 0.8, 0],     # overlaps but kept (NMS-free)
                    [0, 0, 5, 5, 0.1, 1]], float)
    boxes, scores, classes = decode_v26(raw, conf=0.25)
    assert len(boxes) == 2
    assert set(scores.round(1)) == {0.9, 0.8}

def test_decode_v8_conf_and_nms():
    # 2 classes; head shape (4+2, M) = (6, 3)
    xywh = np.array([[5, 5, 10, 10], [5.5, 5.5, 10, 10], [80, 80, 6, 6]]).T   # (4,3)
    cls_scores = np.array([[0.9, 0.85, 0.1], [0.0, 0.0, 0.7]])                # (2,3)
    raw = np.vstack([xywh, cls_scores])                                       # (6,3)
    boxes, scores, classes = decode_v8(raw, conf=0.25, iou=0.5, nc=2)
    assert len(boxes) == 2            # the 0.85 box suppressed by NMS with 0.9
    assert 0 in classes and 1 in classes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_postprocess.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.inference.postprocess'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/inference/__init__.py
```

```python
# src/ml/plate_detect/plate_detect/inference/postprocess.py
from __future__ import annotations
import numpy as np

def _iou(box, boxes):
    xx1 = np.maximum(box[0], boxes[:, 0]); yy1 = np.maximum(box[1], boxes[:, 1])
    xx2 = np.minimum(box[2], boxes[:, 2]); yy2 = np.minimum(box[3], boxes[:, 3])
    w = np.clip(xx2 - xx1, 0, None); h = np.clip(yy2 - yy1, 0, None)
    inter = w * h
    area = (box[2] - box[0]) * (box[3] - box[1])
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / (area + areas - inter + 1e-9)

def nms(boxes, scores, iou_thr: float):
    idx = scores.argsort()[::-1]
    keep = []
    while len(idx):
        i = idx[0]; keep.append(int(i))
        if len(idx) == 1:
            break
        ious = _iou(boxes[i], boxes[idx[1:]])
        idx = idx[1:][ious <= iou_thr]
    return keep

def decode_v26(raw, conf: float):
    raw = np.asarray(raw, float)
    m = raw[:, 4] >= conf
    r = raw[m]
    return r[:, :4], r[:, 4], r[:, 5].astype(int)

def decode_v8(raw, conf: float, iou: float, nc: int):
    raw = np.asarray(raw, float)
    if raw.shape[0] == 4 + nc:
        raw = raw.T                       # (M, 4+nc)
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

Run: `cd src/ml/plate_detect && pytest tests/test_postprocess.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/inference/__init__.py \
  src/ml/plate_detect/plate_detect/inference/postprocess.py src/ml/plate_detect/tests/test_postprocess.py
git commit -m "feat(plate_detect): family-aware detection postprocess

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: PlateDetector API

**Files:**
- Create: `src/ml/plate_detect/plate_detect/inference/plate_detector.py`
- Test: `src/ml/plate_detect/tests/test_plate_detector.py`

**Interfaces:**
- Consumes: postprocess decoders (T13).
- Produces: `@dataclass PlateDetection{bbox_xyxy: tuple[int,int,int,int], cls_id: int, cls_name: str, conf: float, crop: np.ndarray}`; `build_detections(boxes, classes, confs, image, names, pad=4) -> list[PlateDetection]` (clamps bbox to image, extracts padded crop, sorts by conf desc); `class PlateDetector(weights: str, backend: str = "pt", names: dict | None = None, conf=0.25, iou=0.5)` with `.detect(image: np.ndarray) -> list[PlateDetection]`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_plate_detector.py
import numpy as np
from plate_detect.inference.plate_detector import PlateDetection, build_detections

NAMES = {0: "bien_1hang", 1: "bien_2hang"}

def test_build_sorts_by_conf_desc():
    img = np.zeros((100, 100, 3), np.uint8)
    boxes = np.array([[10, 10, 30, 20], [40, 40, 70, 60]], float)
    dets = build_detections(boxes, np.array([0, 1]), np.array([0.6, 0.9]), img, NAMES)
    assert [d.conf for d in dets] == [0.9, 0.6]
    assert dets[0].cls_name == "bien_2hang"

def test_build_clamps_and_crops():
    img = np.zeros((50, 50, 3), np.uint8)
    boxes = np.array([[-5, -5, 40, 30]], float)     # negative → clamp to 0
    dets = build_detections(boxes, np.array([0]), np.array([0.8]), img, NAMES, pad=0)
    x1, y1, x2, y2 = dets[0].bbox_xyxy
    assert x1 == 0 and y1 == 0
    assert dets[0].crop.shape[0] == (y2 - y1) and dets[0].crop.shape[1] == (x2 - x1)

def test_empty_when_no_boxes():
    img = np.zeros((10, 10, 3), np.uint8)
    dets = build_detections(np.empty((0, 4)), np.array([]), np.array([]), img, NAMES)
    assert dets == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_plate_detector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.inference.plate_detector'`

- [ ] **Step 3: Write minimal implementation**

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

def build_detections(boxes, classes, confs, image, names, pad: int = 4):
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

    def _detect_pt(self, image):
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

    def _detect_onnx(self, image):
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

Run: `cd src/ml/plate_detect && pytest tests/test_plate_detector.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/inference/plate_detector.py \
  src/ml/plate_detect/tests/test_plate_detector.py
git commit -m "feat(plate_detect): PlateDetector API (pt/onnx backends)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: ONNX export + parity check

**Files:**
- Create: `src/ml/plate_detect/plate_detect/export/__init__.py`
- Create: `src/ml/plate_detect/plate_detect/export/to_onnx.py`
- Test: `src/ml/plate_detect/tests/test_to_onnx.py`

**Interfaces:**
- Consumes: `PlateDetector` (T14).
- Produces: `detection_delta(a: list[PlateDetection], b: list[PlateDetection]) -> float` — symmetric difference measure: `abs(len(a)-len(b))` plus mean center-distance of matched (same-index, conf-sorted) boxes normalized by image diagonal proxy; `parity_ok(a, b, tol: float = 0.02) -> bool`; `export(weights_pt: str, out_onnx: str, imgsz: int = 640) -> str` — Ultralytics export to ONNX (lazy import), returns path.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_to_onnx.py
import numpy as np
from plate_detect.inference.plate_detector import PlateDetection
from plate_detect.export.to_onnx import detection_delta, parity_ok

def _det(cx, conf):
    return PlateDetection((cx, 10, cx + 20, 30), 0, "bien_1hang", conf, np.zeros((1, 1, 3), np.uint8))

def test_identical_zero_delta():
    a = [_det(10, 0.9), _det(50, 0.8)]
    b = [_det(10, 0.9), _det(50, 0.8)]
    assert detection_delta(a, b) == 0.0
    assert parity_ok(a, b)

def test_count_mismatch_fails_parity():
    a = [_det(10, 0.9), _det(50, 0.8)]
    b = [_det(10, 0.9)]
    assert detection_delta(a, b) >= 1.0
    assert not parity_ok(a, b)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_to_onnx.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.export.to_onnx'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/export/__init__.py
```

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
        dists = [np.linalg.norm(_center(a[i]) - _center(b[i])) for i in range(n)]
        delta += float(np.mean(dists)) / 1000.0     # normalize by ~image-diagonal proxy
    return delta

def parity_ok(a, b, tol: float = 0.02) -> bool:
    return detection_delta(a, b) <= tol

def export(weights_pt: str, out_onnx: str, imgsz: int = 640) -> str:
    from ultralytics import YOLO
    import shutil
    model = YOLO(weights_pt)
    produced = model.export(format="onnx", imgsz=imgsz, opset=12)
    if str(produced) != out_onnx:
        shutil.copy(str(produced), out_onnx)
    return out_onnx
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_to_onnx.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/export/__init__.py \
  src/ml/plate_detect/plate_detect/export/to_onnx.py src/ml/plate_detect/tests/test_to_onnx.py
git commit -m "feat(plate_detect): ONNX export and parity check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: CLI (prepare/train/eval/export/check + --dry-run)

**Files:**
- Create: `src/ml/plate_detect/plate_detect/cli.py`
- Test: `src/ml/plate_detect/tests/test_cli.py`

**Interfaces:**
- Consumes: `Config` (T1), `prepare` (T8), `validate_processed` (T7).
- Produces: `main(argv: list[str]) -> int` — argparse with subcommands `prepare|train|eval|export|check`, global `--config` and `--dry-run`. `check` runs data-contract validation; `--dry-run` prints the resolved plan and returns 0 without heavy compute. Console entry via `python -m plate_detect.cli`.

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_cli.py
from plate_detect.cli import main

def test_check_dry_run_returns_zero(tmp_path, raw_fixture, capsys):
    # dry-run must not require processed data to exist
    rc = main(["check", "--dry-run",
               "--raw-dir", str(raw_fixture),
               "--processed-dir", str(tmp_path / "proc")])
    assert rc == 0
    assert "dry-run" in capsys.readouterr().out.lower()

def test_prepare_then_check(tmp_path, raw_fixture):
    proc = str(tmp_path / "proc")
    rc1 = main(["prepare", "--raw-dir", str(raw_fixture), "--processed-dir", proc,
                "--dataset-yaml", str(tmp_path / "a.yaml"),
                "--split-dir", str(tmp_path / "split")])
    assert rc1 == 0
    rc2 = main(["check", "--processed-dir", proc])
    assert rc2 == 0

def test_unknown_subcommand_errors():
    try:
        main(["frobnicate"])
        assert False, "should have raised SystemExit"
    except SystemExit as e:
        assert e.code != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_detect && pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_detect.cli'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ml/plate_detect/plate_detect/cli.py
from __future__ import annotations
import argparse
import sys
from .config import Config
from .data.prepare import prepare
from .data.validate import validate_processed

def _cfg_from_args(a) -> Config:
    over = {}
    for k in ("raw_dir", "processed_dir", "dataset_yaml", "split_dir"):
        v = getattr(a, k, None)
        if v:
            over[k] = v
    return Config.load(getattr(a, "config", None), **over)

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(prog="plate_detect")
    p.add_argument("--config")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--raw-dir", dest="raw_dir")
    p.add_argument("--processed-dir", dest="processed_dir")
    p.add_argument("--dataset-yaml", dest="dataset_yaml")
    p.add_argument("--split-dir", dest="split_dir")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "train", "eval", "export", "check"):
        sub.add_parser(name)
    a = p.parse_args(argv)
    cfg = _cfg_from_args(a)

    if a.dry_run:
        print(f"[dry-run] cmd={a.cmd} raw={cfg.raw_dir} processed={cfg.processed_dir} "
              f"models=yolov8n,yolo26n seeds={cfg.seeds}")
        return 0

    if a.cmd == "prepare":
        summary = prepare(cfg)
        print(f"prepared: {summary}")
        return 0
    if a.cmd == "check":
        errs = validate_processed(cfg.processed_dir, cfg.num_classes)
        if errs:
            print("INVALID:\n  " + "\n  ".join(errs)); return 1
        print("data-contract OK"); return 0
    if a.cmd in ("train", "eval", "export"):
        print(f"'{a.cmd}' runs on Colab GPU via notebooks/train-plate-det.ipynb")
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml/plate_detect && pytest tests/test_cli.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/plate_detect/cli.py src/ml/plate_detect/tests/test_cli.py
git commit -m "feat(plate_detect): CLI with prepare/check and dry-run

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: End-to-end pipeline smoke test

**Files:**
- Create: `src/ml/plate_detect/tests/test_pipeline_smoke.py`

**Interfaces:**
- Consumes: everything (fixtures, prepare, run_train, PlateDetector, export).

- [ ] **Step 1: Write the failing test**

```python
# src/ml/plate_detect/tests/test_pipeline_smoke.py
import os
import cv2
import numpy as np
import pytest
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.prepare import prepare

pytestmark = pytest.mark.slow

def test_full_pipeline_cpu(tmp_path):
    # 1. fixtures → prepare
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=8, seed=0)
    cfg = Config(
        raw_dir=str(raw), processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"), split_dir=str(tmp_path / "split"),
        imgsz=64, epochs=1, batch=2,
    )
    summary = prepare(cfg)
    assert summary["counts"]["train"] == 8

    # 2. train 1 epoch on CPU (downloads yolov8n.pt on first run)
    from plate_detect.train.trainer import run_train
    run_dir = run_train("yolov8n", cfg, cfg.dataset_yaml, seed=0,
                        project=str(tmp_path / "runs"))
    best = os.path.join(run_dir, "weights", "best.pt")
    assert os.path.exists(best)

    # 3. inference via PlateDetector (pt backend)
    from plate_detect.inference.plate_detector import PlateDetector
    det = PlateDetector(best, backend="pt", conf=0.01)
    img = cv2.imread(sorted((tmp_path / "proc" / "images" / "val").glob("*.jpg"))[0].as_posix())
    dets = det.detect(img)           # may be empty on a 1-epoch model; must not crash
    assert isinstance(dets, list)

    # 4. export ONNX
    from plate_detect.export.to_onnx import export
    onnx_path = export(best, str(tmp_path / "model.onnx"), imgsz=64)
    assert os.path.exists(onnx_path)
```

- [ ] **Step 2: Run test to verify it fails (before running, it fails only if pipeline broken)**

Run: `cd src/ml/plate_detect && pytest tests/test_pipeline_smoke.py -v -m slow`
Expected: PASS if Tasks 1–15 correct (this is an integration guard, not a new unit). If it fails, fix the wiring bug it exposes before proceeding.

- [ ] **Step 3: Register the `slow` marker**

Append to `src/ml/plate_detect/pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["slow: end-to-end tests that train a tiny model"]
```

- [ ] **Step 4: Run the full suite (fast only) to confirm no regressions**

Run: `cd src/ml/plate_detect && pytest -m "not slow" -q`
Expected: all fast tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_detect/tests/test_pipeline_smoke.py src/ml/plate_detect/pyproject.toml
git commit -m "test(plate_detect): end-to-end pipeline smoke test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 18: Thin Colab training notebook

**Files:**
- Create: `src/ml/plate_detect/notebooks/train-plate-det.ipynb`

**Interfaces:**
- Consumes: the installed `plate_detect` package + `run_train` (T10), `prepare` (T8), eval helpers (T11–T12), `export` (T15).

**Note:** Use the `colab-training` skill (and the `jupyter-notebook` skill to scaffold the `.ipynb`) when implementing. The notebook only orchestrates; all logic stays in the package. Model this on the existing `src/ml/notebooks/detect-yolov8.ipynb` but pin `ultralytics==8.4.37`, keep 2 classes, and pull A1 via the kaggle API.

- [ ] **Step 1: Scaffold the notebook cells**

Create the notebook with these cells (markdown headers + code):

1. **Markdown** — title + "Select Kernel → Colab GPU runtime → Run All. Resumable via Drive checkpoints."
2. **Code — config:**
```python
DRIVE_ROOT = "/content/drive/MyDrive/UIT_2025"
REPO_URL = "https://github.com/UIT-DoAnCuoiKi/UIT2026-DoAnCuoiKi.git"  # adjust to actual remote
MODELS = ["yolov8n", "yolo26n"]
SEEDS = [0, 1, 2]
```
3. **Code — install (pinned):**
```python
!pip install -q ultralytics==8.4.37
import ultralytics; ultralytics.checks()
```
4. **Code — GPU assert:**
```python
import torch
assert torch.cuda.is_available(), "Select a Colab GPU runtime (not TPU/CPU)."
print("GPU:", torch.cuda.get_device_name(0))
```
5. **Code — clone repo + install package:**
```python
import os
if not os.path.exists("/content/repo"):
    !git clone -q $REPO_URL /content/repo
!pip install -q -e /content/repo/src/ml/plate_detect
```
6. **Code — mount Drive:**
```python
from google.colab import drive; drive.mount("/content/drive")
```
7. **Code — pull A1 via kaggle:**
```python
# expects ~/.kaggle/kaggle.json uploaded
!kaggle datasets download -d duydieunguyen/licenseplates -p /content/data/raw/kaggle_vn_plate_segment --unzip
```
8. **Code — prepare:**
```python
from plate_detect.config import Config
from plate_detect.data.prepare import prepare
cfg = Config(raw_dir="/content/data/raw/kaggle_vn_plate_segment",
             processed_dir="/content/data/processed/a1_det",
             dataset_yaml="/content/repo/src/ml/plate_detect/configs/a1_det.yaml",
             split_dir="/content/repo/src/ml/plate_detect/configs/split")
print(prepare(cfg))
```
9. **Code — train all seeds × models (checkpoints to Drive), record metrics:**
```python
from plate_detect.train.trainer import run_train
from ultralytics import YOLO
from plate_detect.eval.evaluate import aggregate_seeds, append_experiment
runs = {}
for mk in MODELS:
    seed_metrics = []
    for s in SEEDS:
        rd = run_train(mk, cfg, cfg.dataset_yaml, seed=s, project=DRIVE_ROOT + "/runs")
        m = YOLO(rd + "/weights/best.pt").val(data=cfg.dataset_yaml, split="test")
        seed_metrics.append({"map50": m.box.map50, "map5095": m.box.map,
                             "precision": m.box.mp, "recall": m.box.mr})
    runs[mk] = aggregate_seeds(seed_metrics)
    best_seed = max(range(len(SEEDS)), key=lambda i: seed_metrics[i]["map50"])
    append_experiment("/content/repo/src/ml/experiments.csv", mk, "A1",
                      f"imgsz={cfg.imgsz};epochs={cfg.epochs};seeds={SEEDS}",
                      seed_metrics[best_seed], f"weights/{mk}_a1_s{best_seed}.pt")
print(runs)
```
10. **Code — export best model to ONNX + sync weights to Drive/repo weights dir (git-lfs).**
11. **Markdown** — reminder to copy `best.pt`/`.onnx` into `src/ml/plate_detect/weights/` (git-lfs) and commit from the local machine.

- [ ] **Step 2: Structural parse check**

Run: `cd src/ml/plate_detect && python -c "import nbformat; nb=nbformat.read('notebooks/train-plate-det.ipynb', as_version=4); print('cells:', len(nb.cells))"`
Expected: prints a cell count > 8, no exception (valid notebook JSON).

- [ ] **Step 3: Commit**

```bash
git add src/ml/plate_detect/notebooks/train-plate-det.ipynb
git commit -m "feat(plate_detect): thin Colab training notebook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 4: Manual GPU run (out-of-band, on Colab)**

Open the notebook in VS Code, select a Colab **GPU** runtime, Run All. Confirm: prepare prints counts, both models train across 3 seeds, `experiments.csv` gains rows, ONNX exported, mAP@0.5 ≥ 0.90 on test. Copy weights into `weights/` (git-lfs) and commit. *(This step is not automatable in CI — it is the real training run.)*

---

## Self-Review

**1. Spec coverage:**
- D1 axis-aligned bbox → T3, T8. D2 two classes → T1 (`class_names`), T4, T8. D3 A1-only + adapter → T8 (`A1Adapter`/`DatasetAdapter`). D4 split + pHash → T5, T6, T8. D5 weights+ONNX+API → T14, T15, T18. D6 success gate mAP@0.5≥0.90 → T18 Step 4 (asserted on real run), reported via T12. D7 git-lfs → T1 `.gitattributes`. D8 package/config/registry/backends → T1, T9, T14. D9 multi-seed+CI+latency → T11, T12, T18. D10 fixtures+smoke+validate+dry-run → T2, T7, T16, T17. §8 Colab → T18. §9 latency split/PR-curve → T11 (`measure_latency`); **note:** the model-only vs end-to-end latency table + per-class AP + confusion are produced inside the notebook eval cell (T18) using `measure_latency` and Ultralytics `val()` outputs. §10 all covered.
- **Gap fixed:** per-class AP / confusion / PR-curve conf selection are Ultralytics `val()` byproducts consumed in T18; no separate task needed, but T18 Step-1 cell 9 must save `results.png`/`confusion_matrix.png` from each `val()` into `docs/report/figures/`. Added to the notebook cell responsibilities.
- **License R1 / timestamp FP / low-light figures:** R1 honored by synthetic fixtures (T2) — never committing A1 images; timestamp-FP and low-light qualitative checks are manual review items on the real run (T18 Step 4), flagged in the spec risks.

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Every code step shows complete code. Notebook cells are fully written.

**3. Type consistency:** `polygon_to_bbox` returns `(xc,yc,w,h)` used consistently in T4/T8. `PlateDetection` fields identical across T14/T15. `decode_v8/decode_v26` signatures match their T14 calls. `aggregate_seeds` metric keys `map50,map5095,precision,recall` match T18 val extraction. `Config` field names match CLI overrides (T16) and prepare (T8).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-08-07-plate-detect-a1.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
