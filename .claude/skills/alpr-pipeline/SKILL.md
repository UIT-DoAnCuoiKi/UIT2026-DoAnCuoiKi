---
name: alpr-pipeline
description: Use when writing the recognition pipeline code — plate detection crops, skew correction, 2-row splitting, OCR integration, HSV plate-color classification, and the unified per-vehicle API — for the smart parking thesis.
---

# ALPR Pipeline

Integration code lives in `src/ml/pipeline/`. Consumes ONNX models from `src/ml/weights/`. This is the interface frozen before week-6 integration — changes after that need both students' agreement.

## Pipeline contract (the one API everything consumes)

```python
@dataclass
class VehicleRecord:
    plate_text: str          # normalized, e.g. "59A-123.45"; "" if unreadable
    plate_confidence: float  # min of detection and OCR confidence, 0..1
    vehicle_type: str        # "car" | "motorbike" | "truck" | "bus"
    plate_color: str         # "white" | "yellow" | "blue" | "red"
    evidence_jpeg: bytes     # full-scene image at capture time
    timestamp: datetime

def process_vehicle(image: np.ndarray) -> VehicleRecord: ...
```

One call per vehicle at the gate (stationary vehicle per scope — no tracking needed).

## Stage order

1. Vehicle + plate detection (YOLO ONNX) → largest-confidence vehicle box, plate box within it
2. Plate crop → skew correction: minAreaRect on plate contour, rotate to horizontal (cv2.warpAffine)
3. Row split: plate aspect ratio < ~2.0 ⇒ 2-row (motorbike) — split at horizontal projection-profile valley, OCR each row, join top+bottom
4. OCR (PaddleOCR) per row → concatenate
5. Format validation + normalization (below); on failure keep raw text, flag low confidence
6. Plate color: HSV classification on plate crop; CLAHE (on L channel of LAB) before HSV thresholds to handle lighting
7. Vehicle type: classifier on vehicle crop

## VN plate normalization

- Charset: A–Z (no I, O in series), 0–9. Common OCR confusions to correct by position — in numeric positions always resolve toward the digit (O→0, I→1, B→8, S→5, Z→2); in the series letter position resolve toward the letter (0→O is invalid since O never appears in series — prefer D or Q by visual similarity, flag low confidence).
- Patterns (validate after uppercase + strip separators):
  - Car (1-row): `^\d{2}[A-Z]\d{4,5}$` (e.g. 51A12345)
  - Motorbike (2-row): `^\d{2}[A-Z]\d{1}\d{4,5}$` (row1: province+series, row2: number). Note: the two digit groups collapse to `^\d{2}[A-Z]\d{5,6}$` when matching joined text; the split shown mirrors the physical row layout.
- Render normalized as `NNX-NNN.NN` (5-digit) or `NNX-NNNN` (4-digit) for display/storage.

## HSV color classes (starting thresholds — calibrate on own data, log final values for thesis)

- white: S < 40, V > 120 · yellow: H 20–35 · blue: H 95–130 · red: H < 10 or H > 160 (two ranges)
- Decide by majority of plate-crop pixels after CLAHE; record per-class accuracy per lighting condition.

## Testing

- Unit tests per stage with fixture images in `src/ml/pipeline/tests/fixtures/` (one clear + one hard case per: 1-row, 2-row, each color, low light).
- End-to-end test asserts full VehicleRecord on fixtures; latency measured here is the number `edge-deploy` benchmarks against.
