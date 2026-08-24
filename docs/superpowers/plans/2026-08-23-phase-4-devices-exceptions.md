# Phase 4: Devices, barrier control and exceptions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** thêm điều khiển barie (tự động, mở tay có lý do, mở khẩn cấp) với audit; nhịp sống thiết bị và cảnh báo offline; xử lý ngoại lệ vào ra: xe ra không có phiên vào (mất vé) áp phí phạt, và tra cứu xe quá hạn; nhật ký sự cố.

**Architecture:** ba model mới `Device`, `BarrierEvent`, `Incident`. Service `device` (nhịp sống, sức khỏe) và `exceptions` (mất vé, quá hạn). Router `devices` (gồm barie) và `incidents`. Mọi hành động mở tay và khẩn cấp ghi `audit_log` qua `write_audit` hiện có.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 sync, Alembic, pydantic v2, pytest.

## Global Constraints

Kế thừa index mục Global Constraints. Riêng phase này:
- Khóa chính số nguyên cục bộ. `Device.lot_id` FK `parking_lot.id` (nullable). `BarrierEvent` và `Incident` có `session_id` FK `session.id` nullable, `user_id` FK `users.id` nullable.
- Barie `mode`: `auto`, `manual`, `emergency`. `manual` và `emergency` bắt buộc có `reason`; thiếu thì HTTP 422. Mọi lần mở `manual` và `emergency` ghi một dòng `audit_log`.
- Nhịp sống: `POST /devices/{id}/heartbeat` cập nhật `last_heartbeat = now` và `status = online`. Sức khỏe: thiết bị coi là offline nếu `last_heartbeat` cũ hơn ngưỡng (mặc định 60 giây) hoặc chưa từng có nhịp.
- Mất vé (xe ra không có phiên vào): tạo phiên `completed` với `match_flag = "lost_ticket"`, `fee_amount = penalty_amount`, `exit_time = now`, `exit_reading_id = reading.id`; ghi audit.
- Quá hạn: liệt kê phiên `in_lot` có `entry_time` cũ hơn `hours` giờ.
- Bảo vệ endpoint bằng `get_current_user`; heartbeat cho phép `require_edge_key` hoặc `get_current_user` (chọn `get_current_user` để đơn giản, kiosk đăng nhập gọi).
- Không dùng ký tự gạch ngang trong văn xuôi tài liệu.
- Test trên SQLite in-memory qua `db_session`, `client`, `staff_headers`, `make_reading` (fixture phase 1).

---

### Task 1: Model `Device`, `BarrierEvent`, `Incident`; migration; schema test

**Files:**
- Create: `src/backend/app/models/device.py`
- Create: `src/backend/app/models/barrier_event.py`
- Create: `src/backend/app/models/incident.py`
- Modify: `src/backend/app/models/__init__.py`
- Create: `src/backend/alembic/versions/c3d4e5f6a7b8_add_device_barrier_incident.py`
- Test: `src/backend/tests/test_devices_schema.py`

**Interfaces:**
- Produces: `Device(id:int, lot_id:int|None, kind:str, name:str, lane:str|None, status:str, last_heartbeat:datetime|None, created_at:datetime)`; `BarrierEvent(id:int, device_id:int|None, session_id:int|None, action:str, mode:str, reason:str|None, user_id:int|None, created_at:datetime)`; `Incident(id:int, lot_id:int|None, session_id:int|None, kind:str, description:str|None, image_asset_id:int|None, user_id:int|None, created_at:datetime)`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_devices_schema.py`:

```python
def test_new_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401
    for t in ("device", "barrier_event", "incident"):
        assert t in Base.metadata.tables


def test_device_columns():
    from app.models import Device
    cols = Device.__table__.columns.keys()
    for c in ("lot_id", "kind", "name", "status", "last_heartbeat"):
        assert c in cols


def test_barrier_and_incident_columns():
    from app.models import BarrierEvent, Incident
    for c in ("action", "mode", "reason", "user_id"):
        assert c in BarrierEvent.__table__.columns.keys()
    for c in ("kind", "description", "image_asset_id", "user_id"):
        assert c in Incident.__table__.columns.keys()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_devices_schema.py -v`
Expected: FAIL (KeyError).

- [ ] **Step 3: Create the models**

Create `src/backend/app/models/device.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Device(Base):
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("parking_lot.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))   # barrier | camera | led
    name: Mapped[str] = mapped_column(String(64))
    lane: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(8), default="online")  # online | offline
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Create `src/backend/app/models/barrier_event.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BarrierEvent(Base):
    __tablename__ = "barrier_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("device.id"), nullable=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("session.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(8))   # open | close
    mode: Mapped[str] = mapped_column(String(12))    # auto | manual | emergency
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Create `src/backend/app/models/incident.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Incident(Base):
    __tablename__ = "incident"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("parking_lot.id"), nullable=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("session.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(24))   # collision | lost_vehicle | damage | other
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_asset_id: Mapped[int | None] = mapped_column(ForeignKey("image_asset.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Register the models**

In `src/backend/app/models/__init__.py`, add imports and `__all__` entries for `BarrierEvent`, `Device`, `Incident`:

```python
from app.models.barrier_event import BarrierEvent
from app.models.device import Device
from app.models.incident import Incident
```

Add `"BarrierEvent"`, `"Device"`, `"Incident"` to `__all__`.

- [ ] **Step 5: Run schema test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_devices_schema.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Write the migration**

Create `src/backend/alembic/versions/c3d4e5f6a7b8_add_device_barrier_incident.py`:

```python
"""add device, barrier_event, incident tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("lane", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=8), nullable=False, server_default="online"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "barrier_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("device.id"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("session.id"), nullable=True),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("mode", sa.String(length=12), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "incident",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("session.id"), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_asset_id", sa.Integer(), sa.ForeignKey("image_asset.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("incident")
    op.drop_table("barrier_event")
    op.drop_table("device")
```

- [ ] **Step 7: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/models/device.py src/backend/app/models/barrier_event.py src/backend/app/models/incident.py src/backend/app/models/__init__.py src/backend/alembic/versions/c3d4e5f6a7b8_add_device_barrier_incident.py src/backend/tests/test_devices_schema.py
git commit -m "feat(backend): add device, barrier event, incident models"
```

---

### Task 2: Nhịp sống và sức khỏe thiết bị

**Files:**
- Create: `src/backend/app/services/device.py`
- Create: `src/backend/app/schemas/device.py`
- Create: `src/backend/app/routers/devices.py`
- Modify: `src/backend/app/main.py`
- Test: `src/backend/tests/test_devices_health.py`

**Interfaces:**
- Consumes: `Device` (Task 1); `now_utc`, `to_naive` (`app/clock.py`); `get_current_user`, `require_role`, `User`.
- Produces: `device_health(db, stale_seconds:int=60) -> list[dict]` mỗi dict `device_id, name, kind, status, last_heartbeat, online`; `POST /devices` (admin), `GET /devices`, `POST /devices/{id}/heartbeat`, `GET /devices/health`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_devices_health.py`:

```python
def test_heartbeat_marks_online(client, admin_headers, staff_headers):
    dev = client.post("/devices", json={"kind": "camera", "name": "cam-1"}, headers=admin_headers).json()
    hb = client.post(f"/devices/{dev['id']}/heartbeat", headers=staff_headers)
    assert hb.status_code == 200
    health = client.get("/devices/health", headers=staff_headers).json()
    row = next(r for r in health if r["device_id"] == dev["id"])
    assert row["online"] is True


def test_device_without_heartbeat_is_offline(client, admin_headers, staff_headers):
    dev = client.post("/devices", json={"kind": "barrier", "name": "bar-1"}, headers=admin_headers).json()
    health = client.get("/devices/health", headers=staff_headers).json()
    row = next(r for r in health if r["device_id"] == dev["id"])
    assert row["online"] is False


def test_create_device_admin_only(client, staff_headers):
    assert client.post("/devices", json={"kind": "camera", "name": "x"}, headers=staff_headers).status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_devices_health.py -v`
Expected: FAIL (404 on `/devices`).

- [ ] **Step 3: Write the service**

Create `src/backend/app/services/device.py`:

```python
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_utc, to_naive
from app.models import Device


def _is_online(dev: Device, stale_seconds: int) -> bool:
    if dev.last_heartbeat is None:
        return False
    delta = to_naive(now_utc()) - to_naive(dev.last_heartbeat)
    return delta <= timedelta(seconds=stale_seconds)


def record_heartbeat(db: Session, device: Device) -> Device:
    device.last_heartbeat = now_utc()
    device.status = "online"
    db.commit(); db.refresh(device)
    return device


def device_health(db: Session, stale_seconds: int = 60) -> list[dict]:
    rows = []
    for dev in db.scalars(select(Device).order_by(Device.id)).all():
        rows.append({
            "device_id": dev.id, "name": dev.name, "kind": dev.kind,
            "status": dev.status, "last_heartbeat": dev.last_heartbeat,
            "online": _is_online(dev, stale_seconds),
        })
    return rows
```

- [ ] **Step 4: Write the schemas**

Create `src/backend/app/schemas/device.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class DeviceIn(BaseModel):
    kind: str            # barrier | camera | led
    name: str
    lot_id: int | None = None
    lane: str | None = None


class DeviceOut(BaseModel):
    id: int
    lot_id: int | None = None
    kind: str
    name: str
    lane: str | None = None
    status: str
    last_heartbeat: datetime | None = None
    model_config = {"from_attributes": True}


class DeviceHealthOut(BaseModel):
    device_id: int
    name: str
    kind: str
    status: str
    last_heartbeat: datetime | None = None
    online: bool
```

- [ ] **Step 5: Write the router**

Create `src/backend/app/routers/devices.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import Device, User
from app.schemas.device import DeviceHealthOut, DeviceIn, DeviceOut
from app.services.device import device_health, record_heartbeat

router = APIRouter(tags=["devices"])
admin_only = require_role("admin")


@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(body: DeviceIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    device = Device(**body.model_dump())
    db.add(device); db.commit(); db.refresh(device)
    return device


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Device).order_by(Device.id)).all())


@router.post("/devices/{device_id}/heartbeat", response_model=DeviceOut)
def heartbeat(device_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy thiết bị")
    return record_heartbeat(db, device)


@router.get("/devices/health", response_model=list[DeviceHealthOut])
def health(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return device_health(db)
```

- [ ] **Step 6: Register the router**

In `src/backend/app/main.py`, add `devices` to the routers import line and add `app.include_router(devices.router)`.

- [ ] **Step 7: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_devices_health.py -v`
Expected: PASS (3 tests).

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/services/device.py src/backend/app/schemas/device.py src/backend/app/routers/devices.py src/backend/app/main.py src/backend/tests/test_devices_health.py
git commit -m "feat(backend): add device registry, heartbeat and health"
```

---

### Task 3: Điều khiển barie với audit

**Files:**
- Modify: `src/backend/app/routers/devices.py`
- Create: `src/backend/app/schemas/barrier.py`
- Test: `src/backend/tests/test_barrier.py`

**Interfaces:**
- Consumes: `BarrierEvent` (Task 1); `write_audit` (`app/services/audit.py`); `get_current_user`, `User`.
- Produces: `POST /barrier/open {device_id?, session_id?, mode, reason?}` tạo `BarrierEvent(action="open")`; `manual` và `emergency` bắt buộc `reason` (thiếu trả 422) và ghi audit. `GET /barrier/events?limit=` liệt kê gần nhất.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_barrier.py`:

```python
def test_auto_open_no_reason_ok(client, staff_headers):
    r = client.post("/barrier/open", json={"mode": "auto"}, headers=staff_headers)
    assert r.status_code == 201
    assert r.json()["mode"] == "auto"


def test_manual_open_requires_reason(client, staff_headers):
    assert client.post("/barrier/open", json={"mode": "manual"}, headers=staff_headers).status_code == 422
    ok = client.post("/barrier/open", json={"mode": "manual", "reason": "khách quên vé"}, headers=staff_headers)
    assert ok.status_code == 201


def test_manual_open_writes_audit(client, staff_headers, db_session):
    from app.models import AuditLog
    client.post("/barrier/open", json={"mode": "emergency", "reason": "PCCC"}, headers=staff_headers)
    audits = db_session.query(AuditLog).filter(AuditLog.action == "barrier_open").all()
    assert len(audits) >= 1
    assert "PCCC" in (audits[-1].detail or "")


def test_list_barrier_events(client, staff_headers):
    client.post("/barrier/open", json={"mode": "auto"}, headers=staff_headers)
    events = client.get("/barrier/events?limit=10", headers=staff_headers).json()
    assert len(events) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_barrier.py -v`
Expected: FAIL (404 on `/barrier/open`).

- [ ] **Step 3: Write the schemas**

Create `src/backend/app/schemas/barrier.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class BarrierOpenIn(BaseModel):
    mode: str                      # auto | manual | emergency
    device_id: int | None = None
    session_id: int | None = None
    reason: str | None = None


class BarrierEventOut(BaseModel):
    id: int
    device_id: int | None = None
    session_id: int | None = None
    action: str
    mode: str
    reason: str | None = None
    user_id: int | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Add the barrier routes**

In `src/backend/app/routers/devices.py`, extend imports:

```python
from app.models import BarrierEvent, Device, User
from app.schemas.barrier import BarrierEventOut, BarrierOpenIn
from app.services.audit import write_audit
```

Append these routes to the file:

```python
@router.post("/barrier/open", response_model=BarrierEventOut, status_code=status.HTTP_201_CREATED)
def open_barrier(body: BarrierOpenIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.mode not in ("auto", "manual", "emergency"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode không hợp lệ")
    if body.mode in ("manual", "emergency") and not body.reason:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mở tay và khẩn cấp cần lý do")

    event = BarrierEvent(
        device_id=body.device_id, session_id=body.session_id,
        action="open", mode=body.mode, reason=body.reason, user_id=user.id,
    )
    db.add(event)
    if body.mode in ("manual", "emergency"):
        write_audit(
            db, user_id=user.id, action="barrier_open", entity_type="barrier",
            entity_id=str(body.device_id) if body.device_id else None,
            detail=f"mode={body.mode} reason={body.reason}",
        )
    db.commit(); db.refresh(event)
    return event


@router.get("/barrier/events", response_model=list[BarrierEventOut])
def list_barrier_events(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(
        select(BarrierEvent).order_by(BarrierEvent.id.desc()).limit(limit)
    ).all())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_barrier.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/routers/devices.py src/backend/app/schemas/barrier.py src/backend/tests/test_barrier.py
git commit -m "feat(backend): add barrier open control with audit"
```

---

### Task 4: Nhật ký sự cố

**Files:**
- Create: `src/backend/app/schemas/incident.py`
- Create: `src/backend/app/routers/incidents.py`
- Modify: `src/backend/app/main.py`
- Test: `src/backend/tests/test_incidents.py`

**Interfaces:**
- Consumes: `Incident` (Task 1); `get_current_user`, `User`.
- Produces: `POST /incidents {kind, description?, lot_id?, session_id?, image_asset_id?}`, `GET /incidents?session_id=`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_incidents.py`:

```python
def test_create_and_list_incident(client, staff_headers):
    r = client.post("/incidents", json={"kind": "collision", "description": "va chạm nhẹ"}, headers=staff_headers)
    assert r.status_code == 201
    assert r.json()["kind"] == "collision"
    listed = client.get("/incidents", headers=staff_headers).json()
    assert len(listed) >= 1


def test_filter_incident_by_session(client, staff_headers):
    client.post("/incidents", json={"kind": "damage", "session_id": 7}, headers=staff_headers)
    listed = client.get("/incidents?session_id=7", headers=staff_headers).json()
    assert all(i["session_id"] == 7 for i in listed)
    assert len(listed) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_incidents.py -v`
Expected: FAIL (404 on `/incidents`).

- [ ] **Step 3: Write the schemas**

Create `src/backend/app/schemas/incident.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class IncidentIn(BaseModel):
    kind: str                       # collision | lost_vehicle | damage | other
    description: str | None = None
    lot_id: int | None = None
    session_id: int | None = None
    image_asset_id: int | None = None


class IncidentOut(BaseModel):
    id: int
    kind: str
    description: str | None = None
    lot_id: int | None = None
    session_id: int | None = None
    image_asset_id: int | None = None
    user_id: int | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Write the router**

Create `src/backend/app/routers/incidents.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Incident, User
from app.schemas.incident import IncidentIn, IncidentOut

router = APIRouter(tags=["incidents"])


@router.post("/incidents", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(body: IncidentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    incident = Incident(**body.model_dump(), user_id=user.id)
    db.add(incident); db.commit(); db.refresh(incident)
    return incident


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(session_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Incident).order_by(Incident.id.desc())
    if session_id is not None:
        stmt = stmt.where(Incident.session_id == session_id)
    return list(db.scalars(stmt).all())
```

- [ ] **Step 5: Register the router**

In `src/backend/app/main.py`, add `incidents` to the routers import line and add `app.include_router(incidents.router)`.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_incidents.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/schemas/incident.py src/backend/app/routers/incidents.py src/backend/app/main.py src/backend/tests/test_incidents.py
git commit -m "feat(backend): add incident logging"
```

---

### Task 5: Ngoại lệ vào ra: mất vé và quá hạn

**Files:**
- Modify: `src/backend/app/routers/sessions.py`
- Modify: `src/backend/app/schemas/session.py`
- Test: `src/backend/tests/test_exceptions.py`

**Interfaces:**
- Consumes: `ParkingSession`, `PlateReading` (đã import trong `sessions.py`); `now_utc`; `write_audit`; `group_for`; `_session_out`, `_set_retention` (helpers có sẵn trong `sessions.py`).
- Produces: `POST /sessions/lost-ticket {reading_id, penalty_amount, vehicle_group?}` tạo phiên `completed` `match_flag="lost_ticket"`; `GET /sessions/overstay?hours=` liệt kê phiên `in_lot` quá hạn.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_exceptions.py`:

```python
def test_lost_ticket_creates_penalty_session(client, staff_headers, make_reading, db_session):
    reading = make_reading(plate="51F55555", direction="out")
    r = client.post("/sessions/lost-ticket",
                    json={"reading_id": reading.id, "penalty_amount": 50000, "vehicle_group": "o_to_con"},
                    headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["fee_amount"] == 50000
    assert body["match_flag"] == "lost_ticket"
    from app.models import AuditLog
    assert db_session.query(AuditLog).filter(AuditLog.action == "lost_ticket").count() >= 1


def test_lost_ticket_requires_out_reading(client, staff_headers, make_reading):
    reading = make_reading(plate="51F66666", direction="in")
    r = client.post("/sessions/lost-ticket", json={"reading_id": reading.id, "penalty_amount": 1}, headers=staff_headers)
    assert r.status_code == 404


def test_overstay_lists_old_in_lot(client, staff_headers, db_session):
    from datetime import timedelta
    from app.clock import now_utc
    from app.models import ParkingSession
    old = ParkingSession(plate_hash="h1", plate_ciphertext="x", vehicle_group="o_to_con",
                         status="in_lot", entry_time=now_utc() - timedelta(hours=30))
    fresh = ParkingSession(plate_hash="h2", plate_ciphertext="x", vehicle_group="o_to_con",
                           status="in_lot", entry_time=now_utc())
    db_session.add_all([old, fresh]); db_session.commit()
    rows = client.get("/sessions/overstay?hours=24", headers=staff_headers).json()
    ids = {r["id"] for r in rows}
    assert old.id in ids and fresh.id not in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_exceptions.py -v`
Expected: FAIL (404 trên các route mới).

- [ ] **Step 3: Add schemas**

In `src/backend/app/schemas/session.py`, add:

```python
class LostTicketRequest(BaseModel):
    reading_id: int
    penalty_amount: int
    vehicle_group: str | None = None
```

- [ ] **Step 4: Add the endpoints**

In `src/backend/app/routers/sessions.py`, extend imports to include `timedelta`, `write_audit`, and `Query` (some already present):

```python
from datetime import timedelta
from app.services.audit import write_audit
```

(`Query` and `now_utc` are already imported.)

Add the schema to the existing `app.schemas.session` import list: add `LostTicketRequest`.

Add these routes to the router (after `resolve_session`):

```python
@router.post("/lost-ticket", response_model=SessionOut)
def lost_ticket(body: LostTicketRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    reading = db.get(PlateReading, body.reading_id)
    if reading is None or reading.direction != "out":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading ra hợp lệ")
    group = body.vehicle_group or group_for(reading.vehicle_type) or "unknown"
    session = ParkingSession(
        plate_hash=reading.plate_hash or "",
        plate_ciphertext=reading.plate_text_ciphertext or "",
        vehicle_group=group,
        vehicle_type=reading.vehicle_type,
        status="completed",
        exit_time=now_utc(),
        exit_reading_id=reading.id,
        fee_amount=body.penalty_amount,
        match_flag="lost_ticket",
        closed_by=user.id,
    )
    db.add(session)
    _set_retention(db, session)
    write_audit(db, user_id=user.id, action="lost_ticket", entity_type="session",
                entity_id=None, detail=f"penalty={body.penalty_amount} group={group}")
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.get("/overstay", response_model=list[SessionOut])
def overstay(hours: int = Query(24, ge=1), db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SessionOut]:
    cutoff = now_utc() - timedelta(hours=hours)
    rows = db.scalars(
        select(ParkingSession).where(
            ParkingSession.status == "in_lot",
            ParkingSession.entry_time.is_not(None),
            ParkingSession.entry_time < cutoff,
        ).order_by(ParkingSession.entry_time)
    ).all()
    return [_session_out(s) for s in rows]
```

Note: `_set_retention` runs before `db.commit()`; it reads `session.exit_time` which is set above, so retention is scheduled for the penalty session's readings.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_exceptions.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/routers/sessions.py src/backend/app/schemas/session.py src/backend/tests/test_exceptions.py
git commit -m "feat(backend): add lost-ticket penalty and overstay listing"
```

---

### Task 6: Test nghiệm thu phase và chạy toàn suite

**Files:**
- Test: `src/backend/tests/test_phase4_devices_exceptions_acceptance.py`

**Interfaces:**
- Consumes: mọi thứ Task 1 tới 5.

- [ ] **Step 1: Write the acceptance test**

Create `src/backend/tests/test_phase4_devices_exceptions_acceptance.py`:

```python
def test_barrier_device_and_exception_flow(client, admin_headers, staff_headers, make_reading, db_session):
    # thiết bị barie có nhịp sống thì online
    dev = client.post("/devices", json={"kind": "barrier", "name": "cong-1"}, headers=admin_headers).json()
    client.post(f"/devices/{dev['id']}/heartbeat", headers=staff_headers)
    health = {r["device_id"]: r for r in client.get("/devices/health", headers=staff_headers).json()}
    assert health[dev["id"]]["online"] is True

    # mở barie tay có lý do, ghi audit
    ev = client.post("/barrier/open", json={"mode": "manual", "reason": "khách quên vé", "device_id": dev["id"]}, headers=staff_headers)
    assert ev.status_code == 201

    # xe ra không có phiên vào: mất vé, phí phạt
    reading = make_reading(plate="51F77777", direction="out")
    lt = client.post("/sessions/lost-ticket", json={"reading_id": reading.id, "penalty_amount": 60000}, headers=staff_headers).json()
    assert lt["match_flag"] == "lost_ticket" and lt["fee_amount"] == 60000

    # sự cố ghi lại
    inc = client.post("/incidents", json={"kind": "other", "description": "kiểm tra"}, headers=staff_headers)
    assert inc.status_code == 201

    from app.models import AuditLog
    actions = {a.action for a in db_session.query(AuditLog).all()}
    assert "barrier_open" in actions and "lost_ticket" in actions
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd src/backend && python -m pytest tests/test_phase4_devices_exceptions_acceptance.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS toàn bộ.

- [ ] **Step 4: Commit**

```bash
git add src/backend/tests/test_phase4_devices_exceptions_acceptance.py
git commit -m "test(backend): phase 4 devices, barrier and exceptions acceptance"
```

---

## Self-Review

**Spec coverage (spec kiến trúc mục 6.1, 6.7, 6.11; frontend v2 mục 5.2, 5.9):** barie mở tự động/tay/khẩn cấp cộng audit (Task 3), nhịp sống và cảnh báo offline (Task 2), mất vé (Task 5), quá hạn (Task 5), nhật ký sự cố (Task 4), thiết bị camera và led đăng ký được (Task 2 kind). Cảnh báo doanh thu bất thường và bảng đèn để phase báo cáo và tích hợp phần cứng sau, không phải gap.

**Placeholder scan:** không có TBD; mọi bước có code thật.

**Type consistency:** `device_health(...) -> list[dict{device_id, online, ...}]` khớp giữa service (Task 2), schema `DeviceHealthOut` (Task 2), và test (Task 2, 6). `write_audit(db, user_id=, action=, entity_type=, entity_id=, detail=)` dùng đúng chữ ký hiện có ở Task 3 và 5. `BarrierEvent`, `Incident`, `Device` field khớp model (Task 1) và schema. `_session_out`, `_set_retention` là helper có sẵn trong `sessions.py`, tái dùng ở Task 5.
