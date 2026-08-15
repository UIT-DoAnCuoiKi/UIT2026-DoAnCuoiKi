# Plate Color + Lighting Handling — Design

**Date:** 2026-08-15
**Author:** Lê Quang Hoài Đức (25410034)
**Phase:** Week 3 (29/07–05/08 slot, Đức track) — plate color + HSV/CLAHE lighting
**Status:** Approved (brainstorming) → ready for implementation plan

## Purpose

Standalone, importable Python package that, given a plate crop (BGR `np.ndarray`
from `PlateDetection.crop`), returns:

1. **VN plate background color** class (HSV heuristic, no training).
2. **Lighting-enhanced crop for OCR** plus a lighting-condition label.

Reusable by the plate-detection pipeline now and by the workflow app later.

## Scope

**In:** HSV color classifier, full lighting stack (adaptive CLAHE + glare
recovery + gray-world white balance), split-path orchestration, CLI batch tool,
tests, README. Report chapter 03 drafted after code (separate, via thesis-writer).

**Out:** learned/CNN color model (HSV heuristic only this phase), OCR itself
(Nhật), detection (done), green/EV plate class (0.5% of real data — too rare).

## VN color taxonomy

`white` (personal), `yellow` (business/commercial, post-2020), `blue`
(government agency), `red` (military), `unknown` (low confidence / degenerate).

Note VN blue & red plates carry **light text on dark background**; white & yellow
carry **dark text on light background**. Background/text separation must handle
both directions.

## Datasets

- **Primary color validation — `plate_ocr_topkek`** (Kaggle topkek69): 6,643 real
  tight plate crops. Real HSV distribution already measured (`color_check.py`,
  599 crops): white 62.1%, yellow 19.2%, blue 9.5%, red 6.2%, green 0.5%,
  other 2.5%. All four kept classes present, incl. rare blue/red for the
  light-text-on-dark path.
- **Lighting robustness / layout — `plate_segment_duydieu`** (4,578 crops): wider
  framing, color contaminated by scene bg (84% white) → used for lighting-stack
  stress and as base images, NOT color ground truth.
- **No labeled color dataset exists.** Plan: weak-label topkek crops with the
  classifier, hand-verify a ~200-crop sample balanced across the 4 colors →
  that verified sample is the color-accuracy eval set for the report.
- **Skip:** duydieu as color truth (contaminated); green class (too rare).

Ref: `docs/research/2026-07-28-dataset-inventory-verified.md`.

## Package layout

Standalone, mirrors `src/ml/plate_detection_pipeline/` structure.

```
src/ml/plate_color_pipeline/
  pyproject.toml
  README.md
  plate_color/
    __init__.py          # exports: process_plate, PlateAppearance,
                         #          PlateColorClassifier, LightingEnhancer
    types.py             # PlateAppearance, ColorResult, LightingResult dataclasses
    color/
      classifier.py      # HSV heuristic: bg/text split by area, hue -> class
      thresholds.py      # tunable constants (hue bands, sat/val cutoffs)
    lighting/
      metrics.py         # brightness, contrast, glare/clip-ratio measures
      enhance.py         # adaptive CLAHE(V), glare recovery, gray-world WB
    pipeline.py          # process_plate(): split-path orchestration
    cli.py               # batch-classify a glob -> color distribution
  tests/
```

## Public API

```python
@dataclass
class PlateAppearance:
    color: str            # white | yellow | blue | red | unknown
    color_conf: float     # 0..1, fraction of pixels in winning bg cluster
    color_features: dict  # median H/S/V of bg cluster, bg pixel fraction (debug)
    lighting: str         # normal | low_light | overexposed | low_contrast |
                          # glare | degenerate
    crop_for_ocr: np.ndarray  # full-enhanced crop (CLAHE + glare + WB)

def process_plate(crop_bgr: np.ndarray) -> PlateAppearance: ...
```

`PlateColorClassifier` and `LightingEnhancer` are separately usable classes;
`process_plate` is the convenience one-call entry point.

## Data flow — split paths (one call)

The two paths are isolated so white balance never touches the color decision.

```
process_plate(crop_bgr):
  # path A — color (hue-preserving)
  crop_A  = CLAHE on V-channel only        # brightness normalize, hue intact, NO WB
  color   = classify_color(crop_A)         # area-dominant bg cluster -> hue band

  # path B — OCR (full enhance)
  cond    = lighting_metrics(crop_bgr)     # condition label
  crop_B  = enhance(crop_bgr, cond)        # adaptive CLAHE + glare recovery + gray-world WB

  return PlateAppearance(color, color_conf, color_features, cond, crop_B)
```

## Color heuristic (refined vs prototype)

The prototype (`docs/research/tools/color_check.py`) assumes
`background = brightest pixels`, which misclassifies blue/red plates
(light text on dark bg picks the text). Fix — separate by **area dominance**:

1. Convert to HSV.
2. Split candidate background vs text by clustering: low-saturation pixels
   (white/gray candidates) vs high-saturation pixels grouped by hue histogram.
   Background = the largest coherent cluster by pixel area (plate bg is majority
   area; text is minority) — works for both dark-on-light and light-on-dark.
3. If the low-sat cluster dominates and its median V is high → `white`.
4. Else the dominant saturated hue maps to a band → `red` / `yellow` / `blue`.
5. `color_conf` = winning-cluster pixel fraction; below a floor → `unknown`.

Hue bands, saturation/value cutoffs, and the confidence floor all live in
`color/thresholds.py` (single tuning surface).

## Lighting stack

- `metrics.py`: mean/percentile brightness, RMS/percentile contrast, clipped-
  highlight (glare) ratio, clipped-shadow ratio → derive `lighting` condition.
- `enhance.py`: gated by condition — CLAHE on the V channel for low-contrast /
  low-light; highlight rollback (tone-map / inpaint clipped regions) for glare /
  overexposed; gray-world white balance to remove color cast. Good crops
  (`normal`) pass through with minimal change.

## Error handling

Degenerate input (h or w < 8 px, empty, all-clipped) →
`color=unknown`, `lighting="degenerate"`, `crop_for_ocr = original crop`.
Entry validates dtype/shape; never raises on a valid BGR ndarray.

## Testing

- **Synthetic color swatches:** solid white/yellow/blue/red plates with
  contrasting text in BOTH directions (dark-on-light, light-on-dark) → assert
  correct class. Explicitly covers the prototype's blue/red failure.
- **Lighting synth:** dark / overexposed / low-contrast crops → assert correct
  condition label and that `enhance` moves brightness/contrast toward target.
- **Split-path invariant:** color classification identical with WB on vs off
  (proves WB isolated from the color decision).
- **Degenerate inputs:** tiny/empty/all-clipped → graceful `unknown` /
  `degenerate`, no raise.
- **Determinism:** same input → same output.
- **Real-crop smoke (CLI):** run over a topkek crop glob; distribution sanity-
  checked against the `color_check.py` baseline (~62/19/10/6).

## Report

Week-3 deliverable includes `docs/report/chapters/03-*.md` (color module +
HSV/CLAHE method, color-accuracy table on the hand-verified topkek sample).
Drafted after code via thesis-writer — folded into the implementation plan,
not this design.

## Data privacy

Plate crops are personal data (Luật BVDLCN, eff. 01/01/2026). This module is
pure transform in memory — no persistence. The CLI operates on already-local
research crops only and writes aggregate distributions, not per-plate records.
