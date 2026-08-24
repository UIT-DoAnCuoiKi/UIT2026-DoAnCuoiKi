# Phase 1: Edge multi-lot, floor, zone and capacity — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** thêm mô hình bãi, tầng, khu vào backend edge; gắn phiên với `lot_id` và `zone_id`; đếm chiếm dụng thời gian thực; chặn cho vào khi bãi đầy; cung cấp CRUD bãi/tầng/khu cho admin và endpoint sức chứa.

**Architecture:** thêm ba model SQLAlchemy (`ParkingLot`, `Floor`, `Zone`), hai cột khóa ngoại nullable trên `session`, một service đếm chiếm dụng thuần đọc, một router CRUD không gian, và một endpoint sức chứa. Xác nhận vào (`POST /sessions/entry`) nhận thêm `zone_id`, kiểm sức chứa trước khi tạo phiên. Giữ khóa chính số nguyên (định danh toàn cục UUID nằm ở phase 6).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 sync, Alembic, pydantic v2, pytest, httpx (TestClient).

## Global Constraints

Kế thừa `docs/superpowers/plans/2026-08-23-parking-edge-cloud-plan-index.md` mục Global Constraints. Riêng phase này:

- Giữ khóa chính số nguyên cục bộ; không đổi kiểu khóa hiện có. `lot_id` và `zone_id` trên `session` là nullable để không phá phiên cũ và test cũ.
- `capacity = 0` nghĩa là không giới hạn (không chặn vào).
- Kiểm sức chứa chỉ chạy khi `zone_id` được cung cấp và bãi tương ứng có `capacity > 0`; bãi đầy trả HTTP 409, không bao giờ làm hỏng đường nhập tay.
- Reads (list, occupancy) cho `staff` và `admin`; writes (create, patch) chỉ `admin`, theo đúng mẫu `app/routers/config.py`.
- Không dùng ký tự gạch ngang trong văn xuôi tài liệu.
- Test chạy trên SQLite in-memory qua fixture `db_session` (StaticPool); bảng dựng bằng `Base.metadata.create_all`, nên chỉ cần khai báo model là test thấy bảng. Migration Alembic phục vụ Postgres thật.

---

### Task 1: Model bãi, tầng, khu; cột `lot_id` và `zone_id` trên session; migration; fixtures test dùng chung

**Files:**
- Create: `src/backend/app/models/parking_lot.py`
- Create: `src/backend/app/models/floor.py`
- Create: `src/backend/app/models/zone.py`
- Modify: `src/backend/app/models/__init__.py`
- Modify: `src/backend/app/models/parking_session.py`
- Create: `src/backend/alembic/versions/a1b2c3d4e5f6_add_lot_floor_zone.py`
- Modify: `src/backend/tests/conftest.py`
- Test: `src/backend/tests/test_spaces_schema.py`

**Interfaces:**
- Produces: model `ParkingLot(id:int, name:str, address:str|None, capacity:int, active:bool)`, `Floor(id:int, lot_id:int, name:str, capacity:int, active:bool)`, `Zone(id:int, lot_id:int, floor_id:int|None, name:str, capacity:int, active:bool)`. `ParkingSession` thêm `lot_id:int|None`, `zone_id:int|None`.
- Produces: pytest fixtures `admin_headers` (dict header Bearer của user admin) và `make_reading(plate:str="51F12345", direction:str="in", vehicle_type:str|None=None) -> PlateReading`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_spaces_schema.py`:

```python
def test_space_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401  đăng ký bảng
    for t in ("parking_lot", "floor", "zone"):
        assert t in Base.metadata.tables


def test_session_has_lot_and_zone_columns():
    from app.models import ParkingSession
    cols = ParkingSession.__table__.columns.keys()
    assert "lot_id" in cols
    assert "zone_id" in cols


def test_zone_floor_id_is_nullable():
    from app.models import Zone
    assert Zone.__table__.columns["floor_id"].nullable is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_spaces_schema.py -v`
Expected: FAIL (ImportError hoặc KeyError, chưa có model `parking_lot`).

- [ ] **Step 3: Create the three models**

Create `src/backend/app/models/parking_lot.py`:

```python
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ParkingLot(Base):
    __tablename__ = "parking_lot"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=0)  # 0 = không giới hạn
    active: Mapped[bool] = mapped_column(Boolean, default=True)
```

Create `src/backend/app/models/floor.py`:

```python
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Floor(Base):
    __tablename__ = "floor"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("parking_lot.id"))
    name: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
```

Create `src/backend/app/models/zone.py`:

```python
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Zone(Base):
    __tablename__ = "zone"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("parking_lot.id"))
    floor_id: Mapped[int | None] = mapped_column(ForeignKey("floor.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 4: Register models and add session columns**

Replace `src/backend/app/models/__init__.py` with:

```python
from app.models.audit_log import AuditLog
from app.models.feature_toggle import FeatureToggle
from app.models.floor import Floor
from app.models.image_asset import ImageAsset
from app.models.lane import Lane
from app.models.parking_lot import ParkingLot
from app.models.parking_session import ParkingSession
from app.models.plate_reading import PlateReading
from app.models.price_rule import PriceRule
from app.models.user import User
from app.models.zone import Zone

__all__ = [
    "AuditLog", "FeatureToggle", "Floor", "ImageAsset", "Lane",
    "ParkingLot", "ParkingSession", "PlateReading", "PriceRule", "User", "Zone",
]
```

In `src/backend/app/models/parking_session.py`, add two columns inside the `ParkingSession` class, right after the `status` column line:

```python
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("parking_lot.id"), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zone.id"), nullable=True)
```

(`ForeignKey` is already imported in that file.)

- [ ] **Step 5: Run schema test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_spaces_schema.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Write the Alembic migration**

Create `src/backend/alembic/versions/a1b2c3d4e5f6_add_lot_floor_zone.py`:

```python
"""add parking_lot, floor, zone and session lot/zone fk

Revision ID: a1b2c3d4e5f6
Revises: 0b0007c4dc28
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "0b0007c4dc28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parking_lot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("address", sa.String(length=256), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "floor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "zone",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=False),
        sa.Column("floor_id", sa.Integer(), sa.ForeignKey("floor.id"), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("session", sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=True))
    op.add_column("session", sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zone.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("session", "zone_id")
    op.drop_column("session", "lot_id")
    op.drop_table("zone")
    op.drop_table("floor")
    op.drop_table("parking_lot")
```

- [ ] **Step 7: Add shared test fixtures**

In `src/backend/tests/conftest.py`, append these two fixtures at the end of the file:

```python
@pytest.fixture()
def admin_headers(client, make_user):
    make_user(username="boss", password="pw", role="admin")
    token = client.post("/auth/login", json={"username": "boss", "password": "pw"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_reading(db_session):
    from app.models import PlateReading
    from app.security import crypto
    from app.security.plate import plate_hash

    def _make(plate: str = "51F12345", direction: str = "in", vehicle_type: str | None = None):
        reading = PlateReading(
            capture_id=f"cap-{plate}-{direction}",
            direction=direction,
            plate_text_ciphertext=crypto.encrypt_text(plate),
            plate_hash=plate_hash(plate),
            plate_valid=True,
            vehicle_type=vehicle_type,
            review_state="confident",
        )
        db_session.add(reading)
        db_session.commit()
        db_session.refresh(reading)
        return reading

    return _make
```

- [ ] **Step 8: Run the full suite to confirm nothing broke**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS (suite hiện có cộng 3 test schema mới; không có regression vì cột mới nullable).

- [ ] **Step 9: Commit**

```bash
git add src/backend/app/models src/backend/alembic/versions/a1b2c3d4e5f6_add_lot_floor_zone.py src/backend/tests/conftest.py src/backend/tests/test_spaces_schema.py
git commit -m "feat(backend): add parking lot, floor, zone models and session lot/zone fk"
```

---

### Task 2: Service đếm chiếm dụng

**Files:**
- Create: `src/backend/app/services/occupancy.py`
- Test: `src/backend/tests/test_occupancy_service.py`

**Interfaces:**
- Consumes: `ParkingLot`, `Zone`, `ParkingSession` từ Task 1.
- Produces: `lot_occupancy(db, lot_id:int) -> int`, `zone_occupancy(db, zone_id:int) -> int`, `lot_is_full(db, lot_id:int) -> bool`, `occupancy_report(db) -> list[dict]`. Mỗi dict lot có khóa `lot_id, name, capacity, occupancy, available, full, zones`; mỗi dict zone có `zone_id, floor_id, name, capacity, occupancy, available`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_occupancy_service.py`:

```python
def _add_in_lot(db, lot_id, zone_id=None, plate="h"):
    from app.models import ParkingSession
    db.add(ParkingSession(
        plate_hash=plate, plate_ciphertext="x", vehicle_group="o_to_con",
        status="in_lot", lot_id=lot_id, zone_id=zone_id,
    ))
    db.commit()


def test_lot_and_zone_occupancy_counts_only_in_lot(db_session):
    from app.models import ParkingLot, Zone
    from app.services.occupancy import lot_occupancy, zone_occupancy
    lot = ParkingLot(name="A", capacity=10)
    db_session.add(lot); db_session.commit(); db_session.refresh(lot)
    zone = Zone(lot_id=lot.id, name="Z1", capacity=5)
    db_session.add(zone); db_session.commit(); db_session.refresh(zone)

    _add_in_lot(db_session, lot.id, zone.id, "h1")
    _add_in_lot(db_session, lot.id, zone.id, "h2")
    # phiên đã hoàn tất không tính
    from app.models import ParkingSession
    db_session.add(ParkingSession(
        plate_hash="h3", plate_ciphertext="x", vehicle_group="o_to_con",
        status="completed", lot_id=lot.id, zone_id=zone.id,
    ))
    db_session.commit()

    assert lot_occupancy(db_session, lot.id) == 2
    assert zone_occupancy(db_session, zone.id) == 2


def test_lot_is_full_respects_capacity_and_unlimited(db_session):
    from app.models import ParkingLot
    from app.services.occupancy import lot_is_full
    limited = ParkingLot(name="L", capacity=1)
    unlimited = ParkingLot(name="U", capacity=0)
    db_session.add_all([limited, unlimited]); db_session.commit()
    db_session.refresh(limited); db_session.refresh(unlimited)

    assert lot_is_full(db_session, limited.id) is False
    _add_in_lot(db_session, limited.id, None, "h1")
    assert lot_is_full(db_session, limited.id) is True
    # capacity 0 nghĩa là không giới hạn
    _add_in_lot(db_session, unlimited.id, None, "h2")
    assert lot_is_full(db_session, unlimited.id) is False


def test_occupancy_report_shape(db_session):
    from app.models import ParkingLot, Zone
    from app.services.occupancy import occupancy_report
    lot = ParkingLot(name="A", capacity=4)
    db_session.add(lot); db_session.commit(); db_session.refresh(lot)
    zone = Zone(lot_id=lot.id, name="Z1", capacity=2)
    db_session.add(zone); db_session.commit(); db_session.refresh(zone)
    _add_in_lot(db_session, lot.id, zone.id, "h1")

    report = occupancy_report(db_session)
    row = next(r for r in report if r["lot_id"] == lot.id)
    assert row["occupancy"] == 1
    assert row["available"] == 3
    assert row["full"] is False
    z = row["zones"][0]
    assert z["zone_id"] == zone.id
    assert z["occupancy"] == 1
    assert z["available"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_occupancy_service.py -v`
Expected: FAIL (ModuleNotFoundError: app.services.occupancy).

- [ ] **Step 3: Write the service**

Create `src/backend/app/services/occupancy.py`:

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ParkingLot, ParkingSession, Zone


def lot_occupancy(db: Session, lot_id: int) -> int:
    return int(db.scalar(
        select(func.count()).select_from(ParkingSession).where(
            ParkingSession.status == "in_lot", ParkingSession.lot_id == lot_id,
        )
    ) or 0)


def zone_occupancy(db: Session, zone_id: int) -> int:
    return int(db.scalar(
        select(func.count()).select_from(ParkingSession).where(
            ParkingSession.status == "in_lot", ParkingSession.zone_id == zone_id,
        )
    ) or 0)


def lot_is_full(db: Session, lot_id: int) -> bool:
    lot = db.get(ParkingLot, lot_id)
    if lot is None or lot.capacity <= 0:
        return False
    return lot_occupancy(db, lot_id) >= lot.capacity


def _available(capacity: int, occupancy: int) -> int | None:
    return max(capacity - occupancy, 0) if capacity > 0 else None


def occupancy_report(db: Session) -> list[dict]:
    report: list[dict] = []
    for lot in db.scalars(select(ParkingLot).order_by(ParkingLot.id)).all():
        occ = lot_occupancy(db, lot.id)
        zones = []
        for z in db.scalars(select(Zone).where(Zone.lot_id == lot.id).order_by(Zone.id)).all():
            zocc = zone_occupancy(db, z.id)
            zones.append({
                "zone_id": z.id, "floor_id": z.floor_id, "name": z.name,
                "capacity": z.capacity, "occupancy": zocc, "available": _available(z.capacity, zocc),
            })
        report.append({
            "lot_id": lot.id, "name": lot.name, "capacity": lot.capacity,
            "occupancy": occ, "available": _available(lot.capacity, occ),
            "full": lot.capacity > 0 and occ >= lot.capacity, "zones": zones,
        })
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_occupancy_service.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/backend/app/services/occupancy.py src/backend/tests/test_occupancy_service.py
git commit -m "feat(backend): add occupancy counting service"
```

---

### Task 3: Router CRUD bãi, tầng, khu

**Files:**
- Create: `src/backend/app/schemas/space.py`
- Create: `src/backend/app/routers/spaces.py`
- Modify: `src/backend/app/main.py`
- Test: `src/backend/tests/test_spaces_crud.py`

**Interfaces:**
- Consumes: models từ Task 1; mẫu router và phân vai từ `app/routers/config.py` (`require_role("admin")`, `get_current_user`).
- Produces: endpoint `GET/POST /lots`, `PATCH /lots/{lot_id}`, `GET/POST /floors`, `PATCH /floors/{floor_id}`, `GET/POST /zones`, `PATCH /zones/{zone_id}`. `GET /floors` và `GET /zones` nhận query optional `lot_id`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_spaces_crud.py`:

```python
def test_lot_crud_and_rbac(client, admin_headers, staff_headers):
    # staff không được tạo
    assert client.post("/lots", json={"name": "A", "capacity": 10}, headers=staff_headers).status_code == 403
    # admin tạo được
    r = client.post("/lots", json={"name": "A", "capacity": 10}, headers=admin_headers)
    assert r.status_code == 201
    lot_id = r.json()["id"]
    # staff đọc được
    assert client.get("/lots", headers=staff_headers).status_code == 200
    # admin sửa được
    p = client.patch(f"/lots/{lot_id}", json={"capacity": 20}, headers=admin_headers)
    assert p.status_code == 200 and p.json()["capacity"] == 20


def test_floor_and_zone_under_lot(client, admin_headers, staff_headers):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 100}, headers=admin_headers).json()["id"]
    f = client.post("/floors", json={"lot_id": lot_id, "name": "Tang 1", "capacity": 50}, headers=admin_headers)
    assert f.status_code == 201
    floor_id = f.json()["id"]
    z = client.post("/zones", json={"lot_id": lot_id, "floor_id": floor_id, "name": "Khu A", "capacity": 20}, headers=admin_headers)
    assert z.status_code == 201
    # lọc theo lot_id
    floors = client.get(f"/floors?lot_id={lot_id}", headers=staff_headers).json()
    assert len(floors) == 1 and floors[0]["name"] == "Tang 1"
    zones = client.get(f"/zones?lot_id={lot_id}", headers=staff_headers).json()
    assert len(zones) == 1 and zones[0]["floor_id"] == floor_id


def test_floor_requires_existing_lot(client, admin_headers):
    r = client.post("/floors", json={"lot_id": 9999, "name": "x", "capacity": 1}, headers=admin_headers)
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_spaces_crud.py -v`
Expected: FAIL (404 on `/lots`, router chưa tồn tại).

- [ ] **Step 3: Write the schemas**

Create `src/backend/app/schemas/space.py`:

```python
from pydantic import BaseModel


class LotIn(BaseModel):
    name: str
    address: str | None = None
    capacity: int = 0
    active: bool = True


class LotUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    capacity: int | None = None
    active: bool | None = None


class LotOut(BaseModel):
    id: int
    name: str
    address: str | None = None
    capacity: int
    active: bool
    model_config = {"from_attributes": True}


class FloorIn(BaseModel):
    lot_id: int
    name: str
    capacity: int = 0
    active: bool = True


class FloorUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    active: bool | None = None


class FloorOut(BaseModel):
    id: int
    lot_id: int
    name: str
    capacity: int
    active: bool
    model_config = {"from_attributes": True}


class ZoneIn(BaseModel):
    lot_id: int
    floor_id: int | None = None
    name: str
    capacity: int = 0
    active: bool = True


class ZoneUpdate(BaseModel):
    name: str | None = None
    floor_id: int | None = None
    capacity: int | None = None
    active: bool | None = None


class ZoneOut(BaseModel):
    id: int
    lot_id: int
    floor_id: int | None = None
    name: str
    capacity: int
    active: bool
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Write the router**

Create `src/backend/app/routers/spaces.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import Floor, ParkingLot, User, Zone
from app.schemas.space import (
    FloorIn, FloorOut, FloorUpdate, LotIn, LotOut, LotUpdate, ZoneIn, ZoneOut, ZoneUpdate,
)

router = APIRouter(tags=["spaces"])
admin_only = require_role("admin")


@router.get("/lots", response_model=list[LotOut])
def list_lots(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(ParkingLot).order_by(ParkingLot.id)).all())


@router.post("/lots", response_model=LotOut, status_code=status.HTTP_201_CREATED)
def create_lot(body: LotIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lot = ParkingLot(**body.model_dump())
    db.add(lot); db.commit(); db.refresh(lot)
    return lot


@router.patch("/lots/{lot_id}", response_model=LotOut)
def update_lot(lot_id: int, body: LotUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lot = db.get(ParkingLot, lot_id)
    if lot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bãi")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lot, field, value)
    db.commit(); db.refresh(lot)
    return lot


@router.get("/floors", response_model=list[FloorOut])
def list_floors(lot_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Floor).order_by(Floor.id)
    if lot_id is not None:
        stmt = stmt.where(Floor.lot_id == lot_id)
    return list(db.scalars(stmt).all())


@router.post("/floors", response_model=FloorOut, status_code=status.HTTP_201_CREATED)
def create_floor(body: FloorIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.get(ParkingLot, body.lot_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bãi")
    floor = Floor(**body.model_dump())
    db.add(floor); db.commit(); db.refresh(floor)
    return floor


@router.patch("/floors/{floor_id}", response_model=FloorOut)
def update_floor(floor_id: int, body: FloorUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    floor = db.get(Floor, floor_id)
    if floor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy tầng")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(floor, field, value)
    db.commit(); db.refresh(floor)
    return floor


@router.get("/zones", response_model=list[ZoneOut])
def list_zones(lot_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Zone).order_by(Zone.id)
    if lot_id is not None:
        stmt = stmt.where(Zone.lot_id == lot_id)
    return list(db.scalars(stmt).all())


@router.post("/zones", response_model=ZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(body: ZoneIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.get(ParkingLot, body.lot_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bãi")
    zone = Zone(**body.model_dump())
    db.add(zone); db.commit(); db.refresh(zone)
    return zone


@router.patch("/zones/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, body: ZoneUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy khu")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(zone, field, value)
    db.commit(); db.refresh(zone)
    return zone
```

- [ ] **Step 5: Register the router**

In `src/backend/app/main.py`, add `spaces` to the routers import line:

```python
from app.routers import auth, captures, config, gate_ws, health, images, readings, sessions, spaces, stats, users
```

And add this line next to the other `include_router` calls (after `app.include_router(config.router)`):

```python
    app.include_router(spaces.router)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_spaces_crud.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/schemas/space.py src/backend/app/routers/spaces.py src/backend/app/main.py src/backend/tests/test_spaces_crud.py
git commit -m "feat(backend): add CRUD endpoints for lots, floors, zones"
```

---

### Task 4: Endpoint sức chứa

**Files:**
- Modify: `src/backend/app/routers/spaces.py`
- Test: `src/backend/tests/test_occupancy_endpoint.py`

**Interfaces:**
- Consumes: `occupancy_report` từ Task 2; router `spaces` từ Task 3.
- Produces: `GET /occupancy` trả `{"lots": [...]}` với hình dạng từ `occupancy_report`. Đọc cho `staff` và `admin`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_occupancy_endpoint.py`:

```python
def test_occupancy_endpoint_reports_lots_and_zones(client, admin_headers, staff_headers):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 4}, headers=admin_headers).json()["id"]
    client.post("/zones", json={"lot_id": lot_id, "name": "Z1", "capacity": 2}, headers=admin_headers)

    data = client.get("/occupancy", headers=staff_headers).json()
    row = next(r for r in data["lots"] if r["lot_id"] == lot_id)
    assert row["capacity"] == 4
    assert row["occupancy"] == 0
    assert row["available"] == 4
    assert len(row["zones"]) == 1


def test_occupancy_endpoint_requires_auth(client):
    assert client.get("/occupancy").status_code in (401, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_occupancy_endpoint.py -v`
Expected: FAIL (404 on `/occupancy`).

- [ ] **Step 3: Add the endpoint**

In `src/backend/app/routers/spaces.py`, add the import near the top (after the existing `from app.schemas.space import ...` block):

```python
from app.services.occupancy import occupancy_report
```

And append this route at the end of the file:

```python
@router.get("/occupancy")
def get_occupancy(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"lots": occupancy_report(db)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_occupancy_endpoint.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/backend/app/routers/spaces.py src/backend/tests/test_occupancy_endpoint.py
git commit -m "feat(backend): add GET /occupancy endpoint"
```

---

### Task 5: Xác nhận vào nhận `zone_id` và chặn khi đầy bãi

**Files:**
- Modify: `src/backend/app/schemas/session.py`
- Modify: `src/backend/app/routers/sessions.py`
- Test: `src/backend/tests/test_entry_capacity.py`

**Interfaces:**
- Consumes: `lot_is_full` từ Task 2; `Zone` từ Task 1; `make_reading` fixture từ Task 1.
- Produces: `EntryRequest` thêm `zone_id: int | None = None`. `POST /sessions/entry` khi có `zone_id`: gán `session.lot_id` (suy từ `zone.lot_id`) và `session.zone_id`; nếu bãi đầy trả HTTP 409. Không có `zone_id` thì hành vi như cũ.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_entry_capacity.py`:

```python
def test_entry_assigns_lot_and_zone_and_counts(client, admin_headers, staff_headers, make_reading):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 10}, headers=admin_headers).json()["id"]
    zone_id = client.post("/zones", json={"lot_id": lot_id, "name": "Z1", "capacity": 5}, headers=admin_headers).json()["id"]

    reading = make_reading(plate="51F00001", direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id, "zone_id": zone_id}, headers=staff_headers)
    assert r.status_code == 200

    row = next(x for x in client.get("/occupancy", headers=staff_headers).json()["lots"] if x["lot_id"] == lot_id)
    assert row["occupancy"] == 1
    assert row["zones"][0]["occupancy"] == 1


def test_entry_rejected_when_lot_full(client, admin_headers, staff_headers, make_reading):
    lot_id = client.post("/lots", json={"name": "A", "capacity": 1}, headers=admin_headers).json()["id"]
    zone_id = client.post("/zones", json={"lot_id": lot_id, "name": "Z", "capacity": 1}, headers=admin_headers).json()["id"]

    r1 = make_reading(plate="51F11111", direction="in")
    assert client.post("/sessions/entry", json={"reading_id": r1.id, "zone_id": zone_id}, headers=staff_headers).status_code == 200

    r2 = make_reading(plate="51F22222", direction="in")
    resp = client.post("/sessions/entry", json={"reading_id": r2.id, "zone_id": zone_id}, headers=staff_headers)
    assert resp.status_code == 409


def test_entry_without_zone_still_works(client, staff_headers, make_reading):
    reading = make_reading(plate="51F33333", direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.status_code == 200


def test_entry_unknown_zone_returns_404(client, staff_headers, make_reading):
    reading = make_reading(plate="51F44444", direction="in")
    r = client.post("/sessions/entry", json={"reading_id": reading.id, "zone_id": 9999}, headers=staff_headers)
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_entry_capacity.py -v`
Expected: FAIL (`zone_id` bị bỏ qua; occupancy 0; không có 409).

- [ ] **Step 3: Extend `EntryRequest`**

In `src/backend/app/schemas/session.py`, replace the `EntryRequest` class:

```python
class EntryRequest(BaseModel):
    reading_id: int
    zone_id: int | None = None
```

- [ ] **Step 4: Wire zone resolution and capacity check into entry**

In `src/backend/app/routers/sessions.py`, extend the models import to include `Zone`:

```python
from app.models import ImageAsset, ParkingSession, PlateReading, User, Zone
```

Add this import next to the other service imports:

```python
from app.services.occupancy import lot_is_full
```

In `confirm_entry`, insert the lot resolution block immediately after the reading validation (right after the `raise HTTPException(... "không tìm thấy reading vào hợp lệ")` line and before `group = group_for(...)`):

```python
    lot_id = None
    if body.zone_id is not None:
        zone = db.get(Zone, body.zone_id)
        if zone is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy khu")
        lot_id = zone.lot_id
        if lot_is_full(db, lot_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "bãi đã đầy")
```

In the same function, add two keyword arguments to the `ParkingSession(...)` constructor (for example right after `entry_reading_id=reading.id,`):

```python
        lot_id=lot_id,
        zone_id=body.zone_id,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_entry_capacity.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/schemas/session.py src/backend/app/routers/sessions.py src/backend/tests/test_entry_capacity.py
git commit -m "feat(backend): entry assigns zone and rejects when lot is full"
```

---

### Task 6: Test nghiệm thu phase và chạy toàn suite

**Files:**
- Test: `src/backend/tests/test_phase1_multilot_acceptance.py`

**Interfaces:**
- Consumes: mọi thứ ở Task 1 tới 5.

- [ ] **Step 1: Write the acceptance test**

Create `src/backend/tests/test_phase1_multilot_acceptance.py`:

```python
def test_multilot_capacity_end_to_end(client, admin_headers, staff_headers, make_reading):
    # admin dựng một bãi hai tầng, mỗi tầng một khu, sức chứa bãi 2
    lot_id = client.post("/lots", json={"name": "Bai Trung Tam", "capacity": 2}, headers=admin_headers).json()["id"]
    f1 = client.post("/floors", json={"lot_id": lot_id, "name": "Tang 1", "capacity": 1}, headers=admin_headers).json()["id"]
    f2 = client.post("/floors", json={"lot_id": lot_id, "name": "Tang 2", "capacity": 1}, headers=admin_headers).json()["id"]
    z1 = client.post("/zones", json={"lot_id": lot_id, "floor_id": f1, "name": "Khu A", "capacity": 1}, headers=admin_headers).json()["id"]
    z2 = client.post("/zones", json={"lot_id": lot_id, "floor_id": f2, "name": "Khu B", "capacity": 1}, headers=admin_headers).json()["id"]

    # hai xe vào hai khu khác nhau, lấp đầy bãi
    a = make_reading(plate="51F00001", direction="in")
    b = make_reading(plate="51F00002", direction="in")
    assert client.post("/sessions/entry", json={"reading_id": a.id, "zone_id": z1}, headers=staff_headers).status_code == 200
    assert client.post("/sessions/entry", json={"reading_id": b.id, "zone_id": z2}, headers=staff_headers).status_code == 200

    # báo cáo sức chứa: bãi đầy, mỗi khu 1 xe
    report = client.get("/occupancy", headers=staff_headers).json()["lots"]
    row = next(r for r in report if r["lot_id"] == lot_id)
    assert row["occupancy"] == 2
    assert row["available"] == 0
    assert row["full"] is True
    assert {z["zone_id"]: z["occupancy"] for z in row["zones"]} == {z1: 1, z2: 1}

    # xe thứ ba bị chặn vì bãi đầy
    c = make_reading(plate="51F00003", direction="in")
    assert client.post("/sessions/entry", json={"reading_id": c.id, "zone_id": z1}, headers=staff_headers).status_code == 409
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd src/backend && python -m pytest tests/test_phase1_multilot_acceptance.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS toàn bộ (suite cũ cộng mọi test phase 1). Không regression.

- [ ] **Step 4: Commit**

```bash
git add src/backend/tests/test_phase1_multilot_acceptance.py
git commit -m "test(backend): phase 1 multi-lot capacity acceptance"
```

---

## Self-Review

**Spec coverage (spec kiến trúc mục 6.2, 6.8 và spec frontend v2 mục 5.5, 5.8):**
- Mô hình bãi, tầng, khu: Task 1. CRUD admin: Task 3. Đếm chiếm dụng thời gian thực: Task 2. Chặn đầy bãi: Task 5. Endpoint sức chứa cho màn 5.8: Task 4. Gắn phiên với bãi và khu: Task 5. Đủ phạm vi phase 1.
- Ngoài phạm vi phase này (nằm ở phase sau): giá theo bãi (phase 5), phân công nhân viên theo bãi (phase 3 hoặc 6), UUID toàn cục (phase 6), tra cứu liên bãi (phase 6). Không phải gap, là sắp xếp.

**Placeholder scan:** không có TBD, không có bước mô tả suông thiếu code. Mọi bước code có code thật.

**Type consistency:** `lot_is_full(db, lot_id)`, `occupancy_report(db)` dùng thống nhất giữa Task 2, 4, 5. Khóa dict báo cáo (`lot_id, occupancy, available, full, zones`) khớp giữa service (Task 2), endpoint (Task 4), và test nghiệm thu (Task 6). `EntryRequest.zone_id` khớp giữa schema (Task 5 step 3) và router (Task 5 step 4). Tên bảng `session`, `parking_lot`, `zone` khớp giữa model và migration.

**Ghi chú:** capacity ở mức bãi là nguồn chặn vào; capacity tầng và khu để hiển thị và mở rộng, phase 1 không chặn ở mức khu (tránh mơ hồ khi tổng capacity khu khác capacity bãi).
