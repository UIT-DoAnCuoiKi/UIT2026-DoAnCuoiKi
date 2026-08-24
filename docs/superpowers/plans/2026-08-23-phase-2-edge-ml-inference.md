# Phase 2: Edge ML inference — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** cho phép kiosk edge gửi một ảnh thô và nhận về biển, màu, loại xe: thêm endpoint suy luận nhận ảnh, chạy pipeline nhận dạng, tạo lượt đọc và trả `CaptureResponse`; giữ nguyên đường `POST /captures` payload cho cổng tự động.

**Architecture:** backend phụ thuộc một interface `InferenceEngine` chứ không phụ thuộc thẳng model. Test dùng `FakeInferenceEngine` (không torch, không model). Adapter thật `MlInferenceEngine` bọc `run_pipeline_on_image` của `src/ml`, chọn qua biến cấu hình. Logic tạo lượt đọc được tách thành service dùng chung cho cả hai đường ingest, giữ DRY.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 sync, pydantic v2, pytest, httpx (TestClient). Adapter thật cần torch, opencv, và pipeline `src/ml` (chỉ ở runtime edge, ngoài suite test backend).

## Global Constraints

Kế thừa `docs/superpowers/plans/2026-08-23-parking-edge-cloud-plan-index.md` mục Global Constraints. Riêng phase này:

- Hợp đồng payload không đổi: `PipelinePayload` và `PlateItem` trong `app/schemas/capture.py` là đích ánh xạ kết quả pipeline. Dict trả từ `run_pipeline_on_image` khớp đúng các field này (`vehicle_type`, `vehicle_box`, `vehicle_style`, `vehicle_style_conf`, `plates[].{bbox, layout, det_conf, plate_text, plate_valid, ocr_conf, color, color_conf}`).
- `review_state` do backend tính bằng `compute_review_state` hiện có: ngưỡng `ocr_conf < 0.7`, `det_conf < 0.5`, hoặc `plate_valid == false` thì `needs_review`; không bao giờ chặn.
- `capture_id` UNIQUE, idempotent: gửi lại cùng `capture_id` trả bản đã có với `duplicate = true`, không tạo lượt đọc mới.
- Nhóm xe suy từ `vehicle_type` qua `group_for`: `car -> o_to_con`, `motorbike/bicycle -> xe_may`, `truck -> xe_tai`, `bus -> xe_khach`.
- Suy luận thật mục tiêu dưới 2 giây mỗi xe trên Pi 5 (ONNX INT8). Suite test backend không nạp model; adapter thật verify bằng smoke thủ công.
- Endpoint suy luận phục vụ kiosk có nhân viên đăng nhập: bảo vệ bằng `get_current_user` (staff hoặc admin), khác `POST /captures` dùng `require_edge_key`.
- Không dùng ký tự gạch ngang trong văn xuôi tài liệu.
- Test chạy trên SQLite in-memory qua fixture `db_session`; inject engine giả và db qua `app.dependency_overrides`.

---

### Task 1: Tách service ingest lượt đọc dùng chung

**Files:**
- Create: `src/backend/app/services/capture_ingest.py`
- Modify: `src/backend/app/routers/captures.py`
- Test: `src/backend/tests/test_capture_ingest_service.py`

**Interfaces:**
- Consumes: `PipelinePayload`, `PlateItem` (`app/schemas/capture.py`); `select_representative`, `compute_review_state` (`app/services/capture.py`); `store_encrypted_image`, `gate_hub`, `group_for`, `crypto`, `plate_hash` như hiện dùng trong `captures.py`.
- Produces: `ingest_reading(db, *, capture_id: str, direction: str, lane: str | None, payload: PipelinePayload, image_bytes: bytes) -> tuple[PlateReading, str | None, bool]` trả `(reading, plate_text, duplicate)`; `build_capture_response(reading: PlateReading, plate_text: str | None, duplicate: bool) -> CaptureResponse`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_capture_ingest_service.py`:

```python
from app.schemas.capture import PipelinePayload, PlateItem


def _payload():
    return PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(bbox=[0, 0, 10, 10], layout="1", det_conf=0.9,
                          plate_text="51F12345", plate_valid=True, ocr_conf=0.95,
                          color="white", color_conf=0.9)],
    )


def test_ingest_creates_reading_and_response(db_session):
    from app.services.capture_ingest import build_capture_response, ingest_reading
    reading, plate_text, duplicate = ingest_reading(
        db_session, capture_id="cap-1", direction="in", lane="lane1",
        payload=_payload(), image_bytes=b"jpegbytes",
    )
    assert duplicate is False
    assert plate_text == "51F12345"
    assert reading.review_state == "confident"
    assert reading.color == "white"
    assert reading.vehicle_type == "car"

    resp = build_capture_response(reading, plate_text, duplicate)
    assert resp.plate_text == "51F12345"
    assert resp.vehicle_group == "o_to_con"
    assert resp.duplicate is False


def test_ingest_is_idempotent_on_capture_id(db_session):
    from app.services.capture_ingest import ingest_reading
    first, _, dup1 = ingest_reading(
        db_session, capture_id="cap-2", direction="in", lane=None,
        payload=_payload(), image_bytes=b"x")
    second, text2, dup2 = ingest_reading(
        db_session, capture_id="cap-2", direction="in", lane=None,
        payload=_payload(), image_bytes=b"x")
    assert dup1 is False and dup2 is True
    assert second.id == first.id
    assert text2 == "51F12345"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_capture_ingest_service.py -v`
Expected: FAIL (ModuleNotFoundError: app.services.capture_ingest).

- [ ] **Step 3: Write the service**

Create `src/backend/app/services/capture_ingest.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlateReading
from app.schemas.capture import CaptureResponse, PipelinePayload
from app.security import crypto
from app.security.plate import plate_hash
from app.services.capture import compute_review_state, select_representative
from app.services.gate_hub import gate_hub
from app.services.image_store import store_encrypted_image
from app.services.vehicle_groups import group_for


def build_capture_response(reading: PlateReading, plate_text: str | None, duplicate: bool) -> CaptureResponse:
    return CaptureResponse(
        reading_id=reading.id,
        capture_id=reading.capture_id,
        direction=reading.direction,
        review_state=reading.review_state,
        plate_text=plate_text,
        plate_valid=reading.plate_valid,
        vehicle_type=reading.vehicle_type,
        vehicle_group=group_for(reading.vehicle_type),
        color=reading.color,
        image_asset_id=reading.image_asset_id,
        duplicate=duplicate,
    )


def ingest_reading(
    db: Session, *, capture_id: str, direction: str, lane: str | None,
    payload: PipelinePayload, image_bytes: bytes,
) -> tuple[PlateReading, str | None, bool]:
    existing = db.scalars(select(PlateReading).where(PlateReading.capture_id == capture_id)).first()
    if existing is not None:
        text = crypto.decrypt_text(existing.plate_text_ciphertext) if existing.plate_text_ciphertext else None
        return existing, text, True

    asset = store_encrypted_image(db, image_bytes, direction)
    rep = select_representative(payload.plates)
    plate_text = rep.plate_text if rep else None
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
        raw_pipeline_json=payload.model_dump(),
        image_asset_id=asset.id,
        review_state=compute_review_state(rep),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    gate_hub.publish({
        "reading_id": reading.id,
        "capture_id": reading.capture_id,
        "direction": reading.direction,
        "lane": reading.lane,
        "review_state": reading.review_state,
        "plate_text": plate_text,
        "vehicle_group": group_for(payload.vehicle_type),
    })
    return reading, plate_text, False
```

- [ ] **Step 4: Refactor `POST /captures` to use the service**

Replace the whole body of `src/backend/app/routers/captures.py` with:

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_edge_key
from app.models import PlateReading
from app.schemas.capture import CaptureResponse, PipelinePayload
from app.security import crypto
from app.services.capture_ingest import build_capture_response, ingest_reading
from app.services.vehicle_groups import group_for

router = APIRouter(tags=["captures"])


@router.post("/captures", response_model=CaptureResponse, dependencies=[Depends(require_edge_key)])
def ingest_capture(
    capture_id: str = Form(...),
    direction: str = Form(...),
    payload: str = Form(...),
    lane: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CaptureResponse:
    if direction not in ("in", "out"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "direction phải là in hoặc out")
    data = PipelinePayload.model_validate_json(payload)
    raw = image.file.read()
    reading, plate_text, duplicate = ingest_reading(
        db, capture_id=capture_id, direction=direction, lane=lane, payload=data, image_bytes=raw,
    )
    return build_capture_response(reading, plate_text, duplicate)


@router.get("/captures/latest")
def latest_capture(lane: str | None = None, db: Session = Depends(get_db)) -> dict:
    stmt = select(PlateReading).order_by(PlateReading.id.desc())
    if lane:
        stmt = stmt.where(PlateReading.lane == lane)
    reading = db.scalars(stmt.limit(1)).first()
    if reading is None:
        return {}
    text = crypto.decrypt_text(reading.plate_text_ciphertext) if reading.plate_text_ciphertext else None
    return {
        "reading_id": reading.id,
        "capture_id": reading.capture_id,
        "direction": reading.direction,
        "lane": reading.lane,
        "review_state": reading.review_state,
        "plate_text": text,
        "vehicle_group": group_for(reading.vehicle_type),
    }
```

- [ ] **Step 5: Run the new service test and the existing capture tests**

Run: `cd src/backend && python -m pytest tests/test_capture_ingest_service.py tests/test_capture_ingest.py tests/test_capture_logic.py -v`
Expected: PASS (service tests mới cộng test endpoint và logic cũ, không regression vì hành vi giữ nguyên).

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/services/capture_ingest.py src/backend/app/routers/captures.py src/backend/tests/test_capture_ingest_service.py
git commit -m "refactor(backend): extract shared capture ingest service"
```

---

### Task 2: Interface suy luận và engine giả

**Files:**
- Create: `src/backend/app/services/inference.py`
- Modify: `src/backend/app/config.py`
- Test: `src/backend/tests/test_inference_fake.py`

**Interfaces:**
- Consumes: `PipelinePayload`, `PlateItem` (`app/schemas/capture.py`); `settings` (`app/config.py`).
- Produces: Protocol `InferenceEngine` với `infer(self, image_bytes: bytes) -> PipelinePayload`; lớp `FakeInferenceEngine(payload: PipelinePayload | None = None)`; provider `get_inference_engine() -> InferenceEngine` chọn theo `settings.inference_engine` (mặc định `"fake"`).

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_inference_fake.py`:

```python
def test_fake_engine_default_payload_is_valid():
    from app.services.inference import FakeInferenceEngine
    payload = FakeInferenceEngine().infer(b"anything")
    assert payload.vehicle_type == "car"
    assert payload.plates[0].plate_text == "51F12345"
    assert payload.plates[0].plate_valid is True


def test_fake_engine_returns_injected_payload():
    from app.schemas.capture import PipelinePayload, PlateItem
    from app.services.inference import FakeInferenceEngine
    custom = PipelinePayload(vehicle_type="motorbike", plates=[PlateItem(plate_text="59X1", plate_valid=False)])
    payload = FakeInferenceEngine(custom).infer(b"x")
    assert payload.vehicle_type == "motorbike"
    assert payload.plates[0].plate_text == "59X1"


def test_provider_defaults_to_fake():
    from app.services.inference import FakeInferenceEngine, get_inference_engine
    assert isinstance(get_inference_engine(), FakeInferenceEngine)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_inference_fake.py -v`
Expected: FAIL (ModuleNotFoundError: app.services.inference).

- [ ] **Step 3: Add the config setting**

In `src/backend/app/config.py`, add one field to the `Settings` class (for example right after `edge_api_key`):

```python
    inference_engine: str = "fake"   # fake | ml
```

- [ ] **Step 4: Write the inference module**

Create `src/backend/app/services/inference.py`:

```python
from typing import Protocol

from app.config import settings
from app.schemas.capture import PipelinePayload, PlateItem


class InferenceEngine(Protocol):
    def infer(self, image_bytes: bytes) -> PipelinePayload: ...


def _default_payload() -> PipelinePayload:
    return PipelinePayload(
        vehicle_type="car",
        plates=[PlateItem(
            bbox=[0, 0, 10, 10], layout="1", det_conf=0.9,
            plate_text="51F12345", plate_valid=True, ocr_conf=0.95,
            color="white", color_conf=0.9,
        )],
    )


class FakeInferenceEngine:
    def __init__(self, payload: PipelinePayload | None = None) -> None:
        self._payload = payload or _default_payload()

    def infer(self, image_bytes: bytes) -> PipelinePayload:
        return self._payload


def get_inference_engine() -> InferenceEngine:
    if settings.inference_engine == "ml":
        from app.services.ml_inference import get_ml_engine
        return get_ml_engine()
    return FakeInferenceEngine()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_inference_fake.py -v`
Expected: PASS (3 tests). Provider mặc định trả `FakeInferenceEngine`; nhánh `ml` chưa import vì chưa chạm.

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/services/inference.py src/backend/app/config.py src/backend/tests/test_inference_fake.py
git commit -m "feat(backend): add inference engine interface and fake engine"
```

---

### Task 3: Endpoint `POST /captures/infer`

**Files:**
- Modify: `src/backend/app/routers/captures.py`
- Test: `src/backend/tests/test_captures_infer.py`

**Interfaces:**
- Consumes: `ingest_reading`, `build_capture_response` (Task 1); `InferenceEngine`, `get_inference_engine` (Task 2); `get_current_user`, `User` cho bảo vệ theo vai.
- Produces: `POST /captures/infer` nhận multipart `capture_id` (Form), `direction` (Form), `lane` (Form optional), `image` (File); chạy `engine.infer(bytes)` rồi `ingest_reading`; trả `CaptureResponse`. Bảo vệ bằng `get_current_user`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_captures_infer.py`:

```python
from app.schemas.capture import PipelinePayload, PlateItem
from app.services.inference import FakeInferenceEngine, get_inference_engine


def _override_engine(client, payload=None):
    client.app.dependency_overrides[get_inference_engine] = lambda: FakeInferenceEngine(payload)


def test_infer_creates_reading_from_image(client, staff_headers):
    _override_engine(client)
    resp = client.post(
        "/captures/infer",
        data={"capture_id": "infer-1", "direction": "in", "lane": "lane1"},
        files={"image": ("frame.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate_text"] == "51F12345"
    assert body["color"] == "white"
    assert body["vehicle_type"] == "car"
    assert body["vehicle_group"] == "o_to_con"
    assert body["review_state"] == "confident"
    assert body["duplicate"] is False


def test_infer_is_idempotent(client, staff_headers):
    _override_engine(client)
    args = dict(
        data={"capture_id": "infer-2", "direction": "in"},
        files={"image": ("f.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    first = client.post("/captures/infer", **args).json()
    second = client.post("/captures/infer", **args).json()
    assert first["reading_id"] == second["reading_id"]
    assert second["duplicate"] is True


def test_infer_requires_auth(client):
    _override_engine(client)
    resp = client.post(
        "/captures/infer",
        data={"capture_id": "infer-3", "direction": "in"},
        files={"image": ("f.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
    )
    assert resp.status_code in (401, 403)


def test_infer_rejects_bad_direction(client, staff_headers):
    _override_engine(client)
    resp = client.post(
        "/captures/infer",
        data={"capture_id": "infer-4", "direction": "sideways"},
        files={"image": ("f.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_captures_infer.py -v`
Expected: FAIL (404 on `/captures/infer`).

- [ ] **Step 3: Add the endpoint**

In `src/backend/app/routers/captures.py`, extend the imports. Change the deps import line and add model and service imports:

```python
from app.deps import get_current_user, require_edge_key
from app.models import PlateReading, User
from app.services.inference import InferenceEngine, get_inference_engine
```

(keep the existing `from app.services.capture_ingest import build_capture_response, ingest_reading` line).

Add this route to the file (after `ingest_capture`, before `latest_capture`):

```python
@router.post("/captures/infer", response_model=CaptureResponse)
def infer_capture(
    capture_id: str = Form(...),
    direction: str = Form(...),
    lane: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
    user: User = Depends(get_current_user),
) -> CaptureResponse:
    if direction not in ("in", "out"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "direction phải là in hoặc out")
    raw = image.file.read()
    payload = engine.infer(raw)
    reading, plate_text, duplicate = ingest_reading(
        db, capture_id=capture_id, direction=direction, lane=lane, payload=payload, image_bytes=raw,
    )
    return build_capture_response(reading, plate_text, duplicate)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_captures_infer.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the capture suite to confirm no regression**

Run: `cd src/backend && python -m pytest tests/test_capture_ingest.py tests/test_capture_logic.py tests/test_captures_infer.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/routers/captures.py src/backend/tests/test_captures_infer.py
git commit -m "feat(backend): add POST /captures/infer image inference endpoint"
```

---

### Task 4: Adapter suy luận thật bọc pipeline `src/ml`

**Files:**
- Create: `src/backend/app/services/ml_inference.py`
- Test: `src/backend/tests/test_ml_inference_guard.py`

**Interfaces:**
- Consumes: `PipelinePayload` (`app/schemas/capture.py`); `run_pipeline_on_image` và các loader model của `src/ml` (`predict_vehicle.load_style_model`, `classifier.build_transforms`, `plate_detect.inference.plate_detector.PlateDetector`, `pipeline.ocr.CRNNRecognizer`) tại runtime edge.
- Produces: `MlInferenceEngine` với `infer(self, image_bytes: bytes) -> PipelinePayload`; `get_ml_engine() -> MlInferenceEngine` (singleton nạp model một lần). Đường dẫn model và `src/ml` lấy từ biến môi trường.

Ghi chú: adapter này phụ thuộc torch, opencv, và cây `src/ml`, không nạp trong suite test backend. Test ở task này chỉ kiểm module import được và tôn trọng cấu hình; đúng đắn suy luận thật verify bằng smoke thủ công (step cuối).

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_ml_inference_guard.py`:

```python
def test_default_config_does_not_select_ml():
    from app.config import settings
    from app.services.inference import FakeInferenceEngine, get_inference_engine
    assert settings.inference_engine == "fake"
    assert isinstance(get_inference_engine(), FakeInferenceEngine)


def test_map_result_dict_to_payload():
    # ánh xạ thuần, không cần model: dict kết quả pipeline hợp lệ thành PipelinePayload
    from app.services.ml_inference import result_to_payload
    result = {
        "file": "x.jpg", "vehicle_type": "car", "vehicle_box": [1, 2, 3, 4],
        "vehicle_style": "sedan", "vehicle_style_conf": 0.8,
        "plates": [{"bbox": [0, 0, 5, 5], "layout": "1", "det_conf": 0.7,
                    "plate_text": "51F999", "plate_valid": True, "ocr_conf": 0.85,
                    "color": "white", "color_conf": 0.9}],
    }
    payload = result_to_payload(result)
    assert payload.vehicle_type == "car"
    assert payload.vehicle_style == "sedan"
    assert payload.plates[0].plate_text == "51F999"
    assert payload.plates[0].color == "white"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_ml_inference_guard.py -v`
Expected: FAIL (ModuleNotFoundError: app.services.ml_inference).

- [ ] **Step 3: Write the adapter with lazy heavy imports**

Create `src/backend/app/services/ml_inference.py`:

```python
"""Adapter suy luận thật cho runtime edge. Bọc pipeline src/ml.

Phụ thuộc torch, opencv, và cây src/ml; các import nặng nằm trong hàm để
suite test backend (không có model) vẫn import được module cho phần ánh xạ
thuần. Chọn adapter bằng biến môi trường INFERENCE_ENGINE=ml cộng các đường
dẫn model dưới đây.
"""
import os
import tempfile

from app.schemas.capture import PipelinePayload


def result_to_payload(result: dict) -> PipelinePayload:
    """Ánh xạ dict kết quả run_pipeline_on_image thành PipelinePayload.

    Dict đã trùng field với PipelinePayload và PlateItem; khóa thừa (file)
    được pydantic bỏ qua.
    """
    return PipelinePayload.model_validate(result)


class MlInferenceEngine:
    def __init__(self, plate_detector, ocr_recognizer, style_model, style_classes, style_transform, device: str):
        self._plate_detector = plate_detector
        self._ocr = ocr_recognizer
        self._style_model = style_model
        self._style_classes = style_classes
        self._style_transform = style_transform
        self._device = device

    def infer(self, image_bytes: bytes) -> PipelinePayload:
        from pathlib import Path

        from e2e_pipeline_test import run_pipeline_on_image  # cây src/ml trên PYTHONPATH

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
            tmp.write(image_bytes)
            tmp.flush()
            result, _img = run_pipeline_on_image(
                Path(tmp.name), self._plate_detector, self._ocr,
                self._style_model, self._style_classes, self._style_transform, self._device,
            )
        return result_to_payload(result)


_engine: "MlInferenceEngine | None" = None


def get_ml_engine() -> "MlInferenceEngine":
    """Nạp model một lần. Đường dẫn model lấy từ biến môi trường:
    ML_STYLE_MODEL, ML_STYLE_CLASSES, ML_PLATE_WEIGHTS, ML_OCR_WEIGHTS, ML_DEVICE.
    """
    global _engine
    if _engine is not None:
        return _engine

    import json

    import torch  # noqa: F401  xác nhận runtime có torch

    from classifier import build_transforms
    from pipeline.ocr import CRNNRecognizer
    from plate_detect.inference.plate_detector import PlateDetector
    from predict_vehicle import load_style_model

    device = os.environ.get("ML_DEVICE", "cpu")
    style_classes = json.loads(os.environ["ML_STYLE_CLASSES"]) if os.environ.get("ML_STYLE_CLASSES") else []
    if os.environ.get("ML_STYLE_CLASSES", "").endswith(".json"):
        with open(os.environ["ML_STYLE_CLASSES"], encoding="utf-8") as fh:
            style_classes = json.load(fh)
    style_model = load_style_model(os.environ["ML_STYLE_MODEL"], device)
    style_transform = build_transforms(train=False)
    plate_detector = PlateDetector(os.environ["ML_PLATE_WEIGHTS"])
    ocr = CRNNRecognizer(os.environ["ML_OCR_WEIGHTS"], device=device)

    _engine = MlInferenceEngine(plate_detector, ocr, style_model, style_classes, style_transform, device)
    return _engine
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_ml_inference_guard.py -v`
Expected: PASS (2 tests). Module import được vì import nặng nằm trong hàm; `result_to_payload` là ánh xạ thuần.

- [ ] **Step 5: Manual smoke on an edge-like machine (not part of the suite)**

Trên máy có torch, opencv, model, và `src/ml` trên PYTHONPATH, đặt biến môi trường model rồi chạy backend với `INFERENCE_ENGINE=ml` và POST một ảnh thật tới `/captures/infer`. Xác nhận trả biển, màu, loại xe đúng và tổng thời gian dưới 2 giây. Ghi lại kết quả trong report; không thêm vào suite test backend.

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/services/ml_inference.py src/backend/tests/test_ml_inference_guard.py
git commit -m "feat(backend): add real ML inference adapter wrapping src/ml pipeline"
```

---

### Task 5: Test nghiệm thu phase và chạy toàn suite

**Files:**
- Test: `src/backend/tests/test_phase2_inference_acceptance.py`

**Interfaces:**
- Consumes: mọi thứ ở Task 1 tới 3 (đường fake engine).

- [ ] **Step 1: Write the acceptance test**

Create `src/backend/tests/test_phase2_inference_acceptance.py`:

```python
from app.schemas.capture import PipelinePayload, PlateItem
from app.services.inference import FakeInferenceEngine, get_inference_engine


def test_kiosk_photo_to_reading_end_to_end(client, staff_headers):
    # engine giả trả một xe máy biển hợp lệ màu trắng
    payload = PipelinePayload(
        vehicle_type="motorbike",
        plates=[PlateItem(bbox=[0, 0, 8, 8], layout="2", det_conf=0.8,
                          plate_text="59X12345", plate_valid=True, ocr_conf=0.9,
                          color="white", color_conf=0.88)],
    )
    client.app.dependency_overrides[get_inference_engine] = lambda: FakeInferenceEngine(payload)

    resp = client.post(
        "/captures/infer",
        data={"capture_id": "acc-1", "direction": "in", "lane": "cong-1"},
        files={"image": ("shot.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
        headers=staff_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate_text"] == "59X12345"
    assert body["vehicle_type"] == "motorbike"
    assert body["vehicle_group"] == "xe_may"
    assert body["color"] == "white"
    assert body["review_state"] == "confident"
    assert body["reading_id"] is not None

    # lượt đọc xuất hiện ở /captures/latest cho lane đó
    latest = client.get("/captures/latest?lane=cong-1").json()
    assert latest["plate_text"] == "59X12345"
    assert latest["vehicle_group"] == "xe_may"
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd src/backend && python -m pytest tests/test_phase2_inference_acceptance.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS toàn bộ (suite cũ, phase 1, phase 2). Không regression; đường `POST /captures` cũ vẫn xanh qua service tách dùng chung.

- [ ] **Step 4: Commit**

```bash
git add src/backend/tests/test_phase2_inference_acceptance.py
git commit -m "test(backend): phase 2 kiosk image inference acceptance"
```

---

## Self-Review

**Spec coverage (spec kiến trúc mục 5, spec frontend v2 mục 5.2):**
- Endpoint nhận ảnh thô trả biển/màu/loại: Task 3. Chạy pipeline tại edge: Task 4 (adapter thật). Tạo lượt đọc và phát realtime: Task 1 (service dùng chung, `gate_hub.publish`). Giữ đường `POST /captures` payload cho cổng tự động: Task 1 giữ endpoint, đổi ruột sang service chung. Idempotent `capture_id`: Task 1 và test Task 3. Bảo vệ theo vai kiosk: Task 3.
- Ngoài phạm vi phase này (nằm ở phase sau hoặc client): toggle `read_plate` ép nhập tay là hành vi client (kiosk không gọi infer khi tắt); lượng tử hóa INT8 và tối ưu model là việc `edge-deploy` của phase tối ưu; gắn `zone_id` cho lượt đọc không cần ở đây vì phiên đã mang `zone_id` từ phase 1.

**Placeholder scan:** không có TBD. Mọi bước code có code thật. Task 4 step 5 là smoke thủ công có chủ đích (cần model), không phải placeholder.

**Type consistency:** `ingest_reading(...) -> (PlateReading, str | None, bool)` và `build_capture_response(reading, plate_text, duplicate)` dùng thống nhất giữa Task 1, 3. `InferenceEngine.infer(bytes) -> PipelinePayload` và `get_inference_engine()` khớp giữa Task 2, 3, 4. `result_to_payload(dict) -> PipelinePayload` khớp field với dict của `run_pipeline_on_image` (đã đọc từ `src/ml/e2e_pipeline_test.py`). `settings.inference_engine` khớp giữa config (Task 2) và provider (Task 2) và guard test (Task 4).

**Ghi chú rủi ro:** adapter thật (Task 4) phụ thuộc cây `src/ml` chưa đóng gói thành package cài được; nó cần `src/ml` trên PYTHONPATH và đường dẫn model qua biến môi trường. Đây là ghép nối môi trường, verify thủ công. Nếu sau này `src/ml` được đóng gói sạch, thay các import trong `get_ml_engine` cho gọn.
