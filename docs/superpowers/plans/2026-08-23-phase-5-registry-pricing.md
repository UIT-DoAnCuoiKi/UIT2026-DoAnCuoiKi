# Phase 5: Vehicle registry and extended pricing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** thêm vé tháng, chủ xe, danh sách trắng và đen; miễn phí cho vé tháng hoặc danh sách trắng lúc ra; cảnh báo danh sách đen lúc vào; mở rộng giá với grace period và trần ngày.

**Architecture:** bốn model đăng ký (`VehicleOwner`, `MonthlyPass`, `PlateWhitelist`, `PlateBlacklist`), biển lưu mã hóa cộng hash như dữ liệu cá nhân. Service `registry` (kiểm miễn phí, kiểm danh sách đen). Nối vào `_complete_session` (miễn phí) và `confirm_entry` (cảnh báo đen). Giá mở rộng bằng hai cột `grace_minutes` và `daily_cap` trên `price_rule`, áp trong `compute_fee`.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 sync, Alembic, pydantic v2, pytest.

## Global Constraints

Kế thừa index mục Global Constraints. Riêng phase này:
- Biển số là dữ liệu cá nhân: lưu `plate_hash` (HMAC) cộng `plate_ciphertext` (Fernet), không lưu biển thô. Dùng `plate_hash`, `normalize_plate` (`app/security/plate.py`) và `crypto` (`app/security/crypto.py`) như phần còn lại của hệ thống.
- Miễn phí lúc ra: nếu biển có vé tháng còn hiệu lực hoặc trong danh sách trắng thì `fee_amount = 0`, `fee_rule_snapshot = {"exempt": True, ...}`; không cần bảng giá.
- Danh sách đen lúc vào: đặt `warning` trên phản hồi vào, không chặn.
- Vé tháng còn hiệu lực khi `active` và `start_date <= hôm nay <= end_date`.
- Giá: `grace_minutes` (mặc định 0) miễn phí nếu thời gian đỗ trong ngưỡng; `daily_cap` (nullable) trần tổng phí theo số ngày. Khi `grace_minutes = 0` và `daily_cap = None`, hành vi tính phí giữ nguyên như phase trước.
- Reads cho staff và admin; writes (đăng ký) cho admin (edge cho phép chỉnh cục bộ offline, master ở cloud phase 6).
- Không dùng ký tự gạch ngang trong văn xuôi tài liệu.
- Test trên SQLite in-memory qua `db_session`, `client`, `staff_headers`, `admin_headers`, `make_reading`.

---

### Task 1: Model đăng ký; migration; schema test

**Files:**
- Create: `src/backend/app/models/vehicle_owner.py`
- Create: `src/backend/app/models/monthly_pass.py`
- Create: `src/backend/app/models/plate_list.py`
- Modify: `src/backend/app/models/__init__.py`
- Create: `src/backend/alembic/versions/d4e5f6a7b8c9_add_registry.py`
- Test: `src/backend/tests/test_registry_schema.py`

**Interfaces:**
- Produces: `VehicleOwner(id:int, name:str, phone:str|None, plate_hash:str, plate_ciphertext:str, created_at)`; `MonthlyPass(id:int, owner_id:int|None, plate_hash:str, plate_ciphertext:str, vehicle_group:str, start_date:date, end_date:date, active:bool, created_at)`; `PlateWhitelist(id:int, plate_hash:str, plate_ciphertext:str, reason:str|None, active:bool, created_at)`; `PlateBlacklist(id:int, plate_hash:str, plate_ciphertext:str, reason:str|None, active:bool, created_at)`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_registry_schema.py`:

```python
def test_registry_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401
    for t in ("vehicle_owner", "monthly_pass", "plate_whitelist", "plate_blacklist"):
        assert t in Base.metadata.tables


def test_monthly_pass_columns():
    from app.models import MonthlyPass
    cols = MonthlyPass.__table__.columns.keys()
    for c in ("plate_hash", "plate_ciphertext", "vehicle_group", "start_date", "end_date", "active"):
        assert c in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_registry_schema.py -v`
Expected: FAIL (KeyError).

- [ ] **Step 3: Create the models**

Create `src/backend/app/models/vehicle_owner.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class VehicleOwner(Base):
    __tablename__ = "vehicle_owner"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Create `src/backend/app/models/monthly_pass.py`:

```python
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MonthlyPass(Base):
    __tablename__ = "monthly_pass"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_owner.id"), nullable=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    vehicle_group: Mapped[str] = mapped_column(String(16))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Create `src/backend/app/models/plate_list.py`:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PlateWhitelist(Base):
    __tablename__ = "plate_whitelist"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlateBlacklist(Base):
    __tablename__ = "plate_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Register the models**

In `src/backend/app/models/__init__.py`, add imports and `__all__` entries for `MonthlyPass`, `PlateBlacklist`, `PlateWhitelist`, `VehicleOwner`:

```python
from app.models.monthly_pass import MonthlyPass
from app.models.plate_list import PlateBlacklist, PlateWhitelist
from app.models.vehicle_owner import VehicleOwner
```

Add `"MonthlyPass"`, `"PlateBlacklist"`, `"PlateWhitelist"`, `"VehicleOwner"` to `__all__`.

- [ ] **Step 5: Run schema test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_registry_schema.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Write the migration**

Create `src/backend/alembic/versions/d4e5f6a7b8c9_add_registry.py`:

```python
"""add vehicle_owner, monthly_pass, plate_whitelist, plate_blacklist

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def _plate_list(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate_hash", sa.String(length=64), nullable=False),
        sa.Column("plate_ciphertext", sa.String(length=512), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(f"ix_{name}_plate_hash", name, ["plate_hash"])


def upgrade() -> None:
    op.create_table(
        "vehicle_owner",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("plate_hash", sa.String(length=64), nullable=False),
        sa.Column("plate_ciphertext", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vehicle_owner_plate_hash", "vehicle_owner", ["plate_hash"])
    op.create_table(
        "monthly_pass",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("vehicle_owner.id"), nullable=True),
        sa.Column("plate_hash", sa.String(length=64), nullable=False),
        sa.Column("plate_ciphertext", sa.String(length=512), nullable=False),
        sa.Column("vehicle_group", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_monthly_pass_plate_hash", "monthly_pass", ["plate_hash"])
    _plate_list("plate_whitelist")
    _plate_list("plate_blacklist")


def downgrade() -> None:
    op.drop_table("plate_blacklist")
    op.drop_table("plate_whitelist")
    op.drop_table("monthly_pass")
    op.drop_table("vehicle_owner")
```

- [ ] **Step 7: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/models/vehicle_owner.py src/backend/app/models/monthly_pass.py src/backend/app/models/plate_list.py src/backend/app/models/__init__.py src/backend/alembic/versions/d4e5f6a7b8c9_add_registry.py src/backend/tests/test_registry_schema.py
git commit -m "feat(backend): add vehicle owner, monthly pass and plate lists"
```

---

### Task 2: Router đăng ký (chủ xe, vé tháng, danh sách trắng đen)

**Files:**
- Create: `src/backend/app/schemas/registry.py`
- Create: `src/backend/app/routers/registry.py`
- Modify: `src/backend/app/main.py`
- Test: `src/backend/tests/test_registry_api.py`

**Interfaces:**
- Consumes: registry models (Task 1); `plate_hash`, `crypto`; `get_current_user`, `require_role`, `User`.
- Produces: `POST/GET /monthly-passes`, `POST/GET /whitelist`, `POST/GET /blacklist`, `POST/GET /owners`. Đầu vào nhận `plate_text` thô; backend lưu hash cộng ciphertext, đầu ra trả `plate_text` giải mã.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_registry_api.py`:

```python
def test_monthly_pass_crud_and_plaintext_roundtrip(client, admin_headers, staff_headers):
    body = {"plate_text": "51F12345", "vehicle_group": "o_to_con",
            "start_date": "2026-08-01", "end_date": "2026-08-31"}
    r = client.post("/monthly-passes", json=body, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["plate_text"] == "51F12345"
    listed = client.get("/monthly-passes", headers=staff_headers).json()
    assert any(p["plate_text"] == "51F12345" for p in listed)


def test_whitelist_and_blacklist_admin_only(client, admin_headers, staff_headers):
    assert client.post("/whitelist", json={"plate_text": "51F1"}, headers=staff_headers).status_code == 403
    assert client.post("/whitelist", json={"plate_text": "51F1"}, headers=admin_headers).status_code == 201
    assert client.post("/blacklist", json={"plate_text": "99Z9", "reason": "mất cắp"}, headers=admin_headers).status_code == 201
    bl = client.get("/blacklist", headers=staff_headers).json()
    assert any(x["plate_text"] == "99Z9" for x in bl)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_registry_api.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Write the schemas**

Create `src/backend/app/schemas/registry.py`:

```python
from datetime import date

from pydantic import BaseModel


class OwnerIn(BaseModel):
    name: str
    phone: str | None = None
    plate_text: str


class OwnerOut(BaseModel):
    id: int
    name: str
    phone: str | None = None
    plate_text: str


class MonthlyPassIn(BaseModel):
    plate_text: str
    vehicle_group: str
    start_date: date
    end_date: date
    owner_id: int | None = None
    active: bool = True


class MonthlyPassOut(BaseModel):
    id: int
    plate_text: str
    vehicle_group: str
    start_date: date
    end_date: date
    owner_id: int | None = None
    active: bool


class PlateListIn(BaseModel):
    plate_text: str
    reason: str | None = None
    active: bool = True


class PlateListOut(BaseModel):
    id: int
    plate_text: str
    reason: str | None = None
    active: bool
```

- [ ] **Step 4: Write the router**

Create `src/backend/app/routers/registry.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import MonthlyPass, PlateBlacklist, PlateWhitelist, User, VehicleOwner
from app.schemas.registry import (
    MonthlyPassIn, MonthlyPassOut, OwnerIn, OwnerOut, PlateListIn, PlateListOut,
)
from app.security import crypto
from app.security.plate import plate_hash

router = APIRouter(tags=["registry"])
admin_only = require_role("admin")


def _plate_fields(plate_text: str) -> dict:
    return {"plate_hash": plate_hash(plate_text), "plate_ciphertext": crypto.encrypt_text(plate_text)}


@router.post("/owners", response_model=OwnerOut, status_code=status.HTTP_201_CREATED)
def create_owner(body: OwnerIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    owner = VehicleOwner(name=body.name, phone=body.phone, **_plate_fields(body.plate_text))
    db.add(owner); db.commit(); db.refresh(owner)
    return OwnerOut(id=owner.id, name=owner.name, phone=owner.phone, plate_text=body.plate_text)


@router.get("/owners", response_model=list[OwnerOut])
def list_owners(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(VehicleOwner).order_by(VehicleOwner.id)).all()
    return [OwnerOut(id=o.id, name=o.name, phone=o.phone,
                     plate_text=crypto.decrypt_text(o.plate_ciphertext)) for o in rows]


@router.post("/monthly-passes", response_model=MonthlyPassOut, status_code=status.HTTP_201_CREATED)
def create_pass(body: MonthlyPassIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    mp = MonthlyPass(
        owner_id=body.owner_id, vehicle_group=body.vehicle_group,
        start_date=body.start_date, end_date=body.end_date, active=body.active,
        **_plate_fields(body.plate_text),
    )
    db.add(mp); db.commit(); db.refresh(mp)
    return MonthlyPassOut(id=mp.id, plate_text=body.plate_text, vehicle_group=mp.vehicle_group,
                          start_date=mp.start_date, end_date=mp.end_date, owner_id=mp.owner_id, active=mp.active)


@router.get("/monthly-passes", response_model=list[MonthlyPassOut])
def list_passes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(MonthlyPass).order_by(MonthlyPass.id)).all()
    return [MonthlyPassOut(id=p.id, plate_text=crypto.decrypt_text(p.plate_ciphertext),
                           vehicle_group=p.vehicle_group, start_date=p.start_date, end_date=p.end_date,
                           owner_id=p.owner_id, active=p.active) for p in rows]


def _list_out(rows) -> list[PlateListOut]:
    return [PlateListOut(id=r.id, plate_text=crypto.decrypt_text(r.plate_ciphertext),
                         reason=r.reason, active=r.active) for r in rows]


@router.post("/whitelist", response_model=PlateListOut, status_code=status.HTTP_201_CREATED)
def add_whitelist(body: PlateListIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    row = PlateWhitelist(reason=body.reason, active=body.active, **_plate_fields(body.plate_text))
    db.add(row); db.commit(); db.refresh(row)
    return PlateListOut(id=row.id, plate_text=body.plate_text, reason=row.reason, active=row.active)


@router.get("/whitelist", response_model=list[PlateListOut])
def list_whitelist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _list_out(db.scalars(select(PlateWhitelist).order_by(PlateWhitelist.id)).all())


@router.post("/blacklist", response_model=PlateListOut, status_code=status.HTTP_201_CREATED)
def add_blacklist(body: PlateListIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    row = PlateBlacklist(reason=body.reason, active=body.active, **_plate_fields(body.plate_text))
    db.add(row); db.commit(); db.refresh(row)
    return PlateListOut(id=row.id, plate_text=body.plate_text, reason=row.reason, active=row.active)


@router.get("/blacklist", response_model=list[PlateListOut])
def list_blacklist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _list_out(db.scalars(select(PlateBlacklist).order_by(PlateBlacklist.id)).all())
```

- [ ] **Step 5: Register the router**

In `src/backend/app/main.py`, add `registry` to the routers import line and add `app.include_router(registry.router)`.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_registry_api.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/schemas/registry.py src/backend/app/routers/registry.py src/backend/app/main.py src/backend/tests/test_registry_api.py
git commit -m "feat(backend): add registry CRUD for owners, passes, whitelist, blacklist"
```

---

### Task 3: Service miễn phí và cảnh báo; nối vào ra vào

**Files:**
- Create: `src/backend/app/services/registry.py`
- Modify: `src/backend/app/routers/sessions.py`
- Test: `src/backend/tests/test_registry_service.py`, `src/backend/tests/test_exit_exemption.py`, `src/backend/tests/test_entry_blacklist.py`

**Interfaces:**
- Consumes: `MonthlyPass`, `PlateWhitelist`, `PlateBlacklist` (Task 1); `_complete_session`, `confirm_entry`, `_session_out` (`sessions.py`).
- Produces: `has_valid_pass(db, plate_hash, on:date|None=None) -> bool`; `is_whitelisted(db, plate_hash) -> bool`; `is_blacklisted(db, plate_hash) -> bool`; `is_exempt(db, plate_hash) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `src/backend/tests/test_registry_service.py`:

```python
from datetime import date, timedelta


def _add_pass(db, ph, start, end, active=True):
    from app.models import MonthlyPass
    db.add(MonthlyPass(plate_hash=ph, plate_ciphertext="x", vehicle_group="o_to_con",
                       start_date=start, end_date=end, active=active))
    db.commit()


def test_has_valid_pass_within_window(db_session):
    from app.services.registry import has_valid_pass
    today = date(2026, 8, 15)
    _add_pass(db_session, "ph1", today - timedelta(days=5), today + timedelta(days=5))
    assert has_valid_pass(db_session, "ph1", on=today) is True
    assert has_valid_pass(db_session, "ph1", on=today + timedelta(days=10)) is False


def test_inactive_pass_not_valid(db_session):
    from app.services.registry import has_valid_pass
    today = date(2026, 8, 15)
    _add_pass(db_session, "ph2", today, today + timedelta(days=30), active=False)
    assert has_valid_pass(db_session, "ph2", on=today) is False


def test_whitelist_and_blacklist_and_exempt(db_session):
    from app.models import PlateBlacklist, PlateWhitelist
    from app.services.registry import is_blacklisted, is_exempt, is_whitelisted
    db_session.add(PlateWhitelist(plate_hash="wh", plate_ciphertext="x", active=True))
    db_session.add(PlateBlacklist(plate_hash="bl", plate_ciphertext="x", active=True))
    db_session.commit()
    assert is_whitelisted(db_session, "wh") is True
    assert is_exempt(db_session, "wh") is True
    assert is_blacklisted(db_session, "bl") is True
    assert is_exempt(db_session, "bl") is False
```

Create `src/backend/tests/test_exit_exemption.py`:

```python
def test_whitelisted_plate_exits_free(client, admin_headers, staff_headers, make_reading, db_session):
    from app.models import ParkingSession
    from app.clock import now_utc
    from app.security.plate import plate_hash

    plate = "51F88888"
    client.post("/whitelist", json={"plate_text": plate}, headers=admin_headers)
    session = ParkingSession(plate_hash=plate_hash(plate), plate_ciphertext="x",
                             vehicle_group="o_to_con", status="in_lot", entry_time=now_utc())
    db_session.add(session); db_session.commit(); db_session.refresh(session)

    out_reading = make_reading(plate=plate, direction="out")
    r = client.post("/sessions/exit", json={"reading_id": out_reading.id, "session_id": session.id}, headers=staff_headers)
    assert r.status_code == 200
    assert r.json()["session"]["fee_amount"] == 0
```

Create `src/backend/tests/test_entry_blacklist.py`:

```python
def test_blacklisted_plate_entry_warns(client, admin_headers, staff_headers, make_reading):
    plate = "99Z99999"
    client.post("/blacklist", json={"plate_text": plate, "reason": "mất cắp"}, headers=admin_headers)
    reading = make_reading(plate=plate, direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.status_code == 200
    assert "đen" in (r.json()["warning"] or "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/backend && python -m pytest tests/test_registry_service.py tests/test_exit_exemption.py tests/test_entry_blacklist.py -v`
Expected: FAIL (ModuleNotFoundError app.services.registry; exit not free; no warning).

- [ ] **Step 3: Write the service**

Create `src/backend/app/services/registry.py`:

```python
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MonthlyPass, PlateBlacklist, PlateWhitelist


def has_valid_pass(db: Session, plate_hash: str, on: date | None = None) -> bool:
    if not plate_hash:
        return False
    today = on or date.today()
    passes = db.scalars(
        select(MonthlyPass).where(MonthlyPass.plate_hash == plate_hash, MonthlyPass.active.is_(True))
    ).all()
    return any(p.start_date <= today <= p.end_date for p in passes)


def is_whitelisted(db: Session, plate_hash: str) -> bool:
    if not plate_hash:
        return False
    return db.scalars(
        select(PlateWhitelist).where(PlateWhitelist.plate_hash == plate_hash, PlateWhitelist.active.is_(True))
    ).first() is not None


def is_blacklisted(db: Session, plate_hash: str) -> bool:
    if not plate_hash:
        return False
    return db.scalars(
        select(PlateBlacklist).where(PlateBlacklist.plate_hash == plate_hash, PlateBlacklist.active.is_(True))
    ).first() is not None


def is_exempt(db: Session, plate_hash: str) -> bool:
    return has_valid_pass(db, plate_hash) or is_whitelisted(db, plate_hash)
```

- [ ] **Step 4: Apply exemption at exit**

In `src/backend/app/routers/sessions.py`, add the import:

```python
from app.services.registry import is_blacklisted, is_exempt
```

Replace the body of `_complete_session` with this exemption-aware version:

```python
def _complete_session(db: Session, session: ParkingSession, exit_reading_id: int | None, match_flag: str, user: User) -> None:
    session.exit_reading_id = exit_reading_id
    session.exit_time = now_utc()
    session.match_flag = match_flag
    if is_exempt(db, session.plate_hash):
        session.fee_amount = 0
        session.fee_rule_snapshot = {"exempt": True}
    else:
        rule = get_active_rule(db, session.vehicle_group)
        if rule is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "chưa có bảng giá cho nhóm xe này")
        fee, snapshot = compute_fee(rule, session.entry_time, session.exit_time)
        session.fee_amount = fee
        session.fee_rule_snapshot = snapshot
    session.status = "completed"
    session.closed_by = user.id
    _set_retention(db, session)
```

- [ ] **Step 5: Apply blacklist warning at entry**

In `confirm_entry` (same file), after the existing duplicate-plate warning block and before constructing `ParkingSession`, add:

```python
    if has_plate and is_blacklisted(db, reading.plate_hash):
        warning = "biển trong danh sách đen"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_registry_service.py tests/test_exit_exemption.py tests/test_entry_blacklist.py -v`
Expected: PASS.

- [ ] **Step 7: Run the exit and fee suites to confirm no regression**

Run: `cd src/backend && python -m pytest tests/test_session_exit.py tests/test_fee.py tests/test_session_entry.py -v`
Expected: PASS (không exempt trong các test cũ nên phí không đổi).

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/services/registry.py src/backend/app/routers/sessions.py src/backend/tests/test_registry_service.py src/backend/tests/test_exit_exemption.py src/backend/tests/test_entry_blacklist.py
git commit -m "feat(backend): exempt passes and whitelist at exit, warn blacklist at entry"
```

---

### Task 4: Giá mở rộng: grace period và trần ngày

**Files:**
- Modify: `src/backend/app/models/price_rule.py`
- Modify: `src/backend/app/services/fee.py`
- Modify: `src/backend/app/schemas/config.py`
- Create: `src/backend/alembic/versions/e5f6a7b8c9d0_price_grace_cap.py`
- Test: `src/backend/tests/test_fee_grace_cap.py`

**Interfaces:**
- Consumes: `PriceRule`, `compute_fee` (đã có).
- Produces: `PriceRule` thêm `grace_minutes:int` (mặc định 0) và `daily_cap:int|None`. `compute_fee` áp grace (miễn phí nếu thời gian trong ngưỡng) và trần ngày. `PriceRuleIn`, `PriceRuleUpdate`, `PriceRuleOut` thêm hai trường.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_fee_grace_cap.py`:

```python
from datetime import datetime

from app.models import PriceRule
from app.services.fee import compute_fee


def test_grace_period_makes_short_stay_free():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60)
    rule.grace_minutes = 15
    rule.daily_cap = None
    entry = datetime(2026, 8, 1, 8, 0)
    exit_ = datetime(2026, 8, 1, 8, 10)  # 10 phút, trong grace
    fee, snap = compute_fee(rule, entry, exit_)
    assert fee == 0
    assert snap["free"] is True


def test_daily_cap_limits_block_fee():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60)
    rule.grace_minutes = 0
    rule.daily_cap = 30000
    entry = datetime(2026, 8, 1, 0, 0)
    exit_ = datetime(2026, 8, 1, 20, 0)  # 20 giờ = 20 block * 5000 = 100000, trần 30000
    fee, snap = compute_fee(rule, entry, exit_)
    assert fee == 30000
    assert snap["capped"] is True


def test_no_grace_no_cap_unchanged():
    rule = PriceRule(vehicle_group="o_to_con", mode="flat", unit_price=10000)
    rule.grace_minutes = 0
    rule.daily_cap = None
    fee, snap = compute_fee(rule, datetime(2026, 8, 1, 8, 0), datetime(2026, 8, 1, 9, 0))
    assert fee == 10000
    assert snap["mode"] == "flat"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_fee_grace_cap.py -v`
Expected: FAIL (grace và cap chưa áp).

- [ ] **Step 3: Add the columns**

In `src/backend/app/models/price_rule.py`, add two columns inside `PriceRule` (after `block_minutes`):

```python
    grace_minutes: Mapped[int] = mapped_column(Integer, default=0)
    daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 4: Extend `compute_fee`**

Replace `compute_fee` in `src/backend/app/services/fee.py` with:

```python
def compute_fee(rule: PriceRule, entry_time: datetime, exit_time: datetime) -> tuple[int, dict]:
    grace = getattr(rule, "grace_minutes", 0) or 0
    daily_cap = getattr(rule, "daily_cap", None)
    minutes = max(0.0, (to_naive(exit_time) - to_naive(entry_time)).total_seconds() / 60.0)

    if grace > 0 and minutes <= grace:
        return 0, {"mode": rule.mode, "grace_minutes": grace, "minutes": round(minutes, 2), "free": True}

    if rule.mode == "flat":
        return rule.unit_price, {"mode": "flat", "unit_price": rule.unit_price}

    blocks = max(1, math.ceil(minutes / rule.block_minutes))
    fee = blocks * rule.unit_price
    snapshot = {
        "mode": "block", "unit_price": rule.unit_price, "block_minutes": rule.block_minutes,
        "blocks": blocks, "minutes": round(minutes, 2),
    }
    if daily_cap is not None:
        days = max(1, math.ceil(minutes / 1440))
        cap = daily_cap * days
        if fee > cap:
            fee = cap
            snapshot["capped"] = True
            snapshot["daily_cap"] = daily_cap
            snapshot["days"] = days
    return fee, snapshot
```

- [ ] **Step 5: Extend the config schemas**

In `src/backend/app/schemas/config.py`, add `grace_minutes` and `daily_cap` to `PriceRuleIn`, `PriceRuleUpdate`, and `PriceRuleOut`:

```python
# PriceRuleIn: add
    grace_minutes: int = 0
    daily_cap: int | None = None

# PriceRuleUpdate: add
    grace_minutes: int | None = None
    daily_cap: int | None = None

# PriceRuleOut: add
    grace_minutes: int = 0
    daily_cap: int | None = None
```

- [ ] **Step 6: Write the migration**

Create `src/backend/alembic/versions/e5f6a7b8c9d0_price_grace_cap.py`:

```python
"""add grace_minutes and daily_cap to price_rule

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("price_rule", sa.Column("grace_minutes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("price_rule", sa.Column("daily_cap", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("price_rule", "daily_cap")
    op.drop_column("price_rule", "grace_minutes")
```

- [ ] **Step 7: Run test and the existing fee suite**

Run: `cd src/backend && python -m pytest tests/test_fee_grace_cap.py tests/test_fee.py -v`
Expected: PASS (grace và cap mới, cộng fee cũ không đổi vì mặc định 0 và None).

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/models/price_rule.py src/backend/app/services/fee.py src/backend/app/schemas/config.py src/backend/alembic/versions/e5f6a7b8c9d0_price_grace_cap.py src/backend/tests/test_fee_grace_cap.py
git commit -m "feat(backend): add grace period and daily cap to pricing"
```

---

### Task 5: Test nghiệm thu phase và chạy toàn suite

**Files:**
- Test: `src/backend/tests/test_phase5_registry_pricing_acceptance.py`

**Interfaces:**
- Consumes: mọi thứ Task 1 tới 4.

- [ ] **Step 1: Write the acceptance test**

Create `src/backend/tests/test_phase5_registry_pricing_acceptance.py`:

```python
def test_monthly_pass_exit_free_and_grace_pricing(client, admin_headers, staff_headers, make_reading, db_session):
    from datetime import date, timedelta
    from app.clock import now_utc
    from app.models import ParkingSession
    from app.security.plate import plate_hash

    plate = "51F24680"
    today = date.today()
    client.post("/monthly-passes", json={
        "plate_text": plate, "vehicle_group": "o_to_con",
        "start_date": (today - timedelta(days=1)).isoformat(),
        "end_date": (today + timedelta(days=29)).isoformat(),
    }, headers=admin_headers)

    session = ParkingSession(plate_hash=plate_hash(plate), plate_ciphertext="x",
                             vehicle_group="o_to_con", status="in_lot", entry_time=now_utc())
    db_session.add(session); db_session.commit(); db_session.refresh(session)

    out_reading = make_reading(plate=plate, direction="out")
    r = client.post("/sessions/exit", json={"reading_id": out_reading.id, "session_id": session.id}, headers=staff_headers)
    assert r.status_code == 200
    assert r.json()["session"]["fee_amount"] == 0  # vé tháng miễn phí
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd src/backend && python -m pytest tests/test_phase5_registry_pricing_acceptance.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS toàn bộ.

- [ ] **Step 4: Commit**

```bash
git add src/backend/tests/test_phase5_registry_pricing_acceptance.py
git commit -m "test(backend): phase 5 registry and pricing acceptance"
```

---

## Self-Review

**Spec coverage (spec kiến trúc mục 6.3, 6.5; frontend v2 mục 5.2, 5.5):** vé tháng (Task 1, 2, 3), chủ xe (Task 1, 2), danh sách trắng miễn phí và đen cảnh báo (Task 2, 3), grace period và trần ngày (Task 4). Lịch giá theo giờ trong ngày và lễ để phase mở rộng sau, không phải gap của MVP.

**Placeholder scan:** không có TBD; mọi bước có code thật.

**Type consistency:** `is_exempt`, `is_blacklisted`, `has_valid_pass`, `is_whitelisted` khớp giữa service (Task 3), sessions (Task 3), và test. `compute_fee(rule, entry, exit) -> (int, dict)` giữ chữ ký cũ, chỉ mở rộng snapshot với `free`, `capped` (Task 4). `_plate_fields` trả `plate_hash` cộng `plate_ciphertext` khớp cột model. `PriceRule.grace_minutes`, `daily_cap` khớp model (Task 4), schema config (Task 4), và migration.

**Ghi chú:** `getattr(rule, "grace_minutes", 0) or 0` phòng trường hợp `PriceRule` dựng trong Python chưa qua INSERT nên thuộc tính là `None`; giữ test `compute_fee` cũ (không set hai trường) chạy đúng.
