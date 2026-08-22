# Phase 3: Nhận capture, lưu reading và ảnh mã hóa

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** endpoint `POST /captures` nhận ảnh cộng dict pipeline từ edge worker, idempotent theo `capture_id`, lưu `image_asset` mã hóa và `plate_reading`, chọn biển đại diện, tính `review_state`, cộng script giả lập edge worker cho dev PC.

**Architecture:** edge worker (hoặc script giả lập) POST multipart gồm ảnh, JSON payload, `capture_id`, `direction`, `lane`, header `X-Edge-Key`. Backend giải payload, mã hóa ảnh ghi đĩa, chọn biển `det_conf` cao nhất, tính `review_state` (`confident` hoặc `needs_review`), lưu reading với biển mã hóa cộng `plate_hash`. Idempotency dựa `capture_id` UNIQUE.

**Tech Stack:** FastAPI multipart (`python-multipart`), SQLAlchemy, cryptography Fernet, httpx (script giả lập), pytest.

## Global Constraints

Xem `2026-08-22-dashboard-mvp-plan-index.md`. Riêng phase này: `capture_id` UNIQUE idempotent; `review_state` tính ở backend (`confident` hoặc `needs_review` tại bước nhận capture; `disputed` và `manual` gán ở Phase 4); ngưỡng `ocr_conf < 0.7` hoặc `plate_valid == false` hoặc `det_conf < 0.5` thì `needs_review`; biển và ảnh mã hóa trước khi ghi; nhóm xe bốn giá trị; commit chờ người dùng; phase khép bằng acceptance test.

## Interfaces Phase 1 và 2 dùng lại

- `app.db.get_db`, `app.models.PlateReading`, `app.models.ImageAsset`.
- `app.security.crypto.encrypt_text/decrypt_text/encrypt_bytes/decrypt_bytes`, `app.security.plate.plate_hash/normalize_plate`.
- `app.config.settings.image_storage_dir`, `settings.retention_days`.
- `create_app()`, fixture test `client`, `db_session`.

## File Structure

- Modify: `src/backend/app/config.py` (thêm `edge_api_key`).
- Modify: `src/backend/app/deps.py` (thêm `require_edge_key`).
- Create: `src/backend/app/services/image_store.py` lưu ảnh mã hóa.
- Create: `src/backend/app/services/vehicle_groups.py` map `vehicle_type` sang nhóm.
- Create: `src/backend/app/services/capture.py` chọn biển đại diện, tính `review_state`.
- Create: `src/backend/app/schemas/capture.py` schema payload và response.
- Create: `src/backend/app/routers/captures.py` endpoint.
- Modify: `src/backend/app/main.py` (gắn router captures).
- Create: `src/backend/scripts/__init__.py`, `src/backend/scripts/simulate_edge.py` script giả lập edge.
- Create: `tests/test_image_store.py`, `test_capture_logic.py`, `test_capture_ingest.py`, `test_edge_simulator.py`, `test_phase3_acceptance.py`.

---

### Task 1: Edge key và lưu ảnh mã hóa

**Files:**
- Modify: `src/backend/app/config.py`
- Modify: `src/backend/app/deps.py`
- Create: `src/backend/app/services/image_store.py`
- Create: `src/backend/tests/test_image_store.py`

**Interfaces:**
- Produces: `settings.edge_api_key: str`; `deps.require_edge_key(x_edge_key)` chặn khi sai key; `image_store.store_encrypted_image(db, raw: bytes, direction: str | None) -> ImageAsset` (ghi file mã hóa, set `sha256` của plaintext, `retention_delete_after=None`).

- [ ] **Step 1: Thêm edge_api_key vào config.py**

Trong `src/backend/app/config.py`, thêm dòng ngay dưới `image_storage_dir`:

```python
    edge_api_key: str = "edge-dev-key"
```

- [ ] **Step 2: Thêm require_edge_key vào deps.py**

Ở đầu `src/backend/app/deps.py`, đổi dòng import fastapi thành:

```python
from fastapi import Depends, Header, HTTPException, status
```

Thêm import config ngay dưới các import hiện có:

```python
from app.config import settings
```

Thêm hàm vào cuối file:

```python
def require_edge_key(x_edge_key: str = Header(..., alias="X-Edge-Key")) -> None:
    if x_edge_key != settings.edge_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "edge key không hợp lệ")
```

- [ ] **Step 3: Viết test thất bại cho image_store**

`src/backend/tests/test_image_store.py`:

```python
import hashlib
from pathlib import Path

from app.security import crypto
from app.services.image_store import store_encrypted_image


def test_store_encrypts_and_hashes(db_session, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))

    raw = b"\xff\xd8\xff fake jpeg bytes"
    asset = store_encrypted_image(db_session, raw, direction="in")
    db_session.commit()

    assert asset.id is not None
    assert asset.encrypted is True
    assert asset.direction == "in"
    assert asset.sha256 == hashlib.sha256(raw).hexdigest()

    stored = Path(asset.path).read_bytes()
    assert stored != raw
    assert crypto.decrypt_bytes(stored) == raw
```

- [ ] **Step 4: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_image_store.py -v`
Expected: FAIL vì `app.services.image_store` chưa có.

- [ ] **Step 5: Viết image_store.py**

```python
import hashlib
import os
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ImageAsset
from app.security import crypto


def store_encrypted_image(db: Session, raw: bytes, direction: str | None) -> ImageAsset:
    os.makedirs(settings.image_storage_dir, exist_ok=True)
    path = os.path.join(settings.image_storage_dir, f"{uuid.uuid4().hex}.enc")
    with open(path, "wb") as f:
        f.write(crypto.encrypt_bytes(raw))
    asset = ImageAsset(
        path=path,
        encrypted=True,
        sha256=hashlib.sha256(raw).hexdigest(),
        direction=direction,
        retention_delete_after=None,  # đặt khi xe ra; job xóa Phase 5 tính theo exit_time
    )
    db.add(asset)
    db.flush()
    return asset
```

- [ ] **Step 6: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_image_store.py -v`
Expected: PASS.

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/backend/app/config.py src/backend/app/deps.py src/backend/app/services/image_store.py src/backend/tests/test_image_store.py
git commit -m "feat(backend): edge key guard and encrypted image storage"
```

---

### Task 2: Schema payload, chọn biển đại diện, review_state, nhóm xe

**Files:**
- Create: `src/backend/app/schemas/capture.py`
- Create: `src/backend/app/services/vehicle_groups.py`
- Create: `src/backend/app/services/capture.py`
- Create: `src/backend/tests/test_capture_logic.py`

**Interfaces:**
- Produces: schema `PlateItem`, `PipelinePayload`, `CaptureResponse`; `vehicle_groups.group_for(vehicle_type: str | None) -> str | None`; `capture.select_representative(plates: list[PlateItem]) -> PlateItem | None`; `capture.compute_review_state(rep: PlateItem | None) -> str`.

- [ ] **Step 1: Viết schemas/capture.py**

```python
from pydantic import BaseModel


class PlateItem(BaseModel):
    bbox: list[float] | None = None
    layout: str | None = None
    det_conf: float | None = None
    plate_text: str | None = None
    plate_valid: bool | None = None
    ocr_conf: float | None = None
    color: str | None = None
    color_conf: float | None = None


class PipelinePayload(BaseModel):
    vehicle_type: str | None = None
    vehicle_box: list[float] | None = None
    vehicle_style: str | None = None
    vehicle_style_conf: float | None = None
    plates: list[PlateItem] = []


class CaptureResponse(BaseModel):
    reading_id: int
    capture_id: str
    direction: str
    review_state: str
    plate_text: str | None = None
    plate_valid: bool | None = None
    vehicle_type: str | None = None
    vehicle_group: str | None = None
    color: str | None = None
    image_asset_id: int | None = None
    duplicate: bool = False
```

- [ ] **Step 2: Viết test thất bại**

`src/backend/tests/test_capture_logic.py`:

```python
from app.schemas.capture import PlateItem
from app.services.capture import compute_review_state, select_representative
from app.services.vehicle_groups import group_for


def test_select_highest_det_conf():
    plates = [PlateItem(plate_text="A", det_conf=0.6), PlateItem(plate_text="B", det_conf=0.9)]
    assert select_representative(plates).plate_text == "B"


def test_select_none_when_empty():
    assert select_representative([]) is None


def test_review_confident():
    rep = PlateItem(plate_text="51F12345", det_conf=0.95, ocr_conf=0.9, plate_valid=True)
    assert compute_review_state(rep) == "confident"


def test_review_needs_low_ocr():
    rep = PlateItem(plate_text="51F12345", det_conf=0.95, ocr_conf=0.5, plate_valid=True)
    assert compute_review_state(rep) == "needs_review"


def test_review_needs_invalid():
    rep = PlateItem(plate_text="???", det_conf=0.95, ocr_conf=0.9, plate_valid=False)
    assert compute_review_state(rep) == "needs_review"


def test_review_needs_no_plate():
    assert compute_review_state(None) == "needs_review"


def test_group_mapping():
    assert group_for("car") == "o_to_con"
    assert group_for("motorbike") == "xe_may"
    assert group_for("bicycle") == "xe_may"
    assert group_for("truck") == "xe_tai"
    assert group_for("bus") == "xe_khach"
    assert group_for(None) is None
    assert group_for("unknown") is None
```

- [ ] **Step 3: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_capture_logic.py -v`
Expected: FAIL vì service chưa có.

- [ ] **Step 4: Viết vehicle_groups.py**

```python
_MAP = {
    "motorbike": "xe_may",
    "bicycle": "xe_may",
    "car": "o_to_con",
    "truck": "xe_tai",
    "bus": "xe_khach",
}


def group_for(vehicle_type: str | None) -> str | None:
    if vehicle_type is None:
        return None
    return _MAP.get(vehicle_type.lower())
```

- [ ] **Step 5: Viết capture.py**

```python
from app.schemas.capture import PlateItem

OCR_CONF_MIN = 0.7
DET_CONF_MIN = 0.5


def select_representative(plates: list[PlateItem]) -> PlateItem | None:
    if not plates:
        return None
    return max(plates, key=lambda p: p.det_conf if p.det_conf is not None else -1.0)


def compute_review_state(rep: PlateItem | None) -> str:
    if rep is None or not rep.plate_text:
        return "needs_review"
    if rep.plate_valid is False:
        return "needs_review"
    if rep.ocr_conf is not None and rep.ocr_conf < OCR_CONF_MIN:
        return "needs_review"
    if rep.det_conf is not None and rep.det_conf < DET_CONF_MIN:
        return "needs_review"
    return "confident"
```

- [ ] **Step 6: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_capture_logic.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/backend/app/schemas/capture.py src/backend/app/services/vehicle_groups.py src/backend/app/services/capture.py src/backend/tests/test_capture_logic.py
git commit -m "feat(backend): capture payload schema, representative plate and review_state"
```

---

### Task 3: Endpoint POST /captures idempotent

**Files:**
- Create: `src/backend/app/routers/captures.py`
- Modify: `src/backend/app/main.py`
- Create: `src/backend/tests/test_capture_ingest.py`

**Interfaces:**
- Consumes: `require_edge_key`, `store_encrypted_image`, `select_representative`, `compute_review_state`, `group_for`, `crypto`, `plate_hash`, `PipelinePayload`, `CaptureResponse`.
- Produces: `POST /captures` multipart (`capture_id`, `direction`, `payload` JSON string, `lane`, `image` file), trả `CaptureResponse`; gửi lại cùng `capture_id` trả bản cũ với `duplicate=true`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_capture_ingest.py`:

```python
import json

GOOD_PAYLOAD = {
    "vehicle_type": "car",
    "vehicle_style": "sedan",
    "vehicle_style_conf": 0.8,
    "plates": [{
        "plate_text": "51F-123.45", "det_conf": 0.98, "ocr_conf": 0.9,
        "plate_valid": True, "layout": "1 hàng", "color": "trắng", "color_conf": 0.9,
    }],
}


def _post(client, tmp_path, monkeypatch, capture_id="c1", direction="in", payload=None):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    files = {"image": ("f.jpg", b"\xff\xd8\xff fake", "image/jpeg")}
    data = {"capture_id": capture_id, "direction": direction, "lane": "lane1",
            "payload": json.dumps(payload or GOOD_PAYLOAD)}
    return client.post("/captures", data=data, files=files, headers={"X-Edge-Key": "edge-dev-key"})


def test_ingest_confident_and_encrypted(client, tmp_path, monkeypatch, db_session):
    r = _post(client, tmp_path, monkeypatch)
    assert r.status_code == 200
    body = r.json()
    assert body["review_state"] == "confident"
    assert body["vehicle_group"] == "o_to_con"
    assert body["plate_text"] == "51F-123.45"

    from sqlalchemy import select
    from app.models import PlateReading
    from app.security import crypto, plate
    reading = db_session.scalars(select(PlateReading)).one()
    assert crypto.decrypt_text(reading.plate_text_ciphertext) == "51F-123.45"
    assert reading.plate_hash == plate.plate_hash("51F12345")


def test_idempotent_capture_id(client, tmp_path, monkeypatch, db_session):
    _post(client, tmp_path, monkeypatch, capture_id="dup")
    r2 = _post(client, tmp_path, monkeypatch, capture_id="dup")
    assert r2.json()["duplicate"] is True
    from sqlalchemy import func, select
    from app.models import PlateReading
    count = db_session.scalar(select(func.count()).select_from(PlateReading).where(PlateReading.capture_id == "dup"))
    assert count == 1


def test_needs_review_low_ocr(client, tmp_path, monkeypatch):
    payload = {"vehicle_type": "motorbike", "plates": [
        {"plate_text": "59X1", "det_conf": 0.9, "ocr_conf": 0.4, "plate_valid": True}]}
    r = _post(client, tmp_path, monkeypatch, payload=payload)
    assert r.json()["review_state"] == "needs_review"
    assert r.json()["vehicle_group"] == "xe_may"


def test_needs_review_no_plate(client, tmp_path, monkeypatch):
    payload = {"vehicle_type": "car", "plates": []}
    r = _post(client, tmp_path, monkeypatch, payload=payload)
    assert r.json()["review_state"] == "needs_review"
    assert r.json()["plate_text"] is None


def test_edge_key_required(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    files = {"image": ("f.jpg", b"x", "image/jpeg")}
    data = {"capture_id": "nokey", "direction": "in", "payload": json.dumps(GOOD_PAYLOAD)}
    r = client.post("/captures", data=data, files=files)  # thiếu X-Edge-Key
    assert r.status_code in (401, 422)
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_capture_ingest.py -v`
Expected: FAIL vì route `/captures` chưa có.

- [ ] **Step 3: Viết routers/captures.py**

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_edge_key
from app.models import PlateReading
from app.schemas.capture import CaptureResponse, PipelinePayload
from app.security import crypto
from app.security.plate import plate_hash
from app.services.capture import compute_review_state, select_representative
from app.services.image_store import store_encrypted_image
from app.services.vehicle_groups import group_for

router = APIRouter(tags=["captures"])


def _response(reading: PlateReading, plate_text: str | None, vehicle_group: str | None, duplicate: bool) -> CaptureResponse:
    return CaptureResponse(
        reading_id=reading.id,
        capture_id=reading.capture_id,
        direction=reading.direction,
        review_state=reading.review_state,
        plate_text=plate_text,
        plate_valid=reading.plate_valid,
        vehicle_type=reading.vehicle_type,
        vehicle_group=vehicle_group,
        color=reading.color,
        image_asset_id=reading.image_asset_id,
        duplicate=duplicate,
    )


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

    existing = db.scalars(select(PlateReading).where(PlateReading.capture_id == capture_id)).first()
    if existing is not None:
        text = crypto.decrypt_text(existing.plate_text_ciphertext) if existing.plate_text_ciphertext else None
        return _response(existing, text, group_for(existing.vehicle_type), duplicate=True)

    data = PipelinePayload.model_validate_json(payload)
    raw = image.file.read()
    asset = store_encrypted_image(db, raw, direction)

    rep = select_representative(data.plates)
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
        vehicle_type=data.vehicle_type,
        vehicle_style=data.vehicle_style,
        vehicle_style_conf=data.vehicle_style_conf,
        raw_pipeline_json=data.model_dump(),
        image_asset_id=asset.id,
        review_state=compute_review_state(rep),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return _response(reading, plate_text, group_for(data.vehicle_type), duplicate=False)
```

- [ ] **Step 4: Gắn router captures vào main.py**

Sửa `src/backend/app/main.py`:

```python
from fastapi import FastAPI

from app.routers import auth, captures, users


def create_app() -> FastAPI:
    app = FastAPI(title="Parking backend")
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(captures.router)
    return app


app = create_app()
```

- [ ] **Step 5: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_capture_ingest.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add src/backend/app/routers/captures.py src/backend/app/main.py src/backend/tests/test_capture_ingest.py
git commit -m "feat(backend): idempotent capture ingestion endpoint"
```

---

### Task 4: Script giả lập edge worker

**Files:**
- Create: `src/backend/scripts/__init__.py`
- Create: `src/backend/scripts/simulate_edge.py`
- Create: `src/backend/tests/test_edge_simulator.py`

**Interfaces:**
- Produces: `scripts.simulate_edge.load_payload(img_path: Path) -> dict` (đọc sidecar JSON cùng tên hoặc trả payload rỗng); `post_folder(...)` và `main()` để chạy dòng lệnh.
- Ghi chú: script này POST payload tổng hợp từ file sidecar JSON để test backend trên PC. Nối pipeline thật `src/ml` vào edge worker làm ở Phase 6.
- Ghi chú EINTR: khi chạy trong container đọc thư mục ảnh qua mount chia sẻ của VM (libkrun/virtiofs với Podman trên macOS), `iterdir`/`read_bytes` có thể ném `InterruptedError` (Errno 4). Bọc các thao tác filesystem bằng helper `_retry_eintr` (thử lại vài lần) để không vỡ ở lượt scandir đầu.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_edge_simulator.py`:

```python
import json

from scripts.simulate_edge import load_payload


def test_load_payload_reads_sidecar(tmp_path):
    img = tmp_path / "car.jpg"
    img.write_bytes(b"x")
    (tmp_path / "car.json").write_text(json.dumps({"vehicle_type": "car", "plates": []}))
    assert load_payload(img)["vehicle_type"] == "car"


def test_load_payload_default_when_no_sidecar(tmp_path):
    img = tmp_path / "moto.jpg"
    img.write_bytes(b"x")
    p = load_payload(img)
    assert p["vehicle_type"] is None
    assert p["plates"] == []
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_edge_simulator.py -v`
Expected: FAIL vì `scripts.simulate_edge` chưa có.

- [ ] **Step 3: Tạo package marker scripts**

`src/backend/scripts/__init__.py`: file rỗng.

- [ ] **Step 4: Viết simulate_edge.py**

```python
import argparse
import json
import uuid
from pathlib import Path

import httpx


def load_payload(img_path: Path) -> dict:
    sidecar = img_path.with_suffix(".json")
    if sidecar.exists():
        return json.loads(sidecar.read_text())
    return {"vehicle_type": None, "vehicle_style": None, "vehicle_style_conf": None, "plates": []}


def post_folder(images_dir: str, backend: str, direction: str, lane: str, edge_key: str) -> None:
    for img_path in sorted(Path(images_dir).glob("*.jpg")):
        payload = load_payload(img_path)
        files = {"image": (img_path.name, img_path.read_bytes(), "image/jpeg")}
        data = {
            "capture_id": str(uuid.uuid4()),
            "direction": direction,
            "lane": lane,
            "payload": json.dumps(payload),
        }
        resp = httpx.post(
            f"{backend}/captures", data=data, files=files,
            headers={"X-Edge-Key": edge_key}, timeout=30.0,
        )
        print(img_path.name, resp.status_code, resp.text[:200])


def main() -> None:
    ap = argparse.ArgumentParser(description="Giả lập edge worker: đọc ảnh thư mục và POST /captures")
    ap.add_argument("--images", required=True)
    ap.add_argument("--backend", default="http://localhost:8000")
    ap.add_argument("--direction", default="in", choices=["in", "out"])
    ap.add_argument("--lane", default="lane1")
    ap.add_argument("--edge-key", default="edge-dev-key")
    args = ap.parse_args()
    post_folder(args.images, args.backend, args.direction, args.lane, args.edge_key)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_edge_simulator.py -v`
Expected: PASS cả hai test.

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add src/backend/scripts/__init__.py src/backend/scripts/simulate_edge.py src/backend/tests/test_edge_simulator.py
git commit -m "feat(backend): edge worker simulator script for PC dev"
```

---

### Task 5: Test nghiệm thu Phase 3

Kiểm chứng deliverable cả phase: một capture xe vào biển tốt cho `review_state = confident`, ảnh mã hóa đúng trên đĩa, `plate_hash` khớp; gửi lại cùng `capture_id` không nhân đôi.

**Files:**
- Create: `src/backend/tests/test_phase3_acceptance.py`

**Interfaces:**
- Consumes: `POST /captures`; `app.models.PlateReading`, `app.models.ImageAsset`; `crypto`, `plate`.
- Produces: cổng nghiệm thu, không API mới.

- [ ] **Step 1: Viết test nghiệm thu**

`src/backend/tests/test_phase3_acceptance.py`:

```python
import json
from pathlib import Path

from sqlalchemy import func, select

from app.models import ImageAsset, PlateReading
from app.security import crypto, plate


def test_capture_pipeline_end_to_end(client, tmp_path, monkeypatch, db_session):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))

    payload = {
        "vehicle_type": "car", "vehicle_style": "SUV", "vehicle_style_conf": 0.7,
        "plates": [{"plate_text": "30A-678.90", "det_conf": 0.97, "ocr_conf": 0.88, "plate_valid": True, "color": "trắng"}],
    }
    files = {"image": ("in.jpg", b"\xff\xd8\xff raw", "image/jpeg")}
    data = {"capture_id": "e2e-1", "direction": "in", "lane": "lane1", "payload": json.dumps(payload)}
    h = {"X-Edge-Key": "edge-dev-key"}

    r = client.post("/captures", data=data, files=files, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["review_state"] == "confident"
    assert body["vehicle_group"] == "o_to_con"

    reading = db_session.scalars(select(PlateReading).where(PlateReading.capture_id == "e2e-1")).one()
    assert reading.plate_hash == plate.plate_hash("30A67890")

    asset = db_session.get(ImageAsset, reading.image_asset_id)
    stored = Path(asset.path).read_bytes()
    assert crypto.decrypt_bytes(stored) == b"\xff\xd8\xff raw"

    files2 = {"image": ("in.jpg", b"\xff\xd8\xff raw", "image/jpeg")}
    r2 = client.post("/captures", data=data, files=files2, headers=h)
    assert r2.json()["duplicate"] is True
    assert db_session.scalar(select(func.count()).select_from(PlateReading)) == 1
```

- [ ] **Step 2: Chạy test nghiệm thu**

Run: `cd src/backend && pytest tests/test_phase3_acceptance.py -v`
Expected: PASS.

- [ ] **Step 3: Chạy toàn bộ suite (Phase 1 tới 3)**

Run: `cd src/backend && pytest -v`
Expected: PASS toàn bộ, không lỗi và không skip.

- [ ] **Step 4: Commit (điểm mốc)**

```bash
git add src/backend/tests/test_phase3_acceptance.py
git commit -m "test(backend): phase 3 acceptance for capture ingestion"
```

---

## Self-Review (đã chạy khi soạn plan)

- **Spec coverage phase 3:** nhận capture edge POST multipart cộng `capture_id` idempotent (mục 6 spec) phủ Task 3; biển đại diện `det_conf` cao nhất và ngưỡng soát (mục 2) phủ Task 2; lưu trường bằng chứng `det_conf`, `ocr_conf`, `color`, `layout`, `plate_valid`, style (mục 2, 3) phủ Task 3 khi tạo `PlateReading`; ảnh mã hóa ghi đĩa cộng đường dẫn trong DB (mục 3, 10) phủ Task 1; script giả lập edge chạy PC trước (mục 11) phủ Task 4; `review_state` do backend tính (mục 2, 7) phủ Task 2 và 3.
- **Placeholder scan:** không có; mọi step có code hoặc lệnh.
- **Type consistency:** `PipelinePayload` và `PlateItem` và `CaptureResponse` dùng nhất quán giữa schema, service, router, test; `store_encrypted_image(db, raw, direction)` chữ ký giống nhau ở service, router, test; `group_for`, `select_representative`, `compute_review_state` chữ ký khớp mọi nơi; `X-Edge-Key` alias khớp giữa deps và test.
- **Ghi chú:** thiếu header `X-Edge-Key` trả 422 (Header bắt buộc), sai key trả 401, nên test chấp nhận cả hai.

## Điểm nối sang Phase 4

Phase 4 dùng `PlateReading` (đặc biệt `plate_hash`, `direction`, `vehicle_type`, `review_state`) làm đầu vào xác nhận vào và ra, dùng `group_for` để gán `vehicle_group` cho session, và dùng `deps.get_current_user` cho endpoint xác nhận có nhân viên. Endpoint xác nhận vào và ra thêm ở Phase 4, không sửa `POST /captures` trừ khi cần trả kèm gợi ý khớp.
