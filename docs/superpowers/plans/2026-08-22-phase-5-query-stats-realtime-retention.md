# Phase 5: Tra cứu, thống kê, CSV, cấu hình, WebSocket, job xóa

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** phần dashboard phục vụ: `GET /sessions` lọc và phân trang, `GET /sessions/{id}` chi tiết, `GET /images/{id}` chặn auth cộng audit, `GET /stats` cộng `GET /stats/export` CSV, CRUD `price_rule` và `lane` và `feature_toggle`, `WS /ws/gate` cộng fallback `GET /captures/latest`, và job xóa theo hạn lưu trữ.

**Architecture:** endpoint tra cứu và thống kê truy vấn thẳng DB, tổng hợp theo ngày ở Python để không phụ thuộc dialect. Ảnh giải mã khi phục vụ và ghi audit mỗi lần xem. Gate hub giữ tập hàng đợi asyncio; endpoint capture (chạy threadpool) publish sự kiện qua `call_soon_threadsafe`; WS đọc hàng đợi và đẩy. Job xóa là hàm thuần chạy được qua script và scheduler Phase 6.

**Tech Stack:** FastAPI (WebSocket, StreamingResponse), SQLAlchemy, csv chuẩn, pytest, httpx TestClient.

## Global Constraints

Xem `2026-08-22-dashboard-mvp-plan-index.md`. Riêng phase này: truy cập ảnh chặn auth cộng ghi audit `view_image`; CSV chỉ admin; job xóa xóa session cộng reading cộng file ảnh sau 30 ngày từ `exit_time` cộng ghi audit `delete`; WebSocket cộng fallback polling; commit chờ người dùng; phase khép bằng acceptance test.

## Interfaces Phase 1 tới 4 dùng lại

- `app.models.ParkingSession`, `PlateReading`, `ImageAsset`, `PriceRule`, `Lane`, `FeatureToggle`, `AuditLog`.
- `app.security.crypto`, `app.security.plate.plate_hash`, `app.services.audit.write_audit`, `app.services.image_store.store_encrypted_image`.
- `app.deps.get_current_user`, `app.deps.require_role`, `app.config.settings.retention_days`.
- Router `sessions` (thêm list và detail), `captures` (thêm publish và latest); helper `_session_out`.
- Fixture `client`, `db_session`, `make_user`, `staff_headers`.

## File Structure

- Modify: `src/backend/app/schemas/session.py` thêm schema list và detail.
- Modify: `src/backend/app/routers/sessions.py` thêm `GET /sessions` và `GET /sessions/{id}`.
- Create: `src/backend/app/routers/images.py`.
- Create: `src/backend/app/services/stats.py`, `src/backend/app/routers/stats.py`.
- Create: `src/backend/app/schemas/config.py`, `src/backend/app/routers/config.py`.
- Create: `src/backend/app/services/gate_hub.py`.
- Modify: `src/backend/app/routers/captures.py` thêm publish và `GET /captures/latest`.
- Create: `src/backend/app/routers/gate_ws.py`.
- Create: `src/backend/app/services/retention.py`, `src/backend/scripts/run_retention.py`.
- Modify: `src/backend/app/main.py` gắn router mới.
- Create: `tests/test_session_query.py`, `test_images.py`, `test_stats.py`, `test_config.py`, `test_gate_ws.py`, `test_retention.py`, `test_phase5_acceptance.py`.

---

### Task 1: Danh sách và chi tiết session

**Files:**
- Modify: `src/backend/app/schemas/session.py`
- Modify: `src/backend/app/routers/sessions.py`
- Create: `src/backend/tests/test_session_query.py`

**Interfaces:**
- Consumes: `ParkingSession`, `PlateReading`, `plate_hash`, `crypto`, `get_current_user`.
- Produces: schema `ReadingBrief`, `SessionDetail`, `SessionListResponse`; `GET /sessions?plate=&status=&limit=&offset=` trả `{total, items}`; `GET /sessions/{session_id}` trả `SessionDetail`.

- [ ] **Step 1: Thêm schema vào schemas/session.py**

Thêm vào cuối `src/backend/app/schemas/session.py`:

```python
class ReadingBrief(BaseModel):
    id: int | None = None
    direction: str | None = None
    plate_text: str | None = None
    review_state: str | None = None
    image_asset_id: int | None = None


class SessionDetail(SessionOut):
    vehicle_type: str | None = None
    entry_reading: ReadingBrief | None = None
    exit_reading: ReadingBrief | None = None


class SessionListResponse(BaseModel):
    total: int
    items: list[SessionOut]
```

- [ ] **Step 2: Viết test thất bại**

`src/backend/tests/test_session_query.py`:

```python
from app.models import ParkingSession
from app.security import crypto, plate


def _session(db, plate_text, status="in_lot"):
    s = ParkingSession(plate_hash=plate.plate_hash(plate_text), plate_ciphertext=crypto.encrypt_text(plate_text),
                       vehicle_group="o_to_con", status=status)
    db.add(s); db.commit(); db.refresh(s); return s


def test_list_filters_by_plate(client, db_session, staff_headers):
    _session(db_session, "51F-123.45")
    _session(db_session, "30A-678.90")
    r = client.get("/sessions", params={"plate": "51f 123 45"}, headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["plate_text"] == "51F-123.45"


def test_list_filters_by_status_and_paginates(client, db_session, staff_headers):
    for i in range(3):
        _session(db_session, f"51F-000.0{i}", status="completed")
    _session(db_session, "88H-111.11", status="in_lot")
    r = client.get("/sessions", params={"status": "completed", "limit": 2, "offset": 0}, headers=staff_headers)
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_detail_returns_readings(client, db_session, staff_headers):
    s = _session(db_session, "51F-123.45")
    r = client.get(f"/sessions/{s.id}", headers=staff_headers)
    assert r.status_code == 200
    assert r.json()["plate_text"] == "51F-123.45"


def test_query_requires_auth(client):
    assert client.get("/sessions").status_code in (401, 403)
```

- [ ] **Step 3: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_session_query.py -v`
Expected: FAIL vì route list và detail chưa có.

- [ ] **Step 4: Thêm list và detail vào routers/sessions.py**

Thêm import (nối vào khối import hiện có):

```python
from fastapi import Query
from app.models import PlateReading  # đã dùng ở exit, giữ nếu chưa import
from app.schemas.session import ReadingBrief, SessionDetail, SessionListResponse
from app.security.plate import plate_hash  # đã import cùng normalize_plate; giữ nguyên
```

Thêm vào cuối file:

```python
@router.get("", response_model=SessionListResponse)
def list_sessions(
    plate: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionListResponse:
    stmt = select(ParkingSession)
    if plate:
        stmt = stmt.where(ParkingSession.plate_hash == plate_hash(plate))
    if status_filter:
        stmt = stmt.where(ParkingSession.status == status_filter)
    total = len(list(db.scalars(stmt).all()))
    rows = db.scalars(stmt.order_by(ParkingSession.id.desc()).limit(limit).offset(offset)).all()
    return SessionListResponse(total=total, items=[_session_out(s) for s in rows])


def _reading_brief(db: Session, reading_id: int | None) -> ReadingBrief | None:
    if not reading_id:
        return None
    reading = db.get(PlateReading, reading_id)
    if reading is None:
        return None
    text = crypto.decrypt_text(reading.plate_text_ciphertext) if reading.plate_text_ciphertext else None
    return ReadingBrief(
        id=reading.id, direction=reading.direction, plate_text=text,
        review_state=reading.review_state, image_asset_id=reading.image_asset_id,
    )


@router.get("/{session_id}", response_model=SessionDetail)
def session_detail(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionDetail:
    s = db.get(ParkingSession, session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    base = _session_out(s)
    return SessionDetail(
        **base.model_dump(),
        vehicle_type=s.vehicle_type,
        entry_reading=_reading_brief(db, s.entry_reading_id),
        exit_reading=_reading_brief(db, s.exit_reading_id),
    )
```

- [ ] **Step 5: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_session_query.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add src/backend/app/schemas/session.py src/backend/app/routers/sessions.py src/backend/tests/test_session_query.py
git commit -m "feat(backend): session listing and detail endpoints"
```

---

### Task 2: Truy cập ảnh chặn auth và audit

**Files:**
- Create: `src/backend/app/routers/images.py`
- Modify: `src/backend/app/main.py`
- Create: `src/backend/tests/test_images.py`

**Interfaces:**
- Consumes: `ImageAsset`, `crypto.decrypt_bytes`, `write_audit`, `get_current_user`.
- Produces: `GET /images/{image_id}` trả ảnh giải mã (`image/jpeg`), chặn auth, ghi audit `view_image`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_images.py`:

```python
from sqlalchemy import select

from app.models import AuditLog
from app.services.image_store import store_encrypted_image


def test_view_image_decrypts_and_audits(client, db_session, staff_headers, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    asset = store_encrypted_image(db_session, b"\xff\xd8\xff raw", "in")
    db_session.commit()

    r = client.get(f"/images/{asset.id}", headers=staff_headers)
    assert r.status_code == 200
    assert r.content == b"\xff\xd8\xff raw"

    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "view_image")).all()
    assert len(logs) == 1


def test_view_image_requires_auth(client, db_session, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    asset = store_encrypted_image(db_session, b"x", "in")
    db_session.commit()
    assert client.get(f"/images/{asset.id}").status_code in (401, 403)
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_images.py -v`
Expected: FAIL vì route `/images/{id}` chưa có.

- [ ] **Step 3: Viết routers/images.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import ImageAsset, User
from app.security import crypto
from app.services.audit import write_audit

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    asset = db.get(ImageAsset, image_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy ảnh")
    with open(asset.path, "rb") as f:
        raw = crypto.decrypt_bytes(f.read()) if asset.encrypted else f.read()
    write_audit(db, user_id=user.id, action="view_image", entity_type="image", entity_id=str(image_id))
    db.commit()
    return Response(content=raw, media_type="image/jpeg")
```

- [ ] **Step 4: Gắn router images vào main.py**

Thêm `images` vào import và `app.include_router(images.router)` trong `create_app()` của `src/backend/app/main.py`.

- [ ] **Step 5: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_images.py -v`
Expected: PASS.

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add src/backend/app/routers/images.py src/backend/app/main.py src/backend/tests/test_images.py
git commit -m "feat(backend): authenticated audited image access"
```

---

### Task 3: Thống kê và xuất CSV

**Files:**
- Create: `src/backend/app/services/stats.py`
- Create: `src/backend/app/routers/stats.py`
- Modify: `src/backend/app/main.py`
- Create: `src/backend/tests/test_stats.py`

**Interfaces:**
- Consumes: `ParkingSession`, `get_current_user`, `require_role`.
- Produces: `stats.summary(db, start, end) -> dict`, `stats.daily_rows(db, start, end) -> list[dict]`; `GET /stats?from=&to=`; `GET /stats/export?from=&to=` CSV chỉ admin.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_stats.py`:

```python
from datetime import datetime

from app.models import ParkingSession
from app.security import crypto, plate


def _completed(db, fee, entry, exit_):
    s = ParkingSession(plate_hash=plate.plate_hash("51F-123.45"), plate_ciphertext=crypto.encrypt_text("51F-123.45"),
                       vehicle_group="o_to_con", status="completed", entry_time=entry, exit_time=exit_, fee_amount=fee)
    db.add(s); db.commit(); return s


def test_stats_revenue_and_counts(client, db_session, staff_headers):
    _completed(db_session, 5000, datetime(2026, 8, 22, 8), datetime(2026, 8, 22, 9))
    _completed(db_session, 3000, datetime(2026, 8, 22, 10), datetime(2026, 8, 22, 11))
    db_session.add(ParkingSession(plate_hash="h", plate_ciphertext="", vehicle_group="o_to_con", status="in_lot"))
    db_session.commit()

    r = client.get("/stats", params={"from": "2026-08-22T00:00:00", "to": "2026-08-22T23:59:59"}, headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["in_lot"] == 1
    assert body["exits"] == 2
    assert body["revenue"] == 8000


def test_stats_export_admin_only(client, db_session, make_user):
    make_user(username="stf", password="pw", role="staff")
    make_user(username="adm", password="pw", role="admin")
    st = client.post("/auth/login", json={"username": "stf", "password": "pw"}).json()["access_token"]
    ad = client.post("/auth/login", json={"username": "adm", "password": "pw"}).json()["access_token"]

    assert client.get("/stats/export", headers={"Authorization": f"Bearer {st}"}).status_code == 403
    r = client.get("/stats/export", headers={"Authorization": f"Bearer {ad}"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "date,entries,exits,revenue" in r.text
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_stats.py -v`
Expected: FAIL vì service và route chưa có.

- [ ] **Step 3: Viết services/stats.py**

```python
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ParkingSession

_MIN = datetime(1970, 1, 1)
_MAX = datetime(2999, 1, 1)


def _bounds(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    return (start or _MIN, end or _MAX)


def summary(db: Session, start: datetime | None, end: datetime | None) -> dict:
    lo, hi = _bounds(start, end)
    in_lot = db.scalar(select(func.count()).select_from(ParkingSession).where(ParkingSession.status == "in_lot"))
    entries = db.scalar(select(func.count()).select_from(ParkingSession).where(
        ParkingSession.entry_time.is_not(None), ParkingSession.entry_time >= lo, ParkingSession.entry_time <= hi))
    exits = db.scalar(select(func.count()).select_from(ParkingSession).where(
        ParkingSession.status == "completed", ParkingSession.exit_time.is_not(None),
        ParkingSession.exit_time >= lo, ParkingSession.exit_time <= hi))
    revenue = db.scalar(select(func.coalesce(func.sum(ParkingSession.fee_amount), 0)).where(
        ParkingSession.status == "completed", ParkingSession.exit_time.is_not(None),
        ParkingSession.exit_time >= lo, ParkingSession.exit_time <= hi))
    return {"in_lot": int(in_lot or 0), "entries": int(entries or 0), "exits": int(exits or 0), "revenue": int(revenue or 0)}


def daily_rows(db: Session, start: datetime | None, end: datetime | None) -> list[dict]:
    lo, hi = _bounds(start, end)
    sessions = db.scalars(select(ParkingSession)).all()
    buckets: dict[str, dict] = {}

    def _bucket(day: str) -> dict:
        return buckets.setdefault(day, {"date": day, "entries": 0, "exits": 0, "revenue": 0})

    for s in sessions:
        if s.entry_time and lo <= s.entry_time <= hi:
            _bucket(s.entry_time.date().isoformat())["entries"] += 1
        if s.status == "completed" and s.exit_time and lo <= s.exit_time <= hi:
            b = _bucket(s.exit_time.date().isoformat())
            b["exits"] += 1
            b["revenue"] += s.fee_amount or 0
    return [buckets[k] for k in sorted(buckets)]
```

- [ ] **Step 4: Viết routers/stats.py**

```python
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import User
from app.services import stats as stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return stats_service.summary(db, from_, to)


@router.get("/export")
def export_stats(
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> Response:
    rows = stats_service.daily_rows(db, from_, to)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "entries", "exits", "revenue"])
    for r in rows:
        writer.writerow([r["date"], r["entries"], r["exits"], r["revenue"]])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stats.csv"},
    )
```

- [ ] **Step 5: Gắn router stats vào main.py**

Thêm `stats` vào import và `app.include_router(stats.router)`.

- [ ] **Step 6: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_stats.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/backend/app/services/stats.py src/backend/app/routers/stats.py src/backend/app/main.py src/backend/tests/test_stats.py
git commit -m "feat(backend): statistics summary and CSV export"
```

---

### Task 4: CRUD cấu hình (price_rule, lane, feature_toggle)

**Files:**
- Create: `src/backend/app/schemas/config.py`
- Create: `src/backend/app/routers/config.py`
- Modify: `src/backend/app/main.py`
- Create: `src/backend/tests/test_config.py`

**Interfaces:**
- Consumes: `PriceRule`, `Lane`, `FeatureToggle`, `require_role`, `get_current_user`.
- Produces: `GET /price-rules` (auth), `POST /price-rules` (admin), `PATCH /price-rules/{id}` (admin); `GET/POST/PATCH /lanes`; `GET /feature-toggles` (auth, tạo mặc định nếu chưa có), `PATCH /feature-toggles` (admin).

- [ ] **Step 1: Viết schemas/config.py**

```python
from pydantic import BaseModel


class PriceRuleIn(BaseModel):
    vehicle_group: str
    mode: str  # flat | block
    unit_price: int
    block_minutes: int | None = None
    active: bool = True


class PriceRuleUpdate(BaseModel):
    mode: str | None = None
    unit_price: int | None = None
    block_minutes: int | None = None
    active: bool | None = None


class PriceRuleOut(BaseModel):
    id: int
    vehicle_group: str
    mode: str
    unit_price: int
    block_minutes: int | None = None
    active: bool
    model_config = {"from_attributes": True}


class LaneIn(BaseModel):
    name: str
    rtsp_url: str | None = None
    active: bool = True


class LaneUpdate(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    active: bool | None = None


class LaneOut(BaseModel):
    id: int
    name: str
    rtsp_url: str | None = None
    active: bool
    model_config = {"from_attributes": True}


class ToggleUpdate(BaseModel):
    read_plate: bool | None = None
    plate_color: bool | None = None
    vehicle_class: bool | None = None


class ToggleOut(BaseModel):
    read_plate: bool
    plate_color: bool
    vehicle_class: bool
```

- [ ] **Step 2: Viết test thất bại**

`src/backend/tests/test_config.py`:

```python
def _token(client, make_user, role):
    make_user(username=role, password="pw", role=role)
    return client.post("/auth/login", json={"username": role, "password": "pw"}).json()["access_token"]


def test_price_rule_crud_admin(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'admin')}"}
    r = client.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=h)
    assert r.status_code == 201
    rid = r.json()["id"]
    assert client.get("/price-rules", headers=h).status_code == 200
    r2 = client.patch(f"/price-rules/{rid}", json={"unit_price": 4000}, headers=h)
    assert r2.json()["unit_price"] == 4000


def test_price_rule_create_forbidden_for_staff(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=h)
    assert r.status_code == 403


def test_feature_toggle_get_default_and_update(client, make_user):
    staff_h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.get("/feature-toggles", headers=staff_h)
    assert r.status_code == 200
    assert r.json()["read_plate"] is True

    admin_h = {"Authorization": f"Bearer {_token(client, make_user, 'admin')}"}
    r2 = client.patch("/feature-toggles", json={"read_plate": False}, headers=admin_h)
    assert r2.json()["read_plate"] is False
    assert client.patch("/feature-toggles", json={"read_plate": True}, headers=staff_h).status_code == 403


def test_lane_crud_admin(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'admin')}"}
    r = client.post("/lanes", json={"name": "lane1", "rtsp_url": "rtsp://x"}, headers=h)
    assert r.status_code == 201
    assert client.get("/lanes", headers=h).json()[0]["name"] == "lane1"
```

- [ ] **Step 3: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_config.py -v`
Expected: FAIL vì route chưa có.

- [ ] **Step 4: Viết routers/config.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import FeatureToggle, Lane, PriceRule, User
from app.schemas.config import (
    LaneIn, LaneOut, LaneUpdate, PriceRuleIn, PriceRuleOut, PriceRuleUpdate, ToggleOut, ToggleUpdate,
)

router = APIRouter(tags=["config"])
admin_only = require_role("admin")


@router.get("/price-rules", response_model=list[PriceRuleOut])
def list_price_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(PriceRule).order_by(PriceRule.id)).all())


@router.post("/price-rules", response_model=PriceRuleOut, status_code=status.HTTP_201_CREATED)
def create_price_rule(body: PriceRuleIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if body.mode not in ("flat", "block"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode phải là flat hoặc block")
    rule = PriceRule(**body.model_dump(), updated_by=admin.id)
    db.add(rule); db.commit(); db.refresh(rule)
    return rule


@router.patch("/price-rules/{rule_id}", response_model=PriceRuleOut)
def update_price_rule(rule_id: int, body: PriceRuleUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    rule = db.get(PriceRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bảng giá")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    rule.updated_by = admin.id
    db.commit(); db.refresh(rule)
    return rule


@router.get("/lanes", response_model=list[LaneOut])
def list_lanes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Lane).order_by(Lane.id)).all())


@router.post("/lanes", response_model=LaneOut, status_code=status.HTTP_201_CREATED)
def create_lane(body: LaneIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lane = Lane(**body.model_dump())
    db.add(lane); db.commit(); db.refresh(lane)
    return lane


@router.patch("/lanes/{lane_id}", response_model=LaneOut)
def update_lane(lane_id: int, body: LaneUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lane = db.get(Lane, lane_id)
    if lane is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy lane")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lane, field, value)
    db.commit(); db.refresh(lane)
    return lane


def _get_or_create_toggle(db: Session) -> FeatureToggle:
    toggle = db.scalars(select(FeatureToggle).order_by(FeatureToggle.id)).first()
    if toggle is None:
        toggle = FeatureToggle()
        db.add(toggle); db.commit(); db.refresh(toggle)
    return toggle


@router.get("/feature-toggles", response_model=ToggleOut)
def get_toggles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_or_create_toggle(db)


@router.patch("/feature-toggles", response_model=ToggleOut)
def update_toggles(body: ToggleUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    toggle = _get_or_create_toggle(db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(toggle, field, value)
    db.commit(); db.refresh(toggle)
    return toggle
```

- [ ] **Step 5: Gắn router config vào main.py**

Thêm `config` vào import và `app.include_router(config.router)`.

- [ ] **Step 6: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_config.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/backend/app/schemas/config.py src/backend/app/routers/config.py src/backend/app/main.py src/backend/tests/test_config.py
git commit -m "feat(backend): config CRUD for price rules, lanes and toggles"
```

---

### Task 5: WebSocket cổng và fallback polling

**Files:**
- Create: `src/backend/app/services/gate_hub.py`
- Create: `src/backend/app/routers/gate_ws.py`
- Modify: `src/backend/app/routers/captures.py`
- Modify: `src/backend/app/main.py`
- Create: `src/backend/tests/test_gate_ws.py`

**Interfaces:**
- Produces: `gate_hub.GateHub` với `bind_loop`, `subscribe`, `unsubscribe`, `publish`; instance `gate_hub.gate_hub`; `WS /ws/gate` đẩy sự kiện nhận diện; `GET /captures/latest?lane=` trả reading mới nhất (fallback polling). `POST /captures` publish sự kiện sau khi lưu.

- [ ] **Step 1: Viết gate_hub.py**

```python
import asyncio


class GateHub:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queues: set[asyncio.Queue] = set()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    def publish(self, event: dict) -> None:
        if self._loop is None:
            return
        for queue in list(self._queues):
            self._loop.call_soon_threadsafe(queue.put_nowait, event)


gate_hub = GateHub()
```

- [ ] **Step 2: Viết routers/gate_ws.py**

```python
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.gate_hub import gate_hub

router = APIRouter()


@router.websocket("/ws/gate")
async def ws_gate(ws: WebSocket) -> None:
    gate_hub.bind_loop(asyncio.get_running_loop())
    await ws.accept()
    queue = await gate_hub.subscribe()
    try:
        while True:
            event = await queue.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        gate_hub.unsubscribe(queue)
```

- [ ] **Step 3: Viết test thất bại**

`src/backend/tests/test_gate_ws.py`:

```python
import json


def test_publish_noop_without_loop():
    from app.services.gate_hub import GateHub
    GateHub().publish({"a": 1})  # không lỗi khi chưa bind loop


def test_captures_latest_returns_recent(client, db_session, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    payload = {"vehicle_type": "car", "plates": [{"plate_text": "51F-123.45", "det_conf": 0.9, "ocr_conf": 0.9, "plate_valid": True}]}
    files = {"image": ("f.jpg", b"x", "image/jpeg")}
    data = {"capture_id": "L1", "direction": "in", "lane": "lane1", "payload": json.dumps(payload)}
    client.post("/captures", data=data, files=files, headers={"X-Edge-Key": "edge-dev-key"})

    r = client.get("/captures/latest")
    assert r.status_code == 200
    assert r.json()["capture_id"] == "L1"
    assert r.json()["review_state"] == "confident"


def test_ws_gate_receives_event(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    payload = {"vehicle_type": "car", "plates": [{"plate_text": "30A-1", "det_conf": 0.9, "ocr_conf": 0.9, "plate_valid": True}]}
    with client.websocket_connect("/ws/gate") as ws:
        files = {"image": ("f.jpg", b"x", "image/jpeg")}
        data = {"capture_id": "WS1", "direction": "in", "lane": "lane1", "payload": json.dumps(payload)}
        client.post("/captures", data=data, files=files, headers={"X-Edge-Key": "edge-dev-key"})
        event = ws.receive_json()
    assert event["capture_id"] == "WS1"
    assert event["direction"] == "in"
```

- [ ] **Step 4: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_gate_ws.py -v`
Expected: FAIL vì `/captures/latest` và `/ws/gate` chưa có.

- [ ] **Step 5: Thêm publish và latest vào routers/captures.py**

Thêm import ở đầu `src/backend/app/routers/captures.py`:

```python
from app.schemas.capture import CaptureResponse, PipelinePayload  # đã có; giữ nguyên
from app.services.gate_hub import gate_hub
```

Trong `ingest_capture`, ngay trước `return _response(reading, plate_text, group_for(data.vehicle_type), duplicate=False)`, thêm publish:

```python
    gate_hub.publish({
        "reading_id": reading.id,
        "capture_id": reading.capture_id,
        "direction": reading.direction,
        "lane": reading.lane,
        "review_state": reading.review_state,
        "plate_text": plate_text,
        "vehicle_group": group_for(data.vehicle_type),
    })
```

Thêm endpoint fallback vào cuối file:

```python
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

- [ ] **Step 6: Gắn router gate_ws vào main.py**

Thêm `gate_ws` vào import và `app.include_router(gate_ws.router)`.

- [ ] **Step 7: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_gate_ws.py -v`
Expected: PASS toàn bộ. Nếu `test_ws_gate_receives_event` chập chờn do TestClient, test `test_captures_latest_returns_recent` là đường polling tin cậy vẫn phải PASS; giữ WS test và không xóa.

- [ ] **Step 8: Commit (điểm mốc)**

```bash
git add src/backend/app/services/gate_hub.py src/backend/app/routers/gate_ws.py src/backend/app/routers/captures.py src/backend/app/main.py src/backend/tests/test_gate_ws.py
git commit -m "feat(backend): gate websocket push and latest capture fallback"
```

---

### Task 6: Job xóa theo hạn lưu trữ

**Files:**
- Create: `src/backend/app/services/retention.py`
- Create: `src/backend/scripts/run_retention.py`
- Create: `src/backend/tests/test_retention.py`

**Interfaces:**
- Consumes: `ParkingSession`, `PlateReading`, `ImageAsset`, `write_audit`, `settings.retention_days`.
- Produces: `retention.purge_expired(db, now: datetime | None = None) -> int` (xóa session cộng reading cộng file ảnh sau hạn, ghi audit `delete`); script `run_retention.py`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_retention.py`:

```python
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.models import AuditLog, ParkingSession, PlateReading
from app.services.image_store import store_encrypted_image
from app.services.retention import purge_expired


def _expired_session(db, tmp_path, monkeypatch, days_ago):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "retention_days", 30)
    asset = store_encrypted_image(db, b"img-bytes", "in")
    db.commit()
    reading = PlateReading(capture_id=f"r-{days_ago}", direction="in", image_asset_id=asset.id, review_state="manual")
    db.add(reading); db.commit(); db.refresh(reading)
    when = datetime.utcnow() - timedelta(days=days_ago)
    s = ParkingSession(plate_hash="h", plate_ciphertext="", vehicle_group="o_to_con",
                       status="completed", entry_time=when, exit_time=when, entry_reading_id=reading.id)
    db.add(s); db.commit(); db.refresh(s)
    return s, reading, asset.path


def test_purge_removes_expired(db_session, tmp_path, monkeypatch):
    s, reading, path = _expired_session(db_session, tmp_path, monkeypatch, days_ago=40)
    assert Path(path).exists()

    n = purge_expired(db_session)
    assert n == 1
    assert not Path(path).exists()
    assert db_session.get(ParkingSession, s.id) is None
    assert db_session.get(PlateReading, reading.id) is None
    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "delete")).all()
    assert len(logs) == 1


def test_purge_keeps_recent(db_session, tmp_path, monkeypatch):
    s, reading, path = _expired_session(db_session, tmp_path, monkeypatch, days_ago=5)
    assert purge_expired(db_session) == 0
    assert db_session.get(ParkingSession, s.id) is not None
    assert Path(path).exists()
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_retention.py -v`
Expected: FAIL vì `app.services.retention` chưa có.

- [ ] **Step 3: Viết retention.py**

```python
import os
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_utc
from app.config import settings
from app.models import ImageAsset, ParkingSession, PlateReading
from app.services.audit import write_audit


def purge_expired(db: Session, now: datetime | None = None) -> int:
    now = now or now_utc()  # UTC naive, xem app/clock.py (Phase 4)
    cutoff = now - timedelta(days=settings.retention_days)
    sessions = db.scalars(
        select(ParkingSession).where(
            ParkingSession.status.in_(["completed", "disputed"]),
            ParkingSession.exit_time.is_not(None),
            ParkingSession.exit_time <= cutoff,
        )
    ).all()

    count = 0
    for s in sessions:
        reading_ids = [rid for rid in (s.entry_reading_id, s.exit_reading_id) if rid]
        write_audit(db, user_id=None, action="delete", entity_type="session", entity_id=str(s.id))
        db.delete(s)
        db.flush()
        for rid in reading_ids:
            reading = db.get(PlateReading, rid)
            if reading is None:
                continue
            asset_id = reading.image_asset_id
            db.delete(reading)
            db.flush()
            if asset_id:
                asset = db.get(ImageAsset, asset_id)
                if asset:
                    try:
                        os.remove(asset.path)
                    except FileNotFoundError:
                        pass
                    db.delete(asset)
        count += 1

    db.commit()
    return count
```

- [ ] **Step 4: Viết script run_retention.py**

`src/backend/scripts/run_retention.py`:

```python
from app.db import SessionLocal
from app.services.retention import purge_expired


def main() -> None:
    db = SessionLocal()
    try:
        n = purge_expired(db)
        print(f"purged {n} sessions")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_retention.py -v`
Expected: PASS cả hai test.

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add src/backend/app/services/retention.py src/backend/scripts/run_retention.py src/backend/tests/test_retention.py
git commit -m "feat(backend): retention purge job for expired records"
```

---

### Task 7: Test nghiệm thu Phase 5

Kiểm chứng deliverable cả phase: tra cứu lọc theo biển, xem ảnh ghi audit, thống kê doanh thu, và job xóa dữ liệu quá hạn.

**Files:**
- Create: `src/backend/tests/test_phase5_acceptance.py`

**Interfaces:**
- Consumes: `/sessions`, `/images/{id}`, `/stats`; `purge_expired`.
- Produces: cổng nghiệm thu.

- [ ] **Step 1: Viết test nghiệm thu**

`src/backend/tests/test_phase5_acceptance.py`:

```python
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.models import AuditLog, ParkingSession, PlateReading
from app.security import crypto, plate
from app.services.image_store import store_encrypted_image
from app.services.retention import purge_expired


def test_dashboard_and_retention(client, db_session, staff_headers, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "retention_days", 30)

    asset = store_encrypted_image(db_session, b"\xff\xd8\xff raw", "in")
    db_session.commit()
    reading = PlateReading(capture_id="acc-in", direction="in", image_asset_id=asset.id, review_state="confident")
    db_session.add(reading); db_session.commit(); db_session.refresh(reading)

    old = datetime.utcnow() - timedelta(days=40)
    s = ParkingSession(plate_hash=plate.plate_hash("51F-123.45"), plate_ciphertext=crypto.encrypt_text("51F-123.45"),
                       vehicle_group="o_to_con", status="completed", entry_time=old, exit_time=old,
                       fee_amount=5000, entry_reading_id=reading.id)
    db_session.add(s); db_session.commit()

    # tra cứu theo biển
    r = client.get("/sessions", params={"plate": "51F-123.45"}, headers=staff_headers)
    assert r.json()["total"] == 1

    # xem ảnh ghi audit
    assert client.get(f"/images/{asset.id}", headers=staff_headers).content == b"\xff\xd8\xff raw"
    assert db_session.scalars(select(AuditLog).where(AuditLog.action == "view_image")).all()

    # thống kê doanh thu toàn thời gian
    stats = client.get("/stats", headers=staff_headers).json()
    assert stats["revenue"] == 5000

    # job xóa dữ liệu quá hạn
    path = asset.path
    assert purge_expired(db_session) == 1
    assert not Path(path).exists()
    assert db_session.get(ParkingSession, s.id) is None
```

- [ ] **Step 2: Chạy test nghiệm thu**

Run: `cd src/backend && pytest tests/test_phase5_acceptance.py -v`
Expected: PASS.

- [ ] **Step 3: Chạy toàn bộ suite (Phase 1 tới 5)**

Run: `cd src/backend && pytest -v`
Expected: PASS toàn bộ, không lỗi và không skip.

- [ ] **Step 4: Commit (điểm mốc)**

```bash
git add src/backend/tests/test_phase5_acceptance.py
git commit -m "test(backend): phase 5 acceptance for dashboard endpoints and retention"
```

---

## Self-Review (đã chạy khi soạn plan)

- **Spec coverage phase 5:** tra cứu lọc theo biển và trạng thái cộng phân trang phía server (mục 7) phủ Task 1; xem ảnh vào ra (mục 7) và chặn auth cộng audit truy cập ảnh (mục 9, 10) phủ Task 2; thống kê số xe trong bãi và lưu lượng và doanh thu truy vấn thẳng (mục 7) phủ Task 3; xuất CSV cho buổi bảo vệ (mục 6, 7) phủ Task 3; CRUD bảng giá và lane RTSP và toggle (mục 8, cấu hình) phủ Task 4; WebSocket đẩy sự kiện cộng fallback polling (mục 6) phủ Task 5; job xóa theo hạn lưu trữ cộng audit (mục 10) phủ Task 6.
- **Placeholder scan:** không có; mọi step có code hoặc lệnh.
- **Type consistency:** `summary` và `daily_rows` chữ ký khớp giữa service và router và test; `gate_hub.publish` và `subscribe` dùng nhất quán giữa hub, WS, captures; schema config `PriceRuleOut`, `LaneOut`, `ToggleOut` khớp router và test; `purge_expired(db, now)` khớp service, script, test.
- **Ghi chú:** `list_sessions` đếm `total` bằng cách nạp rồi len cho đơn giản và portable; nếu dữ liệu lớn thật, đổi sang `func.count` với cùng điều kiện where (không đổi hợp đồng API).
- **Ghi chú tz:** `daily_rows` so sánh mốc thời gian trong Python nên phải coerce `entry_time`/`exit_time` về naive bằng `app.clock.to_naive` (Postgres trả aware, SQLite trả naive), nếu không so sánh aware với biên naive sẽ `TypeError`. `summary` dùng so sánh ở tầng SQL nên không dính. Cùng lỗi họ với `compute_fee` ở Phase 4.

## Điểm nối sang Phase 6

Phase 6 đóng gói backend cộng Postgres cộng frontend cộng edge worker bằng Podman; chạy `run_retention.py` định kỳ qua scheduler hoặc cron trong compose; biến môi trường cấp `FERNET_KEY`, `HMAC_KEY`, `JWT_SECRET`, `EDGE_API_KEY`, `DATABASE_URL`; volume giữ Postgres và thư mục ảnh mã hóa.
