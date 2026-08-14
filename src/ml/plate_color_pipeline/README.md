# plate_color_pipeline

VN license-plate background-color classification + lighting handling.
Standalone, importable; consumes a BGR plate crop (e.g. `PlateDetection.crop`).

## Install

```bash
pip install -e .
```

Python ≥ 3.11. Key deps: `opencv-python-headless`, `numpy`.

## Use

```python
from plate_color import process_plate

a = process_plate(crop_bgr)   # crop_bgr: BGR np.ndarray

a.color        # white | yellow | blue | red | unknown
a.color_conf   # 0..1
a.lighting     # normal | low_light | overexposed | low_contrast | glare | degenerate
a.crop_for_ocr # enhanced crop to hand to OCR (same spatial size as input)
```

`process_plate` returns a `PlateAppearance` dataclass. `color_features` is also
available on it for debugging/retraining (raw HSV histogram stats).

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

```bash
plate_color "path/to/crops/**/*.jpg"    # prints color distribution
```

Accepts one or more glob patterns; expands recursively, skips non-image files.

## Tests

```bash
pytest          # 24 unit tests, fast (<1 s)
```

## Validation

Color validated against `plate_ocr_topkek` crops; see
`docs/superpowers/specs/2026-08-15-plate-color-lighting-design.md`.
