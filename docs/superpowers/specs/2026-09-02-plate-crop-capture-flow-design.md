# Plate crop in the capture flow — design

Date: 2026-09-02
Branch: feat/duc-dashboard-backend

## Problem

The recognition pipeline already crops each plate and produces a
color/lighting-processed crop (`appearance.crop_for_ocr` in the e2e notebook and
in `src/ml/pipeline/onnx_pipeline.py:178-179`), but the backend keeps only the
derived strings (plate text, color label, confidences) and the **origin full
frame**. The plate crop is discarded.

We want the backend to crop, color-process, persist **both the origin frame and
the color-processed plate crop**, return the crop to the gate UI for immediate
display, and show both images in the session detail view.

## Flow

```
UI full frame
  -> POST /captures/infer (or edge -> POST /captures)
  -> pipeline: detect plate -> color-process crop -> OCR
  -> persist: origin frame (encrypted) + plate crop (encrypted)
  -> return CaptureResponse { image_asset_id, plate_crop_asset_id, ... }
Gate result panel: show origin + cropped
Session detail (entry/exit reading): show origin + cropped
```

## Decisions

- **Crop variant:** the color-processed crop `appearance.crop_for_ocr` (plate
  region + CLAHE color/lighting processing). One crop persisted per reading. So
  "both" = origin frame + this crop. Raw `det.crop` is not persisted.
- **Delivery:** persist as an encrypted `ImageAsset` (same path as the origin
  frame), return its id. Not inline base64. Consistent with the data-privacy
  rule (plate images are personal data: encrypted at rest, audited fetch via
  `/images/{id}`, retention tied to exit).
- **Both capture paths:** the crop travels as base64 PNG inside the pipeline
  payload, so the same ingest code persists it for both the backend infer path
  and the edge path.
- **History scope:** session **detail** shows both images (per entry/exit
  reading) plus the live gate result. The sessions **list table** stays
  text-only.

## Changes

### 1. Pipeline — `src/ml/pipeline/onnx_pipeline.py`

`OnnxAlprPipeline.run()` adds a per-plate key `crop_proc_b64`: PNG-encoded,
base64 string of `appearance.crop_for_ocr`.

- Encode: `cv2.imencode(".png", appearance.crop_for_ocr)` -> bytes ->
  `base64.b64encode(...).decode("ascii")`. Typical size a few KB.
- The key is added alongside the existing plate fields. Pydantic on the backend
  and `json.dumps` on the edge both carry it with no further change.
- Keep the notebook untouched; the notebook is the reference, not a consumer.

### 2. Schema — `src/backend/app/schemas/capture.py`

- `PlateItem += crop_proc_b64: str | None = None`
- `CaptureResponse += plate_crop_asset_id: int | None = None`

### 3. Model + migration — `src/backend/app/models/plate_reading.py`

- `PlateReading += plate_crop_asset_id: Mapped[int | None]`, FK to
  `image_asset.id`, nullable.
- New alembic migration under `src/backend/alembic/versions/` adding the
  column. Backend tests build schema with `Base.metadata.create_all`, so they
  pick up the column automatically; the migration keeps real Postgres in sync.

### 4. Ingest — `src/backend/app/services/capture_ingest.py`

- After `select_representative(payload.plates)`, if the representative has
  `crop_proc_b64`: base64-decode -> `store_encrypted_image(db, crop_bytes,
  direction)` -> set `reading.plate_crop_asset_id = asset.id`.
- Before building `raw_pipeline_json`, strip `crop_proc_b64` from every plate so
  the image bytes are not duplicated into the JSON column. `raw_pipeline_json`
  keeps all other fields as today.
- `build_capture_response` includes `plate_crop_asset_id`.
- `gate_hub.publish({...})` includes `plate_crop_asset_id` so WS-delivered
  captures carry it too.

### 5. Retention — `src/backend/app/routers/sessions.py::_set_retention`

Also set `retention_delete_after` on the `plate_crop_asset_id` asset (loop over
both `image_asset_id` and `plate_crop_asset_id` of each reading). The crop is
personal data and must expire together with the origin frame.

### 6. Session detail — `src/backend/app/schemas/session.py` + `sessions.py`

- `ReadingBrief += plate_crop_asset_id: int | None = None`.
- `_reading_brief(...)` populates it from the reading.

### 7. Frontend

- `CaptureResponse` / `GateCapture` types gain `plate_crop_asset_id?: number |
  null`. Reading-brief type in the session-detail feature gains it too.
- `src/frontend/src/features/gate/recognition-result.tsx`: render a second
  `CapturePreview` for the crop (origin + cropped, stacked or side by side).
  Only render when `plate_crop_asset_id` is present.
- Session detail view: for entry/exit reading, show both the origin
  (`image_asset_id`) and the crop (`plate_crop_asset_id`) via `CapturePreview` +
  the existing `/images/{id}` encrypted fetch.

### 8. Edge worker — `src/edge/worker.py`

Runs the same `OnnxAlprPipeline.run()`, so its payload JSON gains
`crop_proc_b64` with no logic change. Verify the worker forwards the full plate
dict (does not filter to a known key set); adjust only if it strips unknown
keys.

## Units and boundaries

- Pipeline produces the crop bytes (as b64). It does not know about storage.
- `store_encrypted_image` persists any bytes encrypted; reused unchanged for the
  crop.
- `ingest_reading` is the single place that turns payload crops into a stored
  asset and links it to the reading — one path for both infer and edge.
- Frontend `CapturePreview` already resolves either a local URL or an
  `image_asset_id`; the crop reuses it with a different id.

## Testing

- **Pipeline smoke** (`src/ml/pipeline/tests/`, guarded by model availability
  like existing smoke tests): `run()` output plate dict has `crop_proc_b64` that
  base64-decodes and `cv2.imdecode`s to a non-empty image.
- **Ingest service** (`src/backend/tests/test_capture_ingest_service.py`):
  payload with `crop_proc_b64` -> `reading.plate_crop_asset_id` set, an encrypted
  asset written, `raw_pipeline_json` contains no `crop_proc_b64`. Payload without
  it -> `plate_crop_asset_id` is None.
- **Response/WS**: `CaptureResponse` and the gate_hub publish dict include
  `plate_crop_asset_id`.
- **Retention**: on exit, `_set_retention` sets `retention_delete_after` on the
  crop asset as well as the origin.
- **Frontend** (`recognition-result.test.tsx`): renders two previews when
  `plate_crop_asset_id` is present, one when it is not.

## Out of scope

- Thumbnails in the sessions list table rows.
- Persisting the raw `det.crop` in addition to the processed crop.
- Any change to OCR/color/detector model logic. This only threads an existing
  crop through storage and UI.
