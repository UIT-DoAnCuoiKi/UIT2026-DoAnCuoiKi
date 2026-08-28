# Mảng C: Danh mục loại xe (vehicle_group) + giá Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa nhóm tính tiền (`vehicle_group`) thành danh mục CRUD có tên thân thiện (`display_name`), thay map cứng gạch dưới; UI mọi nơi hiển thị `display_name`; giá đặt theo từng nhóm.

**Architecture:** Thêm bảng `vehicle_group` (code, display_name, active, sort_order) làm lớp hiển thị + danh mục, giữ nguyên `price_rule` (keyed theo code) và `group_for` (seed constant map lớp ML sang nhóm). Router CRUD mới `/vehicle-groups` (đọc cho mọi user, ghi cho manager/root). Frontend gộp danh mục + giá vào một tab, thêm hook `useVehicleGroupMap()` để render `display_name`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest (backend, sqlite in memory); React 19, React Query, orval codegen, Vitest, Testing Library (frontend).

## Global Constraints

- Ba vai hợp lệ: `root`, `manager`, `staff` (từ mảng A đã build). Ghi danh mục và giá: `require_role("manager", "root")`. Đọc: mọi user đăng nhập.
- Phân biệt hai trường: `vehicle_type` là lớp ML detector (motorbike/car/truck/bus, bất biến), `vehicle_group` là nhóm tính tiền (xe_may/o_to_con/...). Operator chỉ quản `vehicle_group`.
- `group_for` và `_MAP` giữ là seed constant, không đọc DB, không sửa logic ánh xạ.
- Không thêm giá theo khung giờ (backlog). `grace_minutes` và `daily_cap` đã có trong `price_rule`, không làm lại.
- Backend test chạy tại `src/backend` bằng venv dự án: `.venv/bin/pytest`. Frontend test chạy tại `src/frontend`: `npm run test`.
- Sau khi thêm endpoint backend, tái sinh client: tại `src/backend` chạy `.venv/bin/python scripts/export_openapi.py` (ghi `src/frontend/openapi.json`), rồi tại `src/frontend` chạy `npm run gen:api`.
- Văn bản tiếng Việt không dùng ký tự gạch ngang làm dấu câu; đường dẫn và định danh trong code giữ nguyên.
- Không tự commit ngoài các bước Commit ghi rõ trong plan; không push.

## File Structure

**Backend (`src/backend`):**
- Create `app/models/vehicle_group.py` — model `VehicleGroup`.
- Modify `app/models/__init__.py` — đăng ký `VehicleGroup`.
- Modify `app/services/vehicle_groups.py` — thêm `DEFAULT_VEHICLE_GROUPS` + `seed_default_vehicle_groups`.
- Create `app/schemas/vehicle_group.py` — `VehicleGroupIn/Update/Out`.
- Create `app/routers/vehicle_groups.py` — CRUD router.
- Modify `app/main.py` — include router.
- Modify `app/routers/config.py` — validate `vehicle_group` khi tạo `price_rule`.
- Create `alembic/versions/a7b8c9d0e1f2_add_vehicle_group.py` — migration + seed.
- Create `scripts/seed_vehicle_groups.py` — seed cho deployment hiện có.
- Create `tests/test_vehicle_groups.py` — test danh mục + validation.

**Frontend (`src/frontend`):**
- Create `src/lib/vehicle-groups.ts` — hook `useVehicleGroupMap` + helper `groupLabel`.
- Create `src/lib/vehicle-groups.test.ts` — test helper/hook.
- Create `src/features/config/vehicle-groups-tab.tsx` — tab danh mục + giá.
- Create `src/features/config/vehicle-groups-tab.test.tsx`.
- Modify `src/features/config/config-page.tsx` — thay tab giá bằng tab loại xe.
- Modify `src/features/sessions/sessions-columns.tsx` — hiển thị `display_name`.
- Modify `src/features/sessions/session-detail-page.tsx` — hiển thị `display_name`.
- Modify `src/features/gate/gate-capture.tsx` — chip nhóm dùng `display_name`.

---

### Task 1: Model VehicleGroup + seed

**Files:**
- Create: `src/backend/app/models/vehicle_group.py`
- Modify: `src/backend/app/models/__init__.py`
- Modify: `src/backend/app/services/vehicle_groups.py`
- Test: `src/backend/tests/test_vehicle_groups.py`

**Interfaces:**
- Produces: `VehicleGroup` model (`id`, `code`, `display_name`, `active`, `sort_order`, `created_at`, `updated_at`); `DEFAULT_VEHICLE_GROUPS: list[dict]`; `seed_default_vehicle_groups(db) -> int` (idempotent, trả số nhóm mới tạo).

- [ ] **Step 1: Viết test thất bại**

Tạo `src/backend/tests/test_vehicle_groups.py`:

```python
from sqlalchemy import select

from app.models import VehicleGroup
from app.services.vehicle_groups import seed_default_vehicle_groups


def test_seed_creates_five_groups(db_session):
    created = seed_default_vehicle_groups(db_session)
    assert created == 5
    codes = set(db_session.scalars(select(VehicleGroup.code)).all())
    assert codes == {"xe_may", "o_to_con", "xe_tai", "xe_khach", "unknown"}
    xe_may = db_session.scalars(select(VehicleGroup).where(VehicleGroup.code == "xe_may")).one()
    assert xe_may.display_name == "Xe máy"


def test_seed_is_idempotent(db_session):
    seed_default_vehicle_groups(db_session)
    again = seed_default_vehicle_groups(db_session)
    assert again == 0
    total = len(db_session.scalars(select(VehicleGroup)).all())
    assert total == 5
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -v`
Expected: FAIL — `ImportError: cannot import name 'VehicleGroup'`.

- [ ] **Step 3: Tạo model**

`src/backend/app/models/vehicle_group.py`:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class VehicleGroup(Base):
    __tablename__ = "vehicle_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # mã kỹ thuật, immutable
    display_name: Mapped[str] = mapped_column(String(64))                   # tên thân thiện
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: Đăng ký model**

Trong `src/backend/app/models/__init__.py` thêm import (theo thứ tự alphabet, cạnh các import khác) và tên vào `__all__`:

```python
from app.models.vehicle_group import VehicleGroup
```

Thêm `"VehicleGroup"` vào list `__all__`.

- [ ] **Step 5: Thêm seed vào service (giữ nguyên `_MAP` và `group_for`)**

Trong `src/backend/app/services/vehicle_groups.py`, thêm phía dưới `group_for` (không đổi `_MAP` và `group_for`):

```python
DEFAULT_VEHICLE_GROUPS = [
    {"code": "xe_may", "display_name": "Xe máy", "sort_order": 1},
    {"code": "o_to_con", "display_name": "Ô tô con", "sort_order": 2},
    {"code": "xe_tai", "display_name": "Xe tải", "sort_order": 3},
    {"code": "xe_khach", "display_name": "Xe khách", "sort_order": 4},
    {"code": "unknown", "display_name": "Chưa xác định", "sort_order": 99},
]


def seed_default_vehicle_groups(db) -> int:
    """Seed danh mục nhóm mặc định. Idempotent: bỏ qua code đã tồn tại."""
    from sqlalchemy import select

    from app.models import VehicleGroup

    created = 0
    for row in DEFAULT_VEHICLE_GROUPS:
        exists = db.scalars(select(VehicleGroup).where(VehicleGroup.code == row["code"])).first()
        if exists is None:
            db.add(VehicleGroup(**row))
            created += 1
    db.commit()
    return created
```

- [ ] **Step 6: Chạy test để xác nhận pass**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/models/vehicle_group.py src/backend/app/models/__init__.py src/backend/app/services/vehicle_groups.py src/backend/tests/test_vehicle_groups.py
git commit -m "feat(vehicle-group): model danh muc nhom xe + seed mac dinh"
```

---

### Task 2: Schemas + router GET/POST/PATCH + guards

**Files:**
- Create: `src/backend/app/schemas/vehicle_group.py`
- Create: `src/backend/app/routers/vehicle_groups.py`
- Modify: `src/backend/app/main.py`
- Test: `src/backend/tests/test_vehicle_groups.py`

**Interfaces:**
- Consumes: `VehicleGroup` model, `seed_default_vehicle_groups` (Task 1); `require_role`, `get_current_user` (`app/deps.py`).
- Produces: endpoints `GET /vehicle-groups`, `POST /vehicle-groups`, `PATCH /vehicle-groups/{id}`; schemas `VehicleGroupIn` (`code`, `display_name`, `sort_order=0`, `active=True`), `VehicleGroupUpdate` (`display_name?`, `sort_order?`, `active?`), `VehicleGroupOut` (`id`, `code`, `display_name`, `active`, `sort_order`). Handler names `list_vehicle_groups`, `create_vehicle_group`, `update_vehicle_group` (orval hooks: `useListVehicleGroups`, `useCreateVehicleGroup`, `useUpdateVehicleGroup`).

- [ ] **Step 1: Viết test thất bại**

Thêm vào `src/backend/tests/test_vehicle_groups.py` (đầu file thêm helper `_token`; nếu đã có thì bỏ qua):

```python
def _token(client, make_user, role):
    make_user(username=role, password="pw", role=role)
    return client.post("/auth/login", json={"username": role, "password": "pw"}).json()["access_token"]


def _seed(client):
    # client và db_session dùng chung engine (conftest override get_db)
    from app.services.vehicle_groups import seed_default_vehicle_groups
    from app.deps import get_db

    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    seed_default_vehicle_groups(db)


def test_list_vehicle_groups_any_user(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.get("/vehicle-groups", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert [g["code"] for g in body][:2] == ["xe_may", "o_to_con"]  # theo sort_order


def test_create_vehicle_group_manager(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'manager')}"}
    r = client.post("/vehicle-groups", json={"code": "xe_dien", "display_name": "Xe điện", "sort_order": 5}, headers=h)
    assert r.status_code == 201
    assert r.json()["display_name"] == "Xe điện"


def test_create_vehicle_group_staff_forbidden(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.post("/vehicle-groups", json={"code": "xe_dien", "display_name": "Xe điện"}, headers=h)
    assert r.status_code == 403


def test_create_duplicate_code_conflict(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    r = client.post("/vehicle-groups", json={"code": "xe_may", "display_name": "Trùng"}, headers=h)
    assert r.status_code == 409


def test_patch_vehicle_group(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    from app.models import VehicleGroup
    from sqlalchemy import select
    gid = db_session.scalars(select(VehicleGroup).where(VehicleGroup.code == "xe_tai")).one().id
    h = {"Authorization": f"Bearer {_token(client, make_user, 'manager')}"}
    r = client.patch(f"/vehicle-groups/{gid}", json={"display_name": "Xe tải nhẹ", "active": False}, headers=h)
    assert r.status_code == 200
    assert r.json()["display_name"] == "Xe tải nhẹ"
    assert r.json()["active"] is False
```

Ghi chú: `db_session` và `client` dùng chung engine (conftest `client` override `get_db` bằng `db_session`), nên seed qua `db_session` thấy được ở request.

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -v`
Expected: FAIL — 404 do route chưa tồn tại.

- [ ] **Step 3: Tạo schemas**

`src/backend/app/schemas/vehicle_group.py`:

```python
from pydantic import BaseModel


class VehicleGroupIn(BaseModel):
    code: str
    display_name: str
    sort_order: int = 0
    active: bool = True


class VehicleGroupUpdate(BaseModel):
    display_name: str | None = None
    sort_order: int | None = None
    active: bool | None = None


class VehicleGroupOut(BaseModel):
    id: int
    code: str
    display_name: str
    active: bool
    sort_order: int
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Tạo router**

`src/backend/app/routers/vehicle_groups.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import User, VehicleGroup
from app.schemas.vehicle_group import VehicleGroupIn, VehicleGroupOut, VehicleGroupUpdate

router = APIRouter(prefix="/vehicle-groups", tags=["vehicle-groups"])
admin_only = require_role("manager", "root")


@router.get("", response_model=list[VehicleGroupOut])
def list_vehicle_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(VehicleGroup).order_by(VehicleGroup.sort_order, VehicleGroup.id)).all())


@router.post("", response_model=VehicleGroupOut, status_code=status.HTTP_201_CREATED)
def create_vehicle_group(body: VehicleGroupIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.scalars(select(VehicleGroup).where(VehicleGroup.code == body.code)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "code đã tồn tại")
    group = VehicleGroup(**body.model_dump())
    db.add(group); db.commit(); db.refresh(group)
    return group


@router.patch("/{group_id}", response_model=VehicleGroupOut)
def update_vehicle_group(group_id: int, body: VehicleGroupUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    group = db.get(VehicleGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy nhóm")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(group, field, value)
    db.commit(); db.refresh(group)
    return group
```

- [ ] **Step 5: Include router trong main.py**

Trong `src/backend/app/main.py`: thêm `vehicle_groups` vào dòng import `from app.routers import ...` và thêm dòng include (đặt cạnh `config`):

```python
    app.include_router(vehicle_groups.router)
```

- [ ] **Step 6: Chạy test để xác nhận pass**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -v`
Expected: PASS (7 passed gồm Task 1).

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/schemas/vehicle_group.py src/backend/app/routers/vehicle_groups.py src/backend/app/main.py src/backend/tests/test_vehicle_groups.py
git commit -m "feat(vehicle-group): router CRUD doc/ghi theo vai + rang buoc code"
```

---

### Task 3: DELETE với chặn tham chiếu

**Files:**
- Modify: `src/backend/app/routers/vehicle_groups.py`
- Test: `src/backend/tests/test_vehicle_groups.py`

**Interfaces:**
- Consumes: router Task 2; models `ParkingSession`, `PriceRule`, `MonthlyPass` (đều có cột `vehicle_group: str`).
- Produces: `DELETE /vehicle-groups/{id}` trả 204 nếu xóa được, 409 nếu referenced, 404 nếu không thấy. Handler `delete_vehicle_group` (hook `useDeleteVehicleGroup`).

- [ ] **Step 1: Viết test thất bại**

Thêm vào `src/backend/tests/test_vehicle_groups.py`:

```python
def test_delete_unreferenced_group_ok(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    created = client.post("/vehicle-groups", json={"code": "xe_dien", "display_name": "Xe điện"}, headers=h).json()
    r = client.delete(f"/vehicle-groups/{created['id']}", headers=h)
    assert r.status_code == 204


def test_delete_referenced_group_conflict(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    from app.models import PriceRule, VehicleGroup
    from sqlalchemy import select
    db_session.add(PriceRule(vehicle_group="xe_may", mode="flat", unit_price=3000))
    db_session.commit()
    gid = db_session.scalars(select(VehicleGroup).where(VehicleGroup.code == "xe_may")).one().id
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    r = client.delete(f"/vehicle-groups/{gid}", headers=h)
    assert r.status_code == 409


def test_delete_group_staff_forbidden(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    from app.models import VehicleGroup
    from sqlalchemy import select
    gid = db_session.scalars(select(VehicleGroup).where(VehicleGroup.code == "unknown")).one().id
    h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    assert client.delete(f"/vehicle-groups/{gid}", headers=h).status_code == 403
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -k delete -v`
Expected: FAIL — 405 Method Not Allowed (chưa có DELETE).

- [ ] **Step 3: Thêm endpoint DELETE**

Trong `src/backend/app/routers/vehicle_groups.py`: mở rộng import models và thêm endpoint:

```python
from app.models import MonthlyPass, ParkingSession, PriceRule, User, VehicleGroup
```

```python
@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_group(group_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    group = db.get(VehicleGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy nhóm")
    referenced = (
        db.scalars(select(ParkingSession.id).where(ParkingSession.vehicle_group == group.code).limit(1)).first()
        or db.scalars(select(PriceRule.id).where(PriceRule.vehicle_group == group.code).limit(1)).first()
        or db.scalars(select(MonthlyPass.id).where(MonthlyPass.vehicle_group == group.code).limit(1)).first()
    )
    if referenced is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "nhóm đang được sử dụng")
    db.delete(group); db.commit()
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -v`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add src/backend/app/routers/vehicle_groups.py src/backend/tests/test_vehicle_groups.py
git commit -m "feat(vehicle-group): DELETE chan khi nhom dang duoc tham chieu"
```

---

### Task 4: Validate vehicle_group khi tạo price_rule

**Files:**
- Modify: `src/backend/app/routers/config.py`
- Test: `src/backend/tests/test_vehicle_groups.py`

**Interfaces:**
- Consumes: `VehicleGroup` model; `create_price_rule` hiện có trong `config.py`.
- Produces: `POST /price-rules` trả 422 nếu `vehicle_group` không có trong danh mục.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `src/backend/tests/test_vehicle_groups.py`:

```python
def test_price_rule_rejects_unknown_group(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    r = client.post("/price-rules", json={"vehicle_group": "khong_ton_tai", "mode": "flat", "unit_price": 1000}, headers=h)
    assert r.status_code == 422


def test_price_rule_accepts_seeded_group(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    r = client.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=h)
    assert r.status_code == 201
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -k price_rule -v`
Expected: FAIL — `test_price_rule_rejects_unknown_group` trả 201 thay vì 422.

- [ ] **Step 3: Thêm validation vào config.py**

Trong `src/backend/app/routers/config.py`: thêm `VehicleGroup` vào import models và chèn kiểm tra ngay đầu `create_price_rule`, sau các kiểm tra `mode`:

Đổi import:
```python
from app.models import FeatureToggle, Lane, PriceRule, User, VehicleGroup
```

Trong `create_price_rule`, sau khối kiểm `mode` và trước dòng `rule = PriceRule(...)`:
```python
    if not db.scalars(select(VehicleGroup).where(VehicleGroup.code == body.vehicle_group)).first():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "vehicle_group không tồn tại")
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `.venv/bin/pytest tests/test_vehicle_groups.py -v && .venv/bin/pytest tests/test_config.py -v`
Expected: PASS cả hai. Lưu ý `tests/test_config.py::test_price_rule_crud_root` không seed danh mục nên có thể fail sau thay đổi này.

- [ ] **Step 5: Sửa test_config.py cho khớp ràng buộc mới**

Trong `src/backend/tests/test_config.py`, ở `test_price_rule_crud_root` và `test_price_rule_create_forbidden_for_staff`, seed danh mục trước khi tạo price_rule. Thêm ngay sau khi lấy header `h` trong `test_price_rule_crud_root`:

```python
    from app.services.vehicle_groups import seed_default_vehicle_groups
    from app.deps import get_db
    seed_default_vehicle_groups(next(client.app.dependency_overrides[get_db]()))
```

Ghi chú: `test_price_rule_create_forbidden_for_staff` trả 403 trước khi chạm validation (guard chặn trước), nên không cần seed. Kiểm lại: nếu test đó vẫn pass thì để nguyên.

- [ ] **Step 6: Chạy lại test để xác nhận pass**

Run: `.venv/bin/pytest tests/test_config.py tests/test_vehicle_groups.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/routers/config.py src/backend/tests/test_config.py src/backend/tests/test_vehicle_groups.py
git commit -m "feat(price-rule): chan tao gia voi vehicle_group khong co trong danh muc"
```

---

### Task 5: Migration + seed script

**Files:**
- Create: `src/backend/alembic/versions/a7b8c9d0e1f2_add_vehicle_group.py`
- Create: `src/backend/scripts/seed_vehicle_groups.py`

**Interfaces:**
- Consumes: `seed_default_vehicle_groups` (Task 1); `SessionLocal` (`app/db.py`).
- Produces: bảng `vehicle_group` khi `alembic upgrade head`; script seed idempotent cho DB hiện có.

- [ ] **Step 1: Tạo migration**

`src/backend/alembic/versions/a7b8c9d0e1f2_add_vehicle_group.py`:

```python
"""add vehicle_group catalog

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_group",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_vehicle_group_code"),
    )
    op.bulk_insert(
        sa.table(
            "vehicle_group",
            sa.column("code", sa.String),
            sa.column("display_name", sa.String),
            sa.column("sort_order", sa.Integer),
            sa.column("active", sa.Boolean),
        ),
        [
            {"code": "xe_may", "display_name": "Xe máy", "sort_order": 1, "active": True},
            {"code": "o_to_con", "display_name": "Ô tô con", "sort_order": 2, "active": True},
            {"code": "xe_tai", "display_name": "Xe tải", "sort_order": 3, "active": True},
            {"code": "xe_khach", "display_name": "Xe khách", "sort_order": 4, "active": True},
            {"code": "unknown", "display_name": "Chưa xác định", "sort_order": 99, "active": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("vehicle_group")
```

Ghi chú: kiểm `down_revision` khớp head hiện tại bằng `.venv/bin/alembic heads`. Nếu head khác `f6a7b8c9d0e1`, sửa `down_revision` cho đúng.

- [ ] **Step 2: Tạo seed script**

`src/backend/scripts/seed_vehicle_groups.py`:

```python
"""Seed danh mục vehicle_group cho deployment hiện có (idempotent)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.services.vehicle_groups import seed_default_vehicle_groups  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        n = seed_default_vehicle_groups(db)
        print(f"Seed vehicle_group: thêm {n} nhóm")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify migration áp được**

Run (tại `src/backend`): `.venv/bin/alembic upgrade head`
Expected: không lỗi; bảng `vehicle_group` tồn tại với 5 dòng. Kiểm nhanh: `.venv/bin/python -c "from app.db import SessionLocal; from app.models import VehicleGroup; from sqlalchemy import select; db=SessionLocal(); print(sorted(db.scalars(select(VehicleGroup.code)).all()))"`
Expected in ra: `['o_to_con', 'unknown', 'xe_khach', 'xe_may', 'xe_tai']`.

- [ ] **Step 4: Commit**

```bash
git add src/backend/alembic/versions/a7b8c9d0e1f2_add_vehicle_group.py src/backend/scripts/seed_vehicle_groups.py
git commit -m "feat(vehicle-group): migration tao bang + seed script cho deployment"
```

---

### Task 6: Regenerate client + hook useVehicleGroupMap

**Files:**
- Regenerate: `src/frontend/openapi.json`, `src/frontend/src/api/generated/**`
- Create: `src/frontend/src/lib/vehicle-groups.ts`
- Test: `src/frontend/src/lib/vehicle-groups.test.ts`

**Interfaces:**
- Consumes: hook `useListVehicleGroups` (từ codegen), model `VehicleGroupOut` (`code`, `display_name`, ...).
- Produces: `useVehicleGroupMap(): Record<string, string>`; `groupLabel(map, code?): string` (trả `display_name`, fallback `code`, `"—"` nếu rỗng).

- [ ] **Step 1: Tái sinh OpenAPI + client**

Run (tại `src/backend`): `.venv/bin/python scripts/export_openapi.py`
Run (tại `src/frontend`): `npm run gen:api`
Expected: xuất hiện `src/frontend/src/api/generated/vehicle-groups/vehicle-groups.ts` với `useListVehicleGroups`, `useCreateVehicleGroup`, `useUpdateVehicleGroup`, `useDeleteVehicleGroup`; model `VehicleGroupOut` trong `src/api/generated/model`.

- [ ] **Step 2: Viết test thất bại**

`src/frontend/src/lib/vehicle-groups.test.ts`:

```ts
import { groupLabel } from "./vehicle-groups";

test("groupLabel returns display_name when present", () => {
  const map = { xe_may: "Xe máy", o_to_con: "Ô tô con" };
  expect(groupLabel(map, "xe_may")).toBe("Xe máy");
});

test("groupLabel falls back to code when unknown", () => {
  expect(groupLabel({}, "xe_la")).toBe("xe_la");
});

test("groupLabel returns dash for empty", () => {
  expect(groupLabel({}, null)).toBe("—");
});
```

- [ ] **Step 3: Chạy test để xác nhận fail**

Run: `npm run test -- src/lib/vehicle-groups.test.ts`
Expected: FAIL — không import được `groupLabel`.

- [ ] **Step 4: Tạo hook + helper**

`src/frontend/src/lib/vehicle-groups.ts`:

```ts
import { useListVehicleGroups } from "@/api/generated/vehicle-groups/vehicle-groups";

export function useVehicleGroupMap(): Record<string, string> {
  const { data } = useListVehicleGroups();
  const map: Record<string, string> = {};
  for (const g of data ?? []) map[g.code] = g.display_name;
  return map;
}

export function groupLabel(map: Record<string, string>, code?: string | null): string {
  if (!code) return "—";
  return map[code] ?? code;
}
```

- [ ] **Step 5: Chạy test để xác nhận pass**

Run: `npm run test -- src/lib/vehicle-groups.test.ts`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add src/frontend/openapi.json src/frontend/src/api/generated src/frontend/src/lib/vehicle-groups.ts src/frontend/src/lib/vehicle-groups.test.ts
git commit -m "feat(ui): sinh client vehicle-groups + hook useVehicleGroupMap"
```

---

### Task 7: Tab "Loại xe" (danh mục + giá) + swap vào config-page

**Files:**
- Create: `src/frontend/src/features/config/vehicle-groups-tab.tsx`
- Create: `src/frontend/src/features/config/vehicle-groups-tab.test.tsx`
- Modify: `src/frontend/src/features/config/config-page.tsx`

**Interfaces:**
- Consumes: `useListVehicleGroups`, `useCreateVehicleGroup`, `useUpdateVehicleGroup`, `useDeleteVehicleGroup`; `useListPriceRules`, `useCreatePriceRule`, `useUpdatePriceRule` (`@/api/generated/config/config`); `DataTable`, `Button`, `Input`, `formatVnd`.
- Produces: component `VehicleGroupsTab`; tab "Loại xe" trong config-page thay tab "Bảng giá".

- [ ] **Step 1: Viết test thất bại**

`src/frontend/src/features/config/vehicle-groups-tab.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { VehicleGroupsTab } from "./vehicle-groups-tab";

vi.mock("@/api/generated/vehicle-groups/vehicle-groups", () => ({
  useListVehicleGroups: () => ({
    data: [
      { id: 1, code: "xe_may", display_name: "Xe máy", active: true, sort_order: 1 },
      { id: 2, code: "o_to_con", display_name: "Ô tô con", active: true, sort_order: 2 },
    ],
    isLoading: false,
  }),
  useCreateVehicleGroup: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateVehicleGroup: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteVehicleGroup: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/config/config", () => ({
  useListPriceRules: () => ({ data: [{ id: 9, vehicle_group: "xe_may", mode: "flat", unit_price: 3000, active: true }] }),
  useCreatePriceRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdatePriceRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

test("renders friendly display_name, not raw code", () => {
  render(<VehicleGroupsTab />);
  expect(screen.getByText("Xe máy")).toBeInTheDocument();
  expect(screen.getByText("Ô tô con")).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/config/vehicle-groups-tab.test.tsx`
Expected: FAIL — không import được `VehicleGroupsTab`.

- [ ] **Step 3: Tạo component**

`src/frontend/src/features/config/vehicle-groups-tab.tsx`:

```tsx
import { useState } from "react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useListVehicleGroups,
  useCreateVehicleGroup,
  useUpdateVehicleGroup,
  useDeleteVehicleGroup,
} from "@/api/generated/vehicle-groups/vehicle-groups";
import { useListPriceRules, useCreatePriceRule, useUpdatePriceRule } from "@/api/generated/config/config";
import type { VehicleGroupOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatVnd } from "@/lib/format";
import { isAxiosError } from "axios";

export function VehicleGroupsTab() {
  const { data: groups, isLoading } = useListVehicleGroups();
  const { data: rules } = useListPriceRules();
  const update = useUpdateVehicleGroup();
  const remove = useDeleteVehicleGroup();
  const create = useCreateVehicleGroup();
  const createRule = useCreatePriceRule();
  const updateRule = useUpdatePriceRule();

  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");

  const ruleFor = (code: string) => (rules ?? []).find((r) => r.vehicle_group === code && r.active);

  const setPrice = async (code: string, unitPrice: number) => {
    const existing = ruleFor(code);
    if (existing) {
      await updateRule.mutateAsync({ ruleId: existing.id, data: { unit_price: unitPrice } });
    } else {
      await createRule.mutateAsync({ data: { vehicle_group: code, mode: "flat", unit_price: unitPrice } });
    }
    toast.success("Đã cập nhật giá");
  };

  const cols: ColumnDef<VehicleGroupOut, unknown>[] = [
    { header: "Tên hiển thị", accessorKey: "display_name" },
    { header: "Mã", accessorKey: "code" },
    {
      header: "Đơn giá",
      cell: ({ row }) => {
        const rule = ruleFor(row.original.code);
        return <span className="tnum">{rule ? formatVnd(rule.unit_price) : "—"}</span>;
      },
    },
    {
      header: "Đặt giá",
      cell: ({ row }) => (
        <PriceCell current={ruleFor(row.original.code)?.unit_price ?? null} onSave={(v) => setPrice(row.original.code, v)} />
      ),
    },
    {
      header: "Kích hoạt",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            await update.mutateAsync({ groupId: row.original.id, data: { active: !row.original.active } });
            toast.success("Đã cập nhật");
          }}
        >
          {row.original.active ? "Bật" : "Tắt"}
        </Button>
      ),
    },
    {
      header: "Xóa",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            try {
              await remove.mutateAsync({ groupId: row.original.id });
              toast.success("Đã xóa nhóm");
            } catch (e) {
              if (isAxiosError(e) && e.response?.status === 409) {
                toast.error("Nhóm đang được sử dụng, không xóa được");
              } else {
                toast.error("Xóa thất bại");
              }
            }
          }}
        >
          Xóa
        </Button>
      ),
    },
  ];

  const addGroup = async () => {
    if (!newCode.trim() || !newName.trim()) {
      toast.error("Nhập mã và tên hiển thị");
      return;
    }
    await create.mutateAsync({ data: { code: newCode.trim(), display_name: newName.trim() } });
    setNewCode("");
    setNewName("");
    toast.success("Đã thêm nhóm");
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <Input placeholder="Mã (vd: xe_dien)" value={newCode} onChange={(e) => setNewCode(e.target.value)} className="max-w-[180px]" />
        <Input placeholder="Tên hiển thị (vd: Xe điện)" value={newName} onChange={(e) => setNewName(e.target.value)} className="max-w-[220px]" />
        <Button onClick={addGroup}>Thêm nhóm</Button>
      </div>
      <DataTable columns={cols} data={groups ?? []} loading={isLoading} empty="Chưa có nhóm xe" />
    </div>
  );
}

function PriceCell({ current, onSave }: { current: number | null; onSave: (value: number) => Promise<void> }) {
  const [value, setValue] = useState<string>(current != null ? String(current) : "");
  return (
    <div className="flex items-center gap-1">
      <Input
        type="number"
        min={0}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="h-8 w-[110px]"
        aria-label="Đơn giá"
      />
      <Button
        variant="outline"
        size="sm"
        onClick={async () => {
          const n = Number(value);
          if (!Number.isFinite(n) || n < 0) {
            toast.error("Giá không hợp lệ");
            return;
          }
          await onSave(n);
        }}
      >
        Lưu
      </Button>
    </div>
  );
}
```

Ghi chú: nhập giá bằng ô input inline (`PriceCell`), không dùng `window.prompt`/`alert`/`confirm` (tránh chặn extension, nhất quán constraint mảng B). `PriceCell` giữ state cục bộ, nút Lưu gọi `setPrice` (patch rule active hoặc tạo mới).

- [ ] **Step 4: Swap vào config-page**

Trong `src/frontend/src/features/config/config-page.tsx`: thay import và tab "Bảng giá" bằng "Loại xe".

Đổi import dòng `PriceRulesTab`:
```tsx
import { VehicleGroupsTab } from "./vehicle-groups-tab";
```

Đổi `TabsTrigger`/`TabsContent` value `price`:
```tsx
          <TabsTrigger value="price">Loại xe</TabsTrigger>
```
```tsx
        <TabsContent value="price">
          <SurfaceCard variant="white">
            <VehicleGroupsTab />
          </SurfaceCard>
        </TabsContent>
```

Xóa dòng `import { PriceRulesTab } from "./price-rules-tab";` (file `price-rules-tab.tsx` giữ lại để tránh vỡ test cũ, hoặc xóa cùng test của nó nếu có; kiểm `git grep PriceRulesTab`).

- [ ] **Step 5: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/config/vehicle-groups-tab.test.tsx`
Expected: PASS.

- [ ] **Step 6: Kiểm không vỡ test config khác**

Run: `npm run test -- src/features/config`
Expected: PASS. Nếu có test cũ import `PriceRulesTab` đã gỡ khỏi trang, cập nhật hoặc xóa test đó cho khớp.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/features/config/vehicle-groups-tab.tsx src/frontend/src/features/config/vehicle-groups-tab.test.tsx src/frontend/src/features/config/config-page.tsx
git commit -m "feat(ui): tab Loai xe gop danh muc va gia, thay tab Bang gia"
```

---

### Task 8: Hiển thị display_name ở sessions + gate chip

**Files:**
- Modify: `src/frontend/src/features/sessions/sessions-columns.tsx`
- Modify: `src/frontend/src/features/sessions/session-detail-page.tsx`
- Modify: `src/frontend/src/features/gate/gate-capture.tsx`
- Test: cập nhật `src/frontend/src/features/sessions/sessions-page.test.tsx` nếu cần

**Interfaces:**
- Consumes: `useVehicleGroupMap`, `groupLabel` (Task 6).

- [ ] **Step 1: Viết test thất bại (sessions column hiển thị display_name)**

Trong `src/frontend/src/features/sessions/sessions-page.test.tsx`, mock lookup và đổi dữ liệu mock để nhóm là `xe_may`, kỳ vọng render "Xe máy". Thêm mock:

```tsx
vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({ xe_may: "Xe máy" }),
  groupLabel: (map: Record<string, string>, code?: string | null) => (code ? map[code] ?? code : "—"),
}));
```

Đổi giá trị mock `vehicle_group: "car"` thành `vehicle_group: "xe_may"` và thêm assert `expect(await screen.findByText("Xe máy")).toBeInTheDocument();` (điều chỉnh theo cấu trúc test hiện có).

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/sessions/sessions-page.test.tsx`
Expected: FAIL — cột vẫn render code `xe_may`, không có "Xe máy".

- [ ] **Step 3: Sửa sessions-columns.tsx**

`sessions-columns.tsx` là mảng cột tĩnh. Chuyển sang factory nhận map, hoặc render cột nhóm bằng một component nhỏ đọc hook. Cách tối giản: đổi cell dùng component nội bộ:

Thêm đầu file:
```tsx
import { useVehicleGroupMap, groupLabel } from "@/lib/vehicle-groups";

function GroupCell({ code }: { code?: string | null }) {
  const map = useVehicleGroupMap();
  return <>{groupLabel(map, code)}</>;
}
```

Đổi cell cột `vehicle_group`:
```tsx
    cell: ({ row }) => <GroupCell code={row.original.vehicle_group} />,
```

- [ ] **Step 4: Sửa session-detail-page.tsx**

Thêm import và dùng lookup cho field "Nhóm xe":
```tsx
import { useVehicleGroupMap, groupLabel } from "@/lib/vehicle-groups";
```
Trong component, lấy map một lần: `const groupMap = useVehicleGroupMap();` và đổi:
```tsx
          <Field label="Nhóm xe">{groupLabel(groupMap, data.vehicle_group)}</Field>
```
Giữ nguyên field "Loại xe" (`data.vehicle_type`, là lớp ML thô).

- [ ] **Step 5: Sửa gate-capture.tsx chip nhóm**

Trong `src/frontend/src/features/gate/gate-capture.tsx`, thêm import lookup và đổi chip "Nhóm phí" sang display_name:
```tsx
import { useVehicleGroupMap, groupLabel } from "@/lib/vehicle-groups";
```
Trong `GateCaptureView`, thêm `const groupMap = useVehicleGroupMap();` và đổi:
```tsx
        <Chip label="Nhóm phí" value={capture?.vehicle_group ? groupLabel(groupMap, capture.vehicle_group) : null} />
```
Giữ chip "Loại xe" (`capture?.vehicle_type`) nguyên.

- [ ] **Step 6: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/sessions src/features/gate`
Expected: PASS. Điều chỉnh mock ở các test gate/sessions khác nếu chúng render nhóm và chưa mock `@/lib/vehicle-groups`.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/features/sessions/sessions-columns.tsx src/frontend/src/features/sessions/session-detail-page.tsx src/frontend/src/features/gate/gate-capture.tsx src/frontend/src/features/sessions/sessions-page.test.tsx
git commit -m "feat(ui): hien thi display_name nhom xe o sessions va gate chip"
```

---

## Self-Review

**Spec coverage:**
- vehicle_group table + seed: Task 1, 5. Backend CRUD + guards: Task 2, 3. price_rule validation: Task 4. group_for giữ constant: Task 1 (không đổi). Frontend hook + tab + display_name: Task 6, 7, 8. Migration + seed script: Task 5. Testing: mỗi task có test. Tiêu chí chấp nhận: thêm/sửa/xóa nhóm (Task 2, 3, 7), đặt giá mỗi nhóm (Task 7), display_name ở gate/sessions (Task 8), xóa referenced chặn (Task 3), price_rule code sai chặn (Task 4), staff không sửa được (Task 2, 3). Stats display_name: hiện stats chưa breakdown theo nhóm; áp dụng cùng hook khi làm mảng E.
- Không đổi `group_for`/`_MAP`: nhất quán toàn plan.

**Type consistency:** hook names `useListVehicleGroups`/`useCreateVehicleGroup`/`useUpdateVehicleGroup`/`useDeleteVehicleGroup` khớp handler names `list_vehicle_groups`/`create_vehicle_group`/`update_vehicle_group`/`delete_vehicle_group` (orval operationId = tên hàm). Mutation payload orval: create dùng `{ data }`, patch dùng `{ groupId, data }`, delete dùng `{ groupId }` (đường dẫn `/vehicle-groups/{group_id}` sinh param `groupId`). `VehicleGroupOut` fields khớp schema.

**Placeholder scan:** không có TBD/TODO; mọi step có code hoặc lệnh cụ thể.
