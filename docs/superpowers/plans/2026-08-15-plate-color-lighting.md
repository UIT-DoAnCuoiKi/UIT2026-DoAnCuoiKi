# Plate Color + Lighting Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standalone `plate_color_pipeline` package that classifies VN plate background color (HSV heuristic) and returns a lighting-enhanced crop for OCR, from a single plate crop.

**Architecture:** One-call `process_plate(crop_bgr)` runs two isolated paths — a hue-preserving path (CLAHE on V only, no white balance) feeds the color classifier; a full-enhance path (adaptive CLAHE + glare recovery + gray-world WB) produces the OCR crop. Color decision never sees WB, so WB cannot corrupt hue. HSV heuristic separates background from text by **area dominance**, handling both dark-on-light (white/yellow) and light-on-dark (blue/red) plates.

**Tech Stack:** Python 3.11+, numpy, opencv-python-headless, pytest. No ML training — pure CV heuristics.

## Global Constraints

- Package name: `plate_color`; directory `src/ml/plate_color_pipeline/` (mirrors `plate_detection_pipeline`).
- All modules start with `from __future__ import annotations`.
- Input crops are BGR `np.ndarray` (OpenCV convention), matching `PlateDetection.crop`.
- Color classes: `white`, `yellow`, `blue`, `red`, `unknown`. No `green`.
- Lighting conditions: `normal`, `low_light`, `overexposed`, `low_contrast`, `glare`, `degenerate`.
- HSV is OpenCV range: H 0–179, S 0–255, V 0–255.
- No persistence of plate crops (personal data — Luật BVDLCN). Module is pure in-memory transform; CLI writes only aggregate distributions.
- Every code step ships with its test; commit after each task.

---

## File Structure

```
src/ml/plate_color_pipeline/
  pyproject.toml                     # Task 1
  README.md                          # Task 7
  plate_color/
    __init__.py                      # Task 1 (exports), extended Task 5
    types.py                         # Task 1  — PlateAppearance
    color/
      __init__.py                    # Task 4
      thresholds.py                  # Task 4  — hue bands, cutoffs
      classifier.py                  # Task 4  — ColorResult, classify_color
    lighting/
      __init__.py                    # Task 2
      metrics.py                     # Task 2  — lighting_metrics, classify_lighting
      enhance.py                     # Task 3  — clahe_v, gamma, gray_world_wb, reduce_glare, enhance
    pipeline.py                      # Task 5  — process_plate
    cli.py                           # Task 6  — batch color distribution
  tests/
    synth.py                         # Task 2  — synthetic crop generators
    test_lighting_metrics.py         # Task 2
    test_lighting_enhance.py         # Task 3
    test_color_classifier.py         # Task 4
    test_pipeline.py                 # Task 5
    test_cli.py                      # Task 6
```

---

### Task 1: Package scaffold + `PlateAppearance` type

**Files:**
- Create: `src/ml/plate_color_pipeline/pyproject.toml`
- Create: `src/ml/plate_color_pipeline/plate_color/__init__.py`
- Create: `src/ml/plate_color_pipeline/plate_color/types.py`
- Test: `src/ml/plate_color_pipeline/tests/test_types_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  @dataclass
  class PlateAppearance:
      color: str            # white|yellow|blue|red|unknown
      color_conf: float
      color_features: dict
      lighting: str         # normal|low_light|overexposed|low_contrast|glare|degenerate
      crop_for_ocr: np.ndarray
  ```
  Importable as `from plate_color import PlateAppearance`.

- [ ] **Step 1: Write the failing test**

`src/ml/plate_color_pipeline/tests/test_types_smoke.py`:
```python
import numpy as np
from plate_color import PlateAppearance


def test_plate_appearance_fields():
    a = PlateAppearance("white", 0.9, {"k": 1}, "normal", np.zeros((4, 4, 3), np.uint8))
    assert a.color == "white"
    assert a.color_conf == 0.9
    assert a.lighting == "normal"
    assert a.crop_for_ocr.shape == (4, 4, 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_types_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_color'`

- [ ] **Step 3: Create the package files**

`src/ml/plate_color_pipeline/pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "plate_color"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "opencv-python-headless",
    "numpy",
]

[project.optional-dependencies]
dev = ["pytest"]

[project.scripts]
plate_color = "plate_color.cli:main"

[tool.setuptools.packages.find]
include = ["plate_color*"]
```

`src/ml/plate_color_pipeline/plate_color/types.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class PlateAppearance:
    color: str
    color_conf: float
    color_features: dict
    lighting: str
    crop_for_ocr: np.ndarray
```

`src/ml/plate_color_pipeline/plate_color/__init__.py`:
```python
from __future__ import annotations
from .types import PlateAppearance

__all__ = ["PlateAppearance"]
```

- [ ] **Step 4: Install package editable and run test**

Run: `cd src/ml/plate_color_pipeline && pip install -e . -q && python -m pytest tests/test_types_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_color_pipeline/pyproject.toml src/ml/plate_color_pipeline/plate_color/__init__.py src/ml/plate_color_pipeline/plate_color/types.py src/ml/plate_color_pipeline/tests/test_types_smoke.py
git commit -m "feat(plate_color): scaffold package + PlateAppearance type"
```

---

### Task 2: Lighting metrics + condition classifier

**Files:**
- Create: `src/ml/plate_color_pipeline/plate_color/lighting/__init__.py`
- Create: `src/ml/plate_color_pipeline/plate_color/lighting/metrics.py`
- Create: `src/ml/plate_color_pipeline/tests/synth.py`
- Test: `src/ml/plate_color_pipeline/tests/test_lighting_metrics.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `lighting_metrics(crop_bgr: np.ndarray) -> dict` with keys `mean_v, contrast, glare, shadow` (all `float`).
  - `classify_lighting(crop_bgr: np.ndarray) -> str` returning one of the 6 condition labels.
  - `tests/synth.py` helpers: `solid(bgr, size=(80,200))`, `plate_swatch(bg_bgr, text_bgr, size=(80,200))`, `dark_crop()`, `bright_crop()`, `low_contrast_crop()`, `glare_crop()`, `normal_crop()` — all return BGR `uint8` ndarrays.

- [ ] **Step 1: Write the synthetic generators**

`src/ml/plate_color_pipeline/tests/synth.py`:
```python
from __future__ import annotations
import numpy as np
import cv2


def solid(bgr, size=(80, 200)):
    h, w = size
    img = np.empty((h, w, 3), np.uint8)
    img[:] = bgr
    return img


def plate_swatch(bg_bgr, text_bgr, size=(80, 200)):
    img = solid(bg_bgr, size)
    cv2.putText(img, "51A-123", (8, size[0] // 2 + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_bgr, 3)
    return img


def dark_crop(size=(80, 200)):
    return solid((40, 40, 40), size)


def bright_crop(size=(80, 200)):
    return solid((230, 230, 230), size)


def low_contrast_crop(size=(80, 200)):
    img = solid((128, 128, 128), size)
    img[:, : size[1] // 2] = 140
    return img


def glare_crop(size=(80, 200)):
    img = solid((90, 90, 90), size)
    img[10:50, 10:70] = 255           # ~15% of pixels clipped
    return img


def normal_crop(size=(80, 200)):
    h, w = size
    row = np.linspace(60, 200, w).astype(np.uint8)
    gray = np.repeat(row[None, :], h, axis=0)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
```

- [ ] **Step 2: Write the failing test**

`src/ml/plate_color_pipeline/tests/test_lighting_metrics.py`:
```python
from plate_color.lighting.metrics import lighting_metrics, classify_lighting
from tests.synth import (dark_crop, bright_crop, low_contrast_crop,
                         glare_crop, normal_crop)


def test_metrics_keys():
    m = lighting_metrics(normal_crop())
    assert set(m) == {"mean_v", "contrast", "glare", "shadow"}


def test_conditions():
    assert classify_lighting(dark_crop()) == "low_light"
    assert classify_lighting(bright_crop()) == "overexposed"
    assert classify_lighting(low_contrast_crop()) == "low_contrast"
    assert classify_lighting(glare_crop()) == "glare"
    assert classify_lighting(normal_crop()) == "normal"


def test_degenerate():
    import numpy as np
    assert classify_lighting(np.zeros((4, 4, 3), np.uint8)) == "degenerate"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_lighting_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_color.lighting'`

- [ ] **Step 4: Implement**

`src/ml/plate_color_pipeline/plate_color/lighting/__init__.py`:
```python
```
(empty file)

`src/ml/plate_color_pipeline/plate_color/lighting/metrics.py`:
```python
from __future__ import annotations
import numpy as np
import cv2

GLARE_FRAC = 0.10          # frac of pixels with V >= 250
OVEREXP_MEAN = 200.0       # mean V above -> overexposed
LOWLIGHT_MEAN = 60.0       # mean V below -> low_light
LOWCONTRAST_RANGE = 50.0   # p95-p5 of V below -> low_contrast


def lighting_metrics(crop_bgr: np.ndarray) -> dict:
    v = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)[:, :, 2]
    p5, p95 = np.percentile(v, [5, 95])
    return {
        "mean_v": float(v.mean()),
        "contrast": float(p95 - p5),
        "glare": float(np.count_nonzero(v >= 250) / v.size),
        "shadow": float(np.count_nonzero(v <= 10) / v.size),
    }


def classify_lighting(crop_bgr: np.ndarray) -> str:
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return "degenerate"
    m = lighting_metrics(crop_bgr)
    if m["glare"] > GLARE_FRAC:
        return "glare"
    if m["mean_v"] > OVEREXP_MEAN:
        return "overexposed"
    if m["mean_v"] < LOWLIGHT_MEAN:
        return "low_light"
    if m["contrast"] < LOWCONTRAST_RANGE:
        return "low_contrast"
    return "normal"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_lighting_metrics.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/ml/plate_color_pipeline/plate_color/lighting/ src/ml/plate_color_pipeline/tests/synth.py src/ml/plate_color_pipeline/tests/test_lighting_metrics.py
git commit -m "feat(plate_color): lighting metrics + condition classifier"
```

---

### Task 3: Lighting enhancement stack

**Files:**
- Create: `src/ml/plate_color_pipeline/plate_color/lighting/enhance.py`
- Test: `src/ml/plate_color_pipeline/tests/test_lighting_enhance.py`

**Interfaces:**
- Consumes: `classify_lighting` from Task 2 (test uses synth crops).
- Produces:
  - `clahe_v(crop_bgr, clip=2.0, grid=8) -> np.ndarray` — CLAHE on V channel only, hue preserved.
  - `gamma(crop_bgr, g) -> np.ndarray` — `g>1` brightens, `g<1` darkens.
  - `gray_world_wb(crop_bgr) -> np.ndarray` — gray-world white balance.
  - `reduce_glare(crop_bgr) -> np.ndarray` — highlight rollback.
  - `enhance(crop_bgr, condition: str) -> np.ndarray` — full OCR-path enhance dispatched by condition.

- [ ] **Step 1: Write the failing test**

`src/ml/plate_color_pipeline/tests/test_lighting_enhance.py`:
```python
import numpy as np
import cv2
from plate_color.lighting.enhance import (clahe_v, gamma, gray_world_wb,
                                          enhance)
from tests.synth import dark_crop, bright_crop, low_contrast_crop


def _mean_v(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2].mean()


def _contrast(img):
    v = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2]
    p5, p95 = np.percentile(v, [5, 95])
    return p95 - p5


def test_clahe_v_preserves_hue():
    img = np.full((40, 60, 3), (30, 200, 220), np.uint8)   # yellow
    h_before = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 0]
    h_after = cv2.cvtColor(clahe_v(img), cv2.COLOR_BGR2HSV)[:, :, 0]
    assert np.abs(h_after.astype(int) - h_before.astype(int)).max() <= 2


def test_gamma_direction():
    img = np.full((10, 10, 3), 100, np.uint8)
    assert _mean_v(gamma(img, 1.6)) > 100
    assert _mean_v(gamma(img, 0.6)) < 100


def test_gray_world_neutralizes_cast():
    img = np.full((10, 10, 3), (200, 100, 50), np.uint8)   # strong cast
    out = gray_world_wb(img)
    ch = out.reshape(-1, 3).mean(axis=0)
    assert ch.max() - ch.min() < 10                        # channels equalized


def test_enhance_low_light_brightens():
    d = dark_crop()
    assert _mean_v(enhance(d, "low_light")) > _mean_v(d)


def test_enhance_overexposed_darkens():
    b = bright_crop()
    assert _mean_v(enhance(b, "overexposed")) < _mean_v(b)


def test_enhance_low_contrast_expands():
    lc = low_contrast_crop()
    assert _contrast(enhance(lc, "low_contrast")) >= _contrast(lc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_lighting_enhance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_color.lighting.enhance'`

- [ ] **Step 3: Implement**

`src/ml/plate_color_pipeline/plate_color/lighting/enhance.py`:
```python
from __future__ import annotations
import numpy as np
import cv2


def clahe_v(crop_bgr: np.ndarray, clip: float = 2.0, grid: int = 8) -> np.ndarray:
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    cl = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    hsv[:, :, 2] = cl.apply(hsv[:, :, 2])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def gamma(crop_bgr: np.ndarray, g: float) -> np.ndarray:
    lut = (np.linspace(0, 1, 256) ** (1.0 / g) * 255).clip(0, 255).astype(np.uint8)
    return cv2.LUT(crop_bgr, lut)


def gray_world_wb(crop_bgr: np.ndarray) -> np.ndarray:
    out = crop_bgr.astype(np.float32)
    means = out.reshape(-1, 3).mean(axis=0)
    k = float(means.mean())
    for i in range(3):
        out[:, :, i] *= k / (means[i] + 1e-6)
    return np.clip(out, 0, 255).astype(np.uint8)


def reduce_glare(crop_bgr: np.ndarray) -> np.ndarray:
    return gamma(crop_bgr, 0.7)


def enhance(crop_bgr: np.ndarray, condition: str) -> np.ndarray:
    out = crop_bgr
    if condition == "low_light":
        out = clahe_v(gamma(out, 1.6))
    elif condition == "low_contrast":
        out = clahe_v(out)
    elif condition == "overexposed":
        out = gamma(out, 0.7)
    elif condition == "glare":
        out = clahe_v(reduce_glare(out))
    # "normal" / "degenerate": no tone change
    return gray_world_wb(out)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_lighting_enhance.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_color_pipeline/plate_color/lighting/enhance.py src/ml/plate_color_pipeline/tests/test_lighting_enhance.py
git commit -m "feat(plate_color): lighting enhancement stack (CLAHE, gamma, WB, glare)"
```

---

### Task 4: HSV color classifier

**Files:**
- Create: `src/ml/plate_color_pipeline/plate_color/color/__init__.py`
- Create: `src/ml/plate_color_pipeline/plate_color/color/thresholds.py`
- Create: `src/ml/plate_color_pipeline/plate_color/color/classifier.py`
- Test: `src/ml/plate_color_pipeline/tests/test_color_classifier.py`

**Interfaces:**
- Consumes: `tests/synth.py` `plate_swatch`, `solid` from Task 2.
- Produces:
  - `ColorResult` dataclass with fields `color: str`, `conf: float`, `features: dict`.
  - `classify_color(crop_bgr: np.ndarray) -> ColorResult`.
  - `thresholds` module with the band/cutoff constants (single tuning surface).

- [ ] **Step 1: Write the failing test**

`src/ml/plate_color_pipeline/tests/test_color_classifier.py`:
```python
import numpy as np
from plate_color.color.classifier import classify_color, ColorResult
from tests.synth import plate_swatch, solid

WHITE_BG = (235, 235, 235); DARK = (20, 20, 20)
YELLOW_BG = (30, 200, 220)
BLUE_BG = (200, 60, 20); LIGHT = (240, 240, 240)
RED_BG = (30, 30, 200)


def test_white_dark_text():
    assert classify_color(plate_swatch(WHITE_BG, DARK)).color == "white"


def test_yellow_dark_text():
    assert classify_color(plate_swatch(YELLOW_BG, DARK)).color == "yellow"


def test_blue_light_text():          # light-on-dark: prototype failed here
    assert classify_color(plate_swatch(BLUE_BG, LIGHT)).color == "blue"


def test_red_light_text():           # light-on-dark: prototype failed here
    assert classify_color(plate_swatch(RED_BG, LIGHT)).color == "red"


def test_conf_in_range():
    r = classify_color(plate_swatch(YELLOW_BG, DARK))
    assert isinstance(r, ColorResult)
    assert 0.0 <= r.conf <= 1.0


def test_degenerate_returns_unknown():
    assert classify_color(np.zeros((4, 4, 3), np.uint8)).color == "unknown"


def test_dark_crop_unknown():        # mostly-dark, nothing classifiable
    assert classify_color(solid((10, 10, 10))).color == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_color_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_color.color'`

- [ ] **Step 3: Implement thresholds + classifier**

`src/ml/plate_color_pipeline/plate_color/color/__init__.py`:
```python
```
(empty file)

`src/ml/plate_color_pipeline/plate_color/color/thresholds.py`:
```python
from __future__ import annotations

# OpenCV HSV: H 0-179, S 0-255, V 0-255
WHITE_SAT_MAX = 55         # below -> low-saturation (white/gray candidate)
WHITE_VAL_MIN = 110        # above -> bright enough to be white
SAT_MIN_FOR_HUE = 55       # at/above -> saturated colored pixel

# hue bands (red wraps around 0/179)
HUE_RED_HI = 12            # H < 12 -> red
HUE_RED_WRAP = 160         # H >= 160 -> red
HUE_YELLOW_LO = 12
HUE_YELLOW_HI = 35
HUE_BLUE_LO = 85
HUE_BLUE_HI = 140

MIN_CONSIDERED_FRAC = 0.15  # classifiable pixels below this frac -> unknown
CONF_FLOOR = 0.35           # winning-cluster share below this -> unknown
```

`src/ml/plate_color_pipeline/plate_color/color/classifier.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import cv2
from . import thresholds as T


@dataclass
class ColorResult:
    color: str
    conf: float
    features: dict


def classify_color(crop_bgr: np.ndarray) -> ColorResult:
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return ColorResult("unknown", 0.0, {})
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    H = hsv[:, :, 0].astype(int); S = hsv[:, :, 1]; V = hsv[:, :, 2]
    total = h * w
    sat = S >= T.SAT_MIN_FOR_HUE
    counts = {
        "white": int(np.count_nonzero((S < T.WHITE_SAT_MAX) & (V >= T.WHITE_VAL_MIN))),
        "red": int(np.count_nonzero(sat & ((H < T.HUE_RED_HI) | (H >= T.HUE_RED_WRAP)))),
        "yellow": int(np.count_nonzero(sat & (H >= T.HUE_YELLOW_LO) & (H < T.HUE_YELLOW_HI))),
        "blue": int(np.count_nonzero(sat & (H >= T.HUE_BLUE_LO) & (H < T.HUE_BLUE_HI))),
    }
    considered = sum(counts.values())
    features = {"counts": counts, "considered_frac": considered / total}
    if considered < T.MIN_CONSIDERED_FRAC * total:
        return ColorResult("unknown", 0.0, features)
    color = max(counts, key=counts.get)
    conf = counts[color] / considered
    if conf < T.CONF_FLOOR:
        return ColorResult("unknown", conf, features)
    return ColorResult(color, conf, features)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_color_classifier.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_color_pipeline/plate_color/color/ src/ml/plate_color_pipeline/tests/test_color_classifier.py
git commit -m "feat(plate_color): HSV color classifier (area-dominant bg, handles light-on-dark)"
```

---

### Task 5: Split-path pipeline orchestration

**Files:**
- Create: `src/ml/plate_color_pipeline/plate_color/pipeline.py`
- Modify: `src/ml/plate_color_pipeline/plate_color/__init__.py` (export `process_plate`)
- Test: `src/ml/plate_color_pipeline/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `clahe_v`, `gray_world_wb`, `enhance` (Task 3); `classify_color` (Task 4); `classify_lighting` (Task 2); `PlateAppearance` (Task 1).
- Produces: `process_plate(crop_bgr: np.ndarray) -> PlateAppearance`, exported as `from plate_color import process_plate`.

- [ ] **Step 1: Write the failing test**

`src/ml/plate_color_pipeline/tests/test_pipeline.py`:
```python
import numpy as np
from plate_color import process_plate, PlateAppearance
from plate_color.color.classifier import classify_color
from plate_color.lighting.enhance import gray_world_wb
from tests.synth import plate_swatch, dark_crop, solid

YELLOW_BG = (30, 200, 220); DARK = (20, 20, 20)


def test_returns_plate_appearance():
    a = process_plate(plate_swatch(YELLOW_BG, DARK))
    assert isinstance(a, PlateAppearance)
    assert a.color == "yellow"
    assert a.crop_for_ocr.shape == plate_swatch(YELLOW_BG, DARK).shape


def test_lighting_label_flows_through():
    assert process_plate(dark_crop()).lighting == "low_light"


def test_degenerate_input():
    tiny = np.zeros((4, 4, 3), np.uint8)
    a = process_plate(tiny)
    assert a.color == "unknown"
    assert a.lighting == "degenerate"
    assert a.crop_for_ocr is tiny            # original returned untouched


def test_wb_isolated_from_color():
    # WB collapses a solid yellow toward gray -> would misclassify,
    # but process_plate classifies on the pre-WB (hue-preserving) path.
    yellow = plate_swatch(YELLOW_BG, DARK)
    assert process_plate(yellow).color == "yellow"
    assert classify_color(gray_world_wb(solid(YELLOW_BG))).color != "yellow"


def test_deterministic():
    crop = plate_swatch(YELLOW_BG, DARK)
    a, b = process_plate(crop), process_plate(crop)
    assert a.color == b.color and a.color_conf == b.color_conf
    assert np.array_equal(a.crop_for_ocr, b.crop_for_ocr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ImportError: cannot import name 'process_plate'`

- [ ] **Step 3: Implement pipeline**

`src/ml/plate_color_pipeline/plate_color/pipeline.py`:
```python
from __future__ import annotations
import numpy as np
from .types import PlateAppearance
from .color.classifier import classify_color
from .lighting.metrics import classify_lighting
from .lighting.enhance import clahe_v, enhance


def process_plate(crop_bgr: np.ndarray) -> PlateAppearance:
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return PlateAppearance("unknown", 0.0, {}, "degenerate", crop_bgr)
    # path A — color: hue-preserving (CLAHE on V only, NO white balance)
    crop_a = clahe_v(crop_bgr)
    cr = classify_color(crop_a)
    # path B — OCR: full enhance (CLAHE + glare recovery + gray-world WB)
    cond = classify_lighting(crop_bgr)
    crop_b = enhance(crop_bgr, cond)
    return PlateAppearance(cr.color, cr.conf, cr.features, cond, crop_b)
```

`src/ml/plate_color_pipeline/plate_color/__init__.py` (replace contents):
```python
from __future__ import annotations
from .types import PlateAppearance
from .pipeline import process_plate

__all__ = ["PlateAppearance", "process_plate"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full suite**

Run: `cd src/ml/plate_color_pipeline && python -m pytest -q`
Expected: PASS (all tasks' tests green)

- [ ] **Step 6: Commit**

```bash
git add src/ml/plate_color_pipeline/plate_color/pipeline.py src/ml/plate_color_pipeline/plate_color/__init__.py src/ml/plate_color_pipeline/tests/test_pipeline.py
git commit -m "feat(plate_color): split-path process_plate orchestration"
```

---

### Task 6: CLI batch color distribution

**Files:**
- Create: `src/ml/plate_color_pipeline/plate_color/cli.py`
- Test: `src/ml/plate_color_pipeline/tests/test_cli.py`

**Interfaces:**
- Consumes: `process_plate` (Task 5).
- Produces:
  - `color_distribution(paths: list[str]) -> dict[str, int]` — counts per color label over readable images.
  - `main(argv: list[str] | None = None) -> int` — CLI entry: takes glob patterns, prints distribution, returns 0.

- [ ] **Step 1: Write the failing test**

`src/ml/plate_color_pipeline/tests/test_cli.py`:
```python
import cv2
from plate_color.cli import color_distribution, main
from tests.synth import plate_swatch

WHITE_BG = (235, 235, 235); DARK = (20, 20, 20)
YELLOW_BG = (30, 200, 220)


def test_color_distribution(tmp_path):
    p1 = tmp_path / "a.png"; p2 = tmp_path / "b.png"
    cv2.imwrite(str(p1), plate_swatch(WHITE_BG, DARK))
    cv2.imwrite(str(p2), plate_swatch(YELLOW_BG, DARK))
    dist = color_distribution([str(p1), str(p2)])
    assert dist["white"] == 1
    assert dist["yellow"] == 1


def test_main_runs(tmp_path, capsys):
    p = tmp_path / "a.png"
    cv2.imwrite(str(p), plate_swatch(WHITE_BG, DARK))
    rc = main([str(tmp_path / "*.png")])
    assert rc == 0
    assert "white" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plate_color.cli'`

- [ ] **Step 3: Implement CLI**

`src/ml/plate_color_pipeline/plate_color/cli.py`:
```python
from __future__ import annotations
import sys
import glob
import collections
import cv2
from .pipeline import process_plate

_EXT = (".jpg", ".jpeg", ".png")


def color_distribution(paths: list[str]) -> dict:
    cnt: collections.Counter = collections.Counter()
    for p in paths:
        if not p.lower().endswith(_EXT):
            continue
        im = cv2.imread(p)
        if im is None:
            continue
        cnt[process_plate(im).color] += 1
    return dict(cnt)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    files: list[str] = []
    for pat in argv:
        files += glob.glob(pat, recursive=True)
    dist = color_distribution(files)
    total = sum(dist.values()) or 1
    print(f"analyzed {sum(dist.values())} crops")
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        print(f"  {k:10s} {v:5d}  {100 * v / total:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/ml/plate_color_pipeline && python -m pytest tests/test_cli.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ml/plate_color_pipeline/plate_color/cli.py src/ml/plate_color_pipeline/tests/test_cli.py
git commit -m "feat(plate_color): CLI batch color distribution"
```

---

### Task 7: README + full-suite verification

**Files:**
- Create: `src/ml/plate_color_pipeline/README.md`

**Interfaces:**
- Consumes: whole package.
- Produces: usage docs. No code.

- [ ] **Step 1: Write README**

`src/ml/plate_color_pipeline/README.md`:
```markdown
# plate_color_pipeline

VN license-plate background-color classification + lighting handling.
Standalone, importable; consumes a BGR plate crop (e.g. `PlateDetection.crop`).

## Install

    pip install -e .

## Use

```python
from plate_color import process_plate
a = process_plate(crop_bgr)          # crop_bgr: BGR np.ndarray
a.color          # white | yellow | blue | red | unknown
a.color_conf     # 0..1
a.lighting       # normal | low_light | overexposed | low_contrast | glare | degenerate
a.crop_for_ocr   # enhanced crop to hand to OCR
```

## Design

Two isolated paths per call:
- **Color path** — CLAHE on the V channel only (hue preserved), then an HSV
  heuristic that separates background from text by **area dominance**, so it
  works for both dark-on-light (white/yellow) and light-on-dark (blue/red) plates.
- **OCR path** — adaptive CLAHE + glare recovery + gray-world white balance.

White balance runs only on the OCR path, so it can never corrupt the color
decision. Tune thresholds in `plate_color/color/thresholds.py` and
`plate_color/lighting/metrics.py`.

## CLI

    plate_color "path/to/crops/**/*.jpg"     # prints color distribution

## Validation

Color validated against `plate_ocr_topkek` crops; see
`docs/superpowers/specs/2026-08-15-plate-color-lighting-design.md`.
```

- [ ] **Step 2: Run the full suite**

Run: `cd src/ml/plate_color_pipeline && python -m pytest -q`
Expected: PASS (all tests across Tasks 1–6)

- [ ] **Step 3: Commit**

```bash
git add src/ml/plate_color_pipeline/README.md
git commit -m "docs(plate_color): package README"
```

---

## Follow-ups (not in this plan)

- **Report chapter** `docs/report/chapters/03-*.md` (color module + HSV/CLAHE method, color-accuracy table on a hand-verified ~200-crop topkek sample) — drafted via `thesis-writer` after code lands.
- **Threshold tuning** against real topkek crops via the CLI; adjust `thresholds.py` if the distribution drifts from the ~62/19/10/6 baseline.
- **Integration** into the ALPR pipeline (feed `PlateDetection.crop` → `process_plate` → OCR) — belongs to the `alpr-pipeline` integration phase.
```
