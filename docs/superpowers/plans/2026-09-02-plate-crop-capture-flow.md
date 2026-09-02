# Plate crop in the capture flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist and return the color-processed plate crop alongside the origin frame, so the gate result and session detail show both images.

**Architecture:** The shared pipeline (`OnnxAlprPipeline.run`) emits the color-processed crop as base64 PNG inside the payload, so both the backend infer path and the edge path carry it. `ingest_reading` decodes the representative plate's crop, stores it as a second encrypted `ImageAsset`, and links it on the `PlateReading`. The response, WS event, and session-detail reading brief carry the new `plate_crop_asset_id`; the frontend reuses `CapturePreview`/`Evidence` to show origin + crop.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, Alembic, Pydantic v2, pytest (backend + ML); React, TypeScript, orval-generated API client, Vitest (frontend); OpenCV + numpy (ML).

## Global Constraints

- **No auto-commit** (user rule): every task ends by staging only (`git add ...`). Do NOT run `git commit` or `git push`. Leave changes staged for the user.
- **Plate crop is personal data**: store it only via `store_encrypted_image` (encrypted at rest); `retention_delete_after` must be set on the crop asset on exit, together with the origin frame.
- **Crop variant** is always `appearance.crop_for_ocr` (plate region + CLAHE color/lighting processing). The raw `det.crop` is not persisted.
- **Codegen order**: after any backend schema change, regenerate the OpenAPI file and the orval client before touching frontend code that consumes generated types (`cd src/backend && python scripts/export_openapi.py` then `cd src/frontend && npm run gen:api`).
- **Alembic head** is currently `b1c2d3e4f5a6`; the new migration's `down_revision` is `b1c2d3e4f5a6`.

---

### Task 1: Pipeline emits the color-processed crop as base64

**Files:**
- Modify: `src/ml/pipeline/onnx_pipeline.py` (add `encode_crop_b64`, wire into `run`)
- Test: `src/ml/pipeline/tests/test_crop_encode.py` (create)

**Interfaces:**
- Produces: `encode_crop_b64(crop_bgr: "np.ndarray") -> str` — PNG+base64 (ascii) of a BGR image, `""` on encode failure.
- Produces: each dict in `run(...)["plates"]` gains key `crop_proc_b64: str` (base64 PNG of `appearance.crop_for_ocr`).

- [ ] **Step 1: Write the failing test**

Create `src/ml/pipeline/tests/test_crop_encode.py`:

```python
import base64

import cv2
import numpy as np

from pipeline.onnx_pipeline import encode_crop_b64


def test_encode_crop_b64_round_trips_to_same_shape():
    crop = np.zeros((4, 8, 3), dtype=np.uint8)
    crop[:, :, 2] = 255  # red in BGR

    b64 = encode_crop_b64(crop)

    assert isinstance(b64, str) and b64
    raw = base64.b64decode(b64)
    decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape == (4, 8, 3)


def test_encode_crop_b64_empty_on_bad_input():
    assert encode_crop_b64(None) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/ml && python -m pytest pipeline/tests/test_crop_encode.py -v`
Expected: FAIL with `ImportError: cannot import name 'encode_crop_b64'`.

- [ ] **Step 3: Add the helper and wire it into `run`**

In `src/ml/pipeline/onnx_pipeline.py`, add near the top-level (after the imports block, before `class _OnnxCRNNRecognizer`):

```python
def encode_crop_b64(crop_bgr) -> str:
    """PNG-encode a BGR crop to a base64 ascii string. Returns "" on failure."""
    import base64

    import cv2

    if crop_bgr is None:
        return ""
    ok, buf = cv2.imencode(".png", crop_bgr)
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")
```

In `OnnxAlprPipeline.run`, inside the plate loop, add the crop field to the appended dict (the loop currently at lines ~177-189):

```python
        for det in self._plate_detector.detect(image_bgr):
            appearance = process_plate(det.crop)
            reading = read_plate(appearance.crop_for_ocr, self._ocr, layout=det.cls_name)
            result["plates"].append({
                "bbox": [float(v) for v in det.bbox_xyxy],
                "layout": det.cls_name,
                "det_conf": float(det.conf),
                "plate_text": reading.text_display,
                "plate_valid": bool(reading.valid_format),
                "ocr_conf": float(reading.confidence),
                "color": appearance.color,
                "color_conf": float(appearance.color_conf) if appearance.color_conf is not None else None,
                "crop_proc_b64": encode_crop_b64(appearance.crop_for_ocr),
            })
```

Also update the `run` docstring line listing per-plate keys to end with `..., color, color_conf, crop_proc_b64`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/ml && python -m pytest pipeline/tests/test_crop_encode.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Stage changes**

```bash
git add src/ml/pipeline/onnx_pipeline.py src/ml/pipeline/tests/test_crop_encode.py
```

---

### Task 2: Backend schema fields

**Files:**
- Modify: `src/backend/app/schemas/capture.py`
- Test: `src/backend/tests/test_capture_schema_crop.py` (create)

**Interfaces:**
- Consumes: `crop_proc_b64` key from Task 1 payload dicts.
- Produces: `PlateItem.crop_proc_b64: str | None`; `CaptureResponse.plate_crop_asset_id: int | None`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_capture_schema_crop.py`:

```python
from app.schemas.capture import CaptureResponse, PipelinePayload


def test_plate_item_accepts_crop_b64():
    p = PipelinePayload.model_validate(
        {"vehicle_type": "car",
         "plates": [{"det_conf": 0.9, "plate_text": "51F1", "crop_proc_b64": "QUJD"}]}
    )
    assert p.plates[0].crop_proc_b64 == "QUJD"


def test_capture_response_has_plate_crop_asset_id():
    r = CaptureResponse(reading_id=1, capture_id="c", direction="in",
                        review_state="confident", plate_crop_asset_id=7)
    assert r.plate_crop_asset_id == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_capture_schema_crop.py -v`
Expected: FAIL — `crop_proc_b64` dropped (attribute is `None`) / `plate_crop_asset_id` unexpected keyword.

- [ ] **Step 3: Add the fields**

In `src/backend/app/schemas/capture.py`, add to `PlateItem` (after `color_conf`):

```python
    crop_proc_b64: str | None = None
```

Add to `CaptureResponse` (after `image_asset_id`):

```python
    plate_crop_asset_id: int | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_capture_schema_crop.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Stage changes**

```bash
git add src/backend/app/schemas/capture.py src/backend/tests/test_capture_schema_crop.py
```

---

### Task 3: PlateReading column + Alembic migration

**Files:**
- Modify: `src/backend/app/models/plate_reading.py`
- Create: `src/backend/alembic/versions/c4d5e6f7a8b9_add_plate_crop_asset.py`
- Test: `src/backend/tests/test_plate_crop_column.py` (create)

**Interfaces:**
- Produces: `PlateReading.plate_crop_asset_id: Mapped[int | None]` (FK `image_asset.id`, nullable).

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_plate_crop_column.py`:

```python
from app.models import ImageAsset, PlateReading


def test_reading_can_link_a_plate_crop_asset(db_session):
    asset = ImageAsset(path="/x.enc", encrypted=True, sha256="a", direction="in")
    db_session.add(asset)
    db_session.flush()
    reading = PlateReading(
        capture_id="cap-crop", direction="in", review_state="confident",
        plate_crop_asset_id=asset.id,
    )
    db_session.add(reading)
    db_session.commit()
    db_session.refresh(reading)
    assert reading.plate_crop_asset_id == asset.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_plate_crop_column.py -v`
Expected: FAIL — `TypeError: 'plate_crop_asset_id' is an invalid keyword argument for PlateReading`.

- [ ] **Step 3: Add the column**

In `src/backend/app/models/plate_reading.py`, add after the `image_asset_id` line (31):

```python
    plate_crop_asset_id: Mapped[int | None] = mapped_column(ForeignKey("image_asset.id"), nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_plate_crop_column.py -v`
Expected: PASS (test uses `create_all`, so the new column exists).

- [ ] **Step 5: Add the Alembic migration**

Create `src/backend/alembic/versions/c4d5e6f7a8b9_add_plate_crop_asset.py`:

```python
"""add plate_reading.plate_crop_asset_id

Persist the color-processed plate crop as a second encrypted image asset,
linked from the reading. SQLite test suite uses create_all; this keeps
Postgres in sync.

Revision ID: c4d5e6f7a8b9
Revises: b1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plate_reading",
        sa.Column("plate_crop_asset_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_plate_reading_plate_crop_asset",
        "plate_reading", "image_asset",
        ["plate_crop_asset_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_plate_reading_plate_crop_asset", "plate_reading", type_="foreignkey")
    op.drop_column("plate_reading", "plate_crop_asset_id")
```

- [ ] **Step 6: Verify migration chain is linear**

Run: `cd src/backend && python -c "from alembic.config import Config; from alembic.script import ScriptDirectory; s=ScriptDirectory.from_config(Config('alembic.ini')); print(s.get_current_head())"`
Expected: prints `c4d5e6f7a8b9` (single head, no branch error).

- [ ] **Step 7: Stage changes**

```bash
git add src/backend/app/models/plate_reading.py \
        src/backend/alembic/versions/c4d5e6f7a8b9_add_plate_crop_asset.py \
        src/backend/tests/test_plate_crop_column.py
```

---

### Task 4: Ingest persists the crop, strips it from raw JSON, carries the id

**Files:**
- Modify: `src/backend/app/services/capture_ingest.py`
- Test: `src/backend/tests/test_capture_ingest_service.py` (extend)

**Interfaces:**
- Consumes: `PlateItem.crop_proc_b64` (Task 2), `PlateReading.plate_crop_asset_id` (Task 3), `store_encrypted_image` (existing).
- Produces: `reading.plate_crop_asset_id` set when the representative plate has a crop; `CaptureResponse.plate_crop_asset_id` populated; `gate_hub` event carries `plate_crop_asset_id`; `raw_pipeline_json` no longer contains `crop_proc_b64`.

- [ ] **Step 1: Write the failing tests**

Append to `src/backend/tests/test_capture_ingest_service.py`:

```python
# Valid 1x1 PNG (bytes content is irrelevant to storage; must be valid base64).
_CROP_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _payload_with_crop():
    return PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(bbox=[0, 0, 10, 10], layout="1", det_conf=0.9,
                          plate_text="51F12345", plate_valid=True, ocr_conf=0.95,
                          color="white", color_conf=0.9, crop_proc_b64=_CROP_B64)],
    )


def test_ingest_persists_plate_crop_asset(db_session):
    from app.models import ImageAsset
    from app.services.capture_ingest import build_capture_response, ingest_reading
    reading, _, _ = ingest_reading(
        db_session, capture_id="cap-crop-1", direction="in", lane=None,
        payload=_payload_with_crop(), image_bytes=b"frame",
    )
    assert reading.plate_crop_asset_id is not None
    assert reading.plate_crop_asset_id != reading.image_asset_id
    assert db_session.get(ImageAsset, reading.plate_crop_asset_id) is not None
    # crop bytes must not be duplicated into the JSON column
    for p in reading.raw_pipeline_json["plates"]:
        assert "crop_proc_b64" not in p
    resp = build_capture_response(reading, "51F12345", False)
    assert resp.plate_crop_asset_id == reading.plate_crop_asset_id


def test_ingest_without_crop_leaves_asset_null(db_session):
    from app.services.capture_ingest import ingest_reading
    reading, _, _ = ingest_reading(
        db_session, capture_id="cap-crop-2", direction="in", lane=None,
        payload=_payload(), image_bytes=b"frame",
    )
    assert reading.plate_crop_asset_id is None


def test_ingest_publishes_plate_crop_asset_id(db_session, monkeypatch):
    from app.services import capture_ingest
    published = {}
    monkeypatch.setattr(capture_ingest.gate_hub, "publish", lambda evt: published.update(evt))
    reading, _, _ = capture_ingest.ingest_reading(
        db_session, capture_id="cap-crop-3", direction="in", lane=None,
        payload=_payload_with_crop(), image_bytes=b"frame",
    )
    assert published["plate_crop_asset_id"] == reading.plate_crop_asset_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/backend && python -m pytest tests/test_capture_ingest_service.py -v`
Expected: the three new tests FAIL (`plate_crop_asset_id` is None / `crop_proc_b64` still present / KeyError on published dict).

- [ ] **Step 3: Implement the crop persistence**

In `src/backend/app/services/capture_ingest.py`:

Add `import base64` at the top.

In `build_capture_response`, add to the `CaptureResponse(...)` kwargs (after `image_asset_id=reading.image_asset_id`):

```python
        plate_crop_asset_id=reading.plate_crop_asset_id,
```

In `ingest_reading`, replace the body from `asset = store_encrypted_image(...)` through the `PlateReading(...)` construction with:

```python
    asset = store_encrypted_image(db, image_bytes, direction)
    rep = select_representative(payload.plates)
    plate_text = rep.plate_text if rep else None

    crop_asset_id = None
    if rep is not None and rep.crop_proc_b64:
        crop_asset = store_encrypted_image(db, base64.b64decode(rep.crop_proc_b64), direction)
        crop_asset_id = crop_asset.id

    raw = payload.model_dump()
    for p in raw.get("plates", []):
        p.pop("crop_proc_b64", None)

    reading = PlateReading(
        capture_id=capture_id,
        direction=direction,
        lane=lane,
        plate_text_ciphertext=crypto.encrypt_text(plate_text) if plate_text else None,
        plate_hash=plate_hash(plate_text) if plate_text else None,
        plate_valid=rep.plate_valid if rep else None,
        det_conf=rep.det_conf if rep else None,
        ocr_conf=rep.ocr_conf if rep else None,
        layout=rep.layout if rep else None,
        color=rep.color if rep else None,
        color_conf=rep.color_conf if rep else None,
        vehicle_type=payload.vehicle_type,
        vehicle_style=payload.vehicle_style,
        vehicle_style_conf=payload.vehicle_style_conf,
        raw_pipeline_json=raw,
        image_asset_id=asset.id,
        plate_crop_asset_id=crop_asset_id,
        review_state=compute_review_state(rep),
    )
```

In the `gate_hub.publish({...})` dict, add after `"image_asset_id": reading.image_asset_id,`:

```python
        "plate_crop_asset_id": reading.plate_crop_asset_id,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_capture_ingest_service.py -v`
Expected: PASS (all tests, including the original two).

- [ ] **Step 5: Stage changes**

```bash
git add src/backend/app/services/capture_ingest.py src/backend/tests/test_capture_ingest_service.py
```

---

### Task 5: Retention covers the crop asset

**Files:**
- Modify: `src/backend/app/routers/sessions.py` (`_set_retention`)
- Test: `src/backend/tests/test_retention_crop.py` (create)

**Interfaces:**
- Consumes: `PlateReading.plate_crop_asset_id` (Task 3).
- Produces: on exit, the crop asset's `retention_delete_after` is set alongside the origin frame's.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_retention_crop.py`:

```python
from app.clock import now_utc
from app.models import ImageAsset, PlateReading, ParkingSession
from app.routers.sessions import _set_retention


def test_set_retention_marks_crop_asset(db_session):
    origin = ImageAsset(path="/o.enc", encrypted=True, sha256="o", direction="out")
    crop = ImageAsset(path="/c.enc", encrypted=True, sha256="c", direction="out")
    db_session.add_all([origin, crop])
    db_session.flush()
    reading = PlateReading(
        capture_id="cap-ret", direction="out", review_state="confident",
        image_asset_id=origin.id, plate_crop_asset_id=crop.id,
    )
    db_session.add(reading)
    db_session.flush()
    session = ParkingSession(
        plate_hash="h", plate_ciphertext="x", vehicle_group="xe_may",
        status="completed", exit_time=now_utc(), exit_reading_id=reading.id,
    )
    db_session.add(session)
    db_session.flush()

    _set_retention(db_session, session)

    assert db_session.get(ImageAsset, crop.id).retention_delete_after is not None
    assert db_session.get(ImageAsset, origin.id).retention_delete_after is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_retention_crop.py -v`
Expected: FAIL — crop asset's `retention_delete_after` is still `None`.

- [ ] **Step 3: Extend `_set_retention`**

In `src/backend/app/routers/sessions.py`, replace the body of `_set_retention` with:

```python
def _set_retention(db: Session, session: ParkingSession) -> None:
    if session.exit_time is None:
        return
    delete_after = session.exit_time + timedelta(days=settings.retention_days)
    for rid in (session.entry_reading_id, session.exit_reading_id):
        if not rid:
            continue
        reading = db.get(PlateReading, rid)
        if not reading:
            continue
        for aid in (reading.image_asset_id, reading.plate_crop_asset_id):
            if not aid:
                continue
            asset = db.get(ImageAsset, aid)
            if asset:
                asset.retention_delete_after = delete_after
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_retention_crop.py -v`
Expected: PASS.

- [ ] **Step 5: Stage changes**

```bash
git add src/backend/app/routers/sessions.py src/backend/tests/test_retention_crop.py
```

---

### Task 6: Session-detail reading brief carries the crop id

**Files:**
- Modify: `src/backend/app/schemas/session.py` (`ReadingBrief`)
- Modify: `src/backend/app/routers/sessions.py` (`_reading_brief`)
- Test: `src/backend/tests/test_reading_brief_crop.py` (create)

**Interfaces:**
- Produces: `ReadingBrief.plate_crop_asset_id: int | None`, populated by `_reading_brief`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_reading_brief_crop.py`:

```python
from app.models import ImageAsset, PlateReading
from app.routers.sessions import _reading_brief


def test_reading_brief_includes_plate_crop_asset_id(db_session):
    origin = ImageAsset(path="/o.enc", encrypted=True, sha256="o", direction="in")
    crop = ImageAsset(path="/c.enc", encrypted=True, sha256="c", direction="in")
    db_session.add_all([origin, crop])
    db_session.flush()
    reading = PlateReading(
        capture_id="cap-brief", direction="in", review_state="confident",
        image_asset_id=origin.id, plate_crop_asset_id=crop.id,
    )
    db_session.add(reading)
    db_session.flush()

    brief = _reading_brief(db_session, reading.id)
    assert brief.plate_crop_asset_id == crop.id
    assert brief.image_asset_id == origin.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_reading_brief_crop.py -v`
Expected: FAIL — `ReadingBrief` has no `plate_crop_asset_id`.

- [ ] **Step 3: Add the field and populate it**

In `src/backend/app/schemas/session.py`, add to `ReadingBrief` (after `image_asset_id`):

```python
    plate_crop_asset_id: int | None = None
```

In `src/backend/app/routers/sessions.py`, in `_reading_brief`, add to the `ReadingBrief(...)` call (after `image_asset_id=reading.image_asset_id,`):

```python
        plate_crop_asset_id=reading.plate_crop_asset_id,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_reading_brief_crop.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS (no regressions).

- [ ] **Step 6: Stage changes**

```bash
git add src/backend/app/schemas/session.py src/backend/app/routers/sessions.py \
        src/backend/tests/test_reading_brief_crop.py
```

---

### Task 7: Regenerate OpenAPI + frontend API client

**Files:**
- Modify: `src/frontend/openapi.json` (regenerated)
- Modify: `src/frontend/src/api/generated/**` (regenerated)

**Interfaces:**
- Produces: generated `CaptureResponse` and `ReadingBrief` models gain `plate_crop_asset_id`.

- [ ] **Step 1: Export the OpenAPI schema**

Run: `cd src/backend && python scripts/export_openapi.py`
Expected: writes `../frontend/openapi.json` with no error.

- [ ] **Step 2: Regenerate the client**

Run: `cd src/frontend && npm run gen:api`
Expected: completes; `git status` shows changes under `src/api/generated/`.

- [ ] **Step 3: Verify the new field is present**

Run: `cd src/frontend && grep -r "plate_crop_asset_id" src/api/generated | head`
Expected: at least one match (in the generated `captureResponse` / `readingBrief` models).

- [ ] **Step 4: Stage changes**

```bash
git add src/frontend/openapi.json src/frontend/src/api/generated
```

---

### Task 8: Gate result shows origin + cropped

**Files:**
- Modify: `src/frontend/src/features/gate/use-gate-socket.ts` (`GateCapture` type)
- Modify: `src/frontend/src/features/gate/recognition-result.tsx`
- Test: `src/frontend/src/features/gate/recognition-result.test.tsx` (extend)

**Interfaces:**
- Consumes: `plate_crop_asset_id` on the capture object.
- Produces: a second `CapturePreview` rendered only when `plate_crop_asset_id` is set.

- [ ] **Step 1: Write the failing test**

At the top of `src/frontend/src/features/gate/recognition-result.test.tsx`, add a mock for the image fetch (so asset-id previews do not hit the network) right after the imports:

```typescript
vi.mock("@/lib/image-blob", () => ({
  fetchImageObjectUrl: vi.fn().mockResolvedValue("blob:x"),
}));
```

Then add:

```typescript
test("shows a second preview for the color-processed crop", () => {
  render(
    <RecognitionResult capture={{ ...base, image_asset_id: 11, plate_crop_asset_id: 12 }} />,
  );
  expect(screen.getByText(/biển đã xử lý màu/i)).toBeInTheDocument();
});

test("no crop preview when plate_crop_asset_id is absent", () => {
  render(<RecognitionResult capture={{ ...base, image_asset_id: 11 }} />);
  expect(screen.queryByText(/biển đã xử lý màu/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/recognition-result.test.tsx`
Expected: FAIL — label "biển đã xử lý màu" not found.

- [ ] **Step 3: Add the field to the type**

In `src/frontend/src/features/gate/use-gate-socket.ts`, add to `GateCapture` (after `image_asset_id?: number | null;`):

```typescript
  plate_crop_asset_id?: number | null;
```

- [ ] **Step 4: Render the crop preview**

In `src/frontend/src/features/gate/recognition-result.tsx`, replace the single origin preview line with an origin preview plus a conditional crop preview:

```tsx
      <CapturePreview localUrl={capture.local_image_url} imageAssetId={capture.image_asset_id} />
      {capture.plate_crop_asset_id != null && (
        <div className="space-y-1">
          <p className="text-[13px] text-muted">Biển đã xử lý màu</p>
          <CapturePreview imageAssetId={capture.plate_crop_asset_id} />
        </div>
      )}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/gate/recognition-result.test.tsx`
Expected: PASS (all tests in the file).

- [ ] **Step 6: Stage changes**

```bash
git add src/frontend/src/features/gate/use-gate-socket.ts \
        src/frontend/src/features/gate/recognition-result.tsx \
        src/frontend/src/features/gate/recognition-result.test.tsx
```

---

### Task 9: Session detail shows origin + cropped

**Files:**
- Modify: `src/frontend/src/features/sessions/session-detail-page.tsx`
- Test: `src/frontend/src/features/sessions/session-detail-page.test.tsx` (extend)

**Interfaces:**
- Consumes: generated `ReadingBrief.plate_crop_asset_id` (Task 7).
- Produces: a labeled crop `Evidence` under each of the entry/exit reading cards.

- [ ] **Step 1: Write the failing test**

In `src/frontend/src/features/sessions/session-detail-page.test.tsx`, add `plate_crop_asset_id: 21` to the mocked `entry_reading` object (so it becomes `{ id: 1, review_state: "confident", plate_text: "51F-123", image_asset_id: 11, plate_crop_asset_id: 21 }`), then add:

```typescript
test("shows the color-processed crop evidence", () => {
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText(/biển đã xử lý màu/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/sessions/session-detail-page.test.tsx`
Expected: FAIL — label not found.

- [ ] **Step 3: Render a labeled crop under each reading card**

In `src/frontend/src/features/sessions/session-detail-page.tsx`, in the entry card add after the existing `<Evidence imageId={data.entry_reading?.image_asset_id} />`:

```tsx
          {data.entry_reading?.plate_crop_asset_id != null && (
            <div className="space-y-1">
              <p className="text-[13px] text-muted">Biển đã xử lý màu</p>
              <Evidence imageId={data.entry_reading.plate_crop_asset_id} />
            </div>
          )}
```

In the exit card add after `<Evidence imageId={data.exit_reading?.image_asset_id} />`:

```tsx
          {data.exit_reading?.plate_crop_asset_id != null && (
            <div className="space-y-1">
              <p className="text-[13px] text-muted">Biển đã xử lý màu</p>
              <Evidence imageId={data.exit_reading.plate_crop_asset_id} />
            </div>
          )}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/sessions/session-detail-page.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full frontend suite**

Run: `cd src/frontend && npm test`
Expected: PASS (no regressions).

- [ ] **Step 6: Stage changes**

```bash
git add src/frontend/src/features/sessions/session-detail-page.tsx \
        src/frontend/src/features/sessions/session-detail-page.test.tsx
```

---

## Notes

- **Edge path**: `src/edge/worker.py` posts `json.dumps(pipeline.run(frame))`, which now includes `crop_proc_b64`; `POST /captures` uses the same `ingest_reading`, so the edge path persists the crop with no worker change. No task needed; confirmed by reading `worker.py:131-190` (forwards the full result dict verbatim).
- **Payload size**: `crop_proc_b64` adds a few KB per plate to the request body and WS is unaffected (the crop id, not the crop, goes over WS). The crop bytes are stripped before `raw_pipeline_json`, so the DB JSON column does not grow.
