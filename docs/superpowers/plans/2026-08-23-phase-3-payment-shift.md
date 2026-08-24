# Phase 3: Payment and shift reconciliation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ghi nhận tiền đã thu cho phiên (phương thức, biên lai, hoàn và điều chỉnh), quản lý ca trực mở đóng, và đối soát cuối ca giữa tiền hệ thống ghi nhận và tiền đếm thực.

**Architecture:** thêm hai model `Payment` và `Shift`; service `shift` (mở, đóng, ca hiện tại, đối soát) và service `payment` (ghi nhận, tự gắn ca đang mở); hai router `shifts` và `payments`. Không đổi logic tính phí phase trước; thanh toán tách khỏi việc đóng phiên.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 sync, Alembic, pydantic v2, pytest.

## Global Constraints

Kế thừa index mục Global Constraints. Riêng phase này:
- Khóa chính số nguyên cục bộ; `Payment.session_id` FK tới `session.id`, `Payment.staff_id` và `Shift.staff_id` FK tới `users.id`.
- Tiền tính bằng VND, số nguyên. `kind` của payment: `payment`, `refund`, `adjustment`.
- Một nhân viên chỉ có một ca `open` tại một thời điểm; mở ca thứ hai trả HTTP 409.
- Đối soát cuối ca: `system_total = tổng payment kind=payment trừ tổng kind=refund trong ca`; `counted = closing_cash trừ opening_cash`; `difference = counted trừ system_total`.
- Thanh toán tự gắn ca đang mở của nhân viên; nếu không có ca mở thì `shift_id = None`.
- Bảo vệ mọi endpoint bằng `get_current_user` (staff hoặc admin).
- Không dùng ký tự gạch ngang trong văn xuôi tài liệu.
- Test trên SQLite in-memory qua fixture `db_session`, `client`, `staff_headers`.

---

### Task 1: Model `Payment` và `Shift`; migration; schema test

**Files:**
- Create: `src/backend/app/models/payment.py`
- Create: `src/backend/app/models/shift.py`
- Modify: `src/backend/app/models/__init__.py`
- Create: `src/backend/alembic/versions/b2c3d4e5f6a7_add_payment_shift.py`
- Test: `src/backend/tests/test_payment_shift_schema.py`

**Interfaces:**
- Produces: `Shift(id:int, staff_id:int, opened_at:datetime, closed_at:datetime|None, opening_cash:int, closing_cash:int|None, status:str)`; `Payment(id:int, session_id:int, amount:int, method:str, kind:str, note:str|None, shift_id:int|None, staff_id:int, paid_at:datetime, created_at:datetime)`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_payment_shift_schema.py`:

```python
def test_payment_and_shift_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401
    assert "payment" in Base.metadata.tables
    assert "shift" in Base.metadata.tables


def test_payment_columns():
    from app.models import Payment
    cols = Payment.__table__.columns.keys()
    for c in ("session_id", "amount", "method", "kind", "shift_id", "staff_id", "paid_at"):
        assert c in cols


def test_shift_columns():
    from app.models import Shift
    cols = Shift.__table__.columns.keys()
    for c in ("staff_id", "opened_at", "closed_at", "opening_cash", "closing_cash", "status"):
        assert c in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_payment_shift_schema.py -v`
Expected: FAIL (KeyError, chưa có bảng).

- [ ] **Step 3: Create the models**

Create `src/backend/app/models/shift.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Shift(Base):
    __tablename__ = "shift"

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opening_cash: Mapped[int] = mapped_column(Integer, default=0)
    closing_cash: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(8), index=True)  # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Create `src/backend/app/models/payment.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("session.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)          # VND
    method: Mapped[str] = mapped_column(String(16))       # cash | qr | ewallet
    kind: Mapped[str] = mapped_column(String(16), default="payment")  # payment | refund | adjustment
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shift.id"), nullable=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Register the models**

In `src/backend/app/models/__init__.py`, add imports and `__all__` entries for `Payment` and `Shift` (keep alphabetical grouping with the existing entries):

```python
from app.models.payment import Payment
from app.models.shift import Shift
```

Add `"Payment"` and `"Shift"` to the `__all__` list.

- [ ] **Step 5: Run schema test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_payment_shift_schema.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Write the migration**

Create `src/backend/alembic/versions/b2c3d4e5f6a7_add_payment_shift.py`:

```python
"""add payment and shift tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shift",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_cash", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("closing_cash", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shift_status", "shift", ["status"])
    op.create_table(
        "payment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("session.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="payment"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("shift_id", sa.Integer(), sa.ForeignKey("shift.id"), nullable=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payment_session_id", "payment", ["session_id"])


def downgrade() -> None:
    op.drop_table("payment")
    op.drop_table("shift")
```

- [ ] **Step 7: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS (không regression).

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/models/payment.py src/backend/app/models/shift.py src/backend/app/models/__init__.py src/backend/alembic/versions/b2c3d4e5f6a7_add_payment_shift.py src/backend/tests/test_payment_shift_schema.py
git commit -m "feat(backend): add payment and shift models"
```

---

### Task 2: Service ca trực và đối soát

**Files:**
- Create: `src/backend/app/services/shift.py`
- Test: `src/backend/tests/test_shift_service.py`

**Interfaces:**
- Consumes: `Shift`, `Payment` (Task 1); `now_utc` (`app/clock.py`).
- Produces: `current_open_shift(db, staff_id:int) -> Shift | None`; `open_shift(db, staff_id:int, opening_cash:int) -> Shift` (raise `ValueError` nếu đã có ca mở); `shift_system_total(db, shift_id:int) -> int`; `close_shift(db, shift:Shift, closing_cash:int) -> dict` với khóa `shift_id, system_total, counted, difference`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_shift_service.py`:

```python
import pytest


def _staff(db):
    from app.models import User
    u = User(username="s", password_hash="x", role="staff")
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_open_shift_rejects_second_open(db_session):
    from app.services.shift import open_shift
    u = _staff(db_session)
    open_shift(db_session, u.id, 100000)
    with pytest.raises(ValueError):
        open_shift(db_session, u.id, 50000)


def test_close_shift_reconciles(db_session):
    from app.models import Payment
    from app.clock import now_utc
    from app.services.shift import close_shift, open_shift, shift_system_total
    u = _staff(db_session)
    shift = open_shift(db_session, u.id, 100000)

    db_session.add(Payment(session_id=1, amount=20000, method="cash", kind="payment",
                           shift_id=shift.id, staff_id=u.id, paid_at=now_utc()))
    db_session.add(Payment(session_id=2, amount=5000, method="cash", kind="refund",
                           shift_id=shift.id, staff_id=u.id, paid_at=now_utc()))
    db_session.commit()

    assert shift_system_total(db_session, shift.id) == 15000
    # đếm được 120000, đầu ca 100000 nên counted 20000; hệ thống 15000; chênh 5000
    recon = close_shift(db_session, shift, closing_cash=120000)
    assert recon["system_total"] == 15000
    assert recon["counted"] == 20000
    assert recon["difference"] == 5000
    assert shift.status == "closed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_shift_service.py -v`
Expected: FAIL (ModuleNotFoundError: app.services.shift).

- [ ] **Step 3: Write the service**

Create `src/backend/app/services/shift.py`:

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import now_utc
from app.models import Payment, Shift


def current_open_shift(db: Session, staff_id: int) -> Shift | None:
    return db.scalars(
        select(Shift).where(Shift.staff_id == staff_id, Shift.status == "open")
    ).first()


def open_shift(db: Session, staff_id: int, opening_cash: int) -> Shift:
    if current_open_shift(db, staff_id) is not None:
        raise ValueError("đã có ca đang mở")
    shift = Shift(staff_id=staff_id, opened_at=now_utc(), opening_cash=opening_cash, status="open")
    db.add(shift); db.commit(); db.refresh(shift)
    return shift


def _sum(db: Session, shift_id: int, kind: str) -> int:
    return int(db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.shift_id == shift_id, Payment.kind == kind)
    ) or 0)


def shift_system_total(db: Session, shift_id: int) -> int:
    return _sum(db, shift_id, "payment") - _sum(db, shift_id, "refund")


def close_shift(db: Session, shift: Shift, closing_cash: int) -> dict:
    shift.closing_cash = closing_cash
    shift.closed_at = now_utc()
    shift.status = "closed"
    db.commit(); db.refresh(shift)
    system_total = shift_system_total(db, shift.id)
    counted = closing_cash - shift.opening_cash
    return {
        "shift_id": shift.id,
        "system_total": system_total,
        "counted": counted,
        "difference": counted - system_total,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_shift_service.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/backend/app/services/shift.py src/backend/tests/test_shift_service.py
git commit -m "feat(backend): add shift open/close/reconcile service"
```

---

### Task 3: Router ca trực

**Files:**
- Create: `src/backend/app/schemas/shift.py`
- Create: `src/backend/app/routers/shifts.py`
- Modify: `src/backend/app/main.py`
- Test: `src/backend/tests/test_shifts_api.py`

**Interfaces:**
- Consumes: shift service (Task 2); `get_current_user`, `User`.
- Produces: `POST /shifts/open {opening_cash}`, `POST /shifts/close {closing_cash}`, `GET /shifts/current`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_shifts_api.py`:

```python
def test_open_current_close_flow(client, staff_headers):
    o = client.post("/shifts/open", json={"opening_cash": 100000}, headers=staff_headers)
    assert o.status_code == 201
    cur = client.get("/shifts/current", headers=staff_headers).json()
    assert cur["status"] == "open" and cur["opening_cash"] == 100000
    # mở lần hai bị chặn
    assert client.post("/shifts/open", json={"opening_cash": 1}, headers=staff_headers).status_code == 409
    c = client.post("/shifts/close", json={"closing_cash": 100000}, headers=staff_headers)
    assert c.status_code == 200
    body = c.json()
    assert body["system_total"] == 0 and body["counted"] == 0 and body["difference"] == 0
    # không còn ca mở
    assert client.get("/shifts/current", headers=staff_headers).status_code == 404


def test_close_without_open_returns_404(client, staff_headers):
    assert client.post("/shifts/close", json={"closing_cash": 0}, headers=staff_headers).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_shifts_api.py -v`
Expected: FAIL (404 on `/shifts/open`).

- [ ] **Step 3: Write the schemas**

Create `src/backend/app/schemas/shift.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class ShiftOpenIn(BaseModel):
    opening_cash: int = 0


class ShiftCloseIn(BaseModel):
    closing_cash: int = 0


class ShiftOut(BaseModel):
    id: int
    staff_id: int
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: int
    closing_cash: int | None = None
    status: str
    model_config = {"from_attributes": True}


class ReconciliationOut(BaseModel):
    shift_id: int
    system_total: int
    counted: int
    difference: int
```

- [ ] **Step 4: Write the router**

Create `src/backend/app/routers/shifts.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.shift import ReconciliationOut, ShiftCloseIn, ShiftOpenIn, ShiftOut
from app.services.shift import close_shift, current_open_shift, open_shift

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.post("/open", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def open_current(body: ShiftOpenIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return open_shift(db, user.id, body.opening_cash)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/current", response_model=ShiftOut)
def get_current(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    shift = current_open_shift(db, user.id)
    if shift is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không có ca đang mở")
    return shift


@router.post("/close", response_model=ReconciliationOut)
def close_current(body: ShiftCloseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    shift = current_open_shift(db, user.id)
    if shift is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không có ca đang mở")
    return close_shift(db, shift, body.closing_cash)
```

- [ ] **Step 5: Register the router**

In `src/backend/app/main.py`, add `shifts` to the routers import line and add `app.include_router(shifts.router)` next to the other include calls.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_shifts_api.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/schemas/shift.py src/backend/app/routers/shifts.py src/backend/app/main.py src/backend/tests/test_shifts_api.py
git commit -m "feat(backend): add shift open/current/close endpoints"
```

---

### Task 4: Service và router thanh toán

**Files:**
- Create: `src/backend/app/services/payment.py`
- Create: `src/backend/app/schemas/payment.py`
- Create: `src/backend/app/routers/payments.py`
- Modify: `src/backend/app/main.py`
- Test: `src/backend/tests/test_payments_api.py`

**Interfaces:**
- Consumes: `Payment` (Task 1); `current_open_shift` (Task 2); `now_utc`; `get_current_user`, `User`; `ParkingSession` để kiểm tồn tại phiên.
- Produces: `record_payment(db, *, session_id:int, amount:int, method:str, staff_id:int, kind:str="payment", note:str|None=None) -> Payment`; `POST /payments {session_id, amount, method, kind?, note?}`; `GET /payments?session_id=`.

- [ ] **Step 1: Write the failing test**

Create `src/backend/tests/test_payments_api.py`:

```python
def _completed_session(db):
    from app.clock import now_utc
    from app.models import ParkingSession
    s = ParkingSession(plate_hash="h", plate_ciphertext="x", vehicle_group="o_to_con",
                       status="completed", exit_time=now_utc(), fee_amount=20000)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_record_payment_links_open_shift(client, staff_headers, db_session):
    client.post("/shifts/open", json={"opening_cash": 0}, headers=staff_headers)
    s = _completed_session(db_session)
    r = client.post("/payments", json={"session_id": s.id, "amount": 20000, "method": "cash"}, headers=staff_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["amount"] == 20000 and body["shift_id"] is not None
    listed = client.get(f"/payments?session_id={s.id}", headers=staff_headers).json()
    assert len(listed) == 1


def test_payment_for_missing_session_404(client, staff_headers):
    assert client.post("/payments", json={"session_id": 9999, "amount": 1, "method": "cash"}, headers=staff_headers).status_code == 404


def test_payment_without_open_shift_has_null_shift(client, staff_headers, db_session):
    s = _completed_session(db_session)
    body = client.post("/payments", json={"session_id": s.id, "amount": 20000, "method": "qr"}, headers=staff_headers).json()
    assert body["shift_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_payments_api.py -v`
Expected: FAIL (404 on `/payments`).

- [ ] **Step 3: Write the service**

Create `src/backend/app/services/payment.py`:

```python
from sqlalchemy.orm import Session

from app.clock import now_utc
from app.models import Payment
from app.services.shift import current_open_shift


def record_payment(
    db: Session, *, session_id: int, amount: int, method: str,
    staff_id: int, kind: str = "payment", note: str | None = None,
) -> Payment:
    shift = current_open_shift(db, staff_id)
    payment = Payment(
        session_id=session_id, amount=amount, method=method, kind=kind, note=note,
        shift_id=shift.id if shift else None, staff_id=staff_id, paid_at=now_utc(),
    )
    db.add(payment); db.commit(); db.refresh(payment)
    return payment
```

- [ ] **Step 4: Write the schemas**

Create `src/backend/app/schemas/payment.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class PaymentIn(BaseModel):
    session_id: int
    amount: int
    method: str          # cash | qr | ewallet
    kind: str = "payment"  # payment | refund | adjustment
    note: str | None = None


class PaymentOut(BaseModel):
    id: int
    session_id: int
    amount: int
    method: str
    kind: str
    note: str | None = None
    shift_id: int | None = None
    staff_id: int
    paid_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Write the router**

Create `src/backend/app/routers/payments.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import ParkingSession, Payment, User
from app.schemas.payment import PaymentIn, PaymentOut
from app.services.payment import record_payment

router = APIRouter(tags=["payments"])


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.get(ParkingSession, body.session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy phiên")
    return record_payment(
        db, session_id=body.session_id, amount=body.amount, method=body.method,
        staff_id=user.id, kind=body.kind, note=body.note,
    )


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(
        select(Payment).where(Payment.session_id == session_id).order_by(Payment.id)
    ).all())
```

- [ ] **Step 6: Register the router**

In `src/backend/app/main.py`, add `payments` to the routers import line and add `app.include_router(payments.router)`.

- [ ] **Step 7: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_payments_api.py -v`
Expected: PASS (3 tests).

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/services/payment.py src/backend/app/schemas/payment.py src/backend/app/routers/payments.py src/backend/app/main.py src/backend/tests/test_payments_api.py
git commit -m "feat(backend): add payment recording endpoints"
```

---

### Task 5: Test nghiệm thu phase và chạy toàn suite

**Files:**
- Test: `src/backend/tests/test_phase3_payment_shift_acceptance.py`

**Interfaces:**
- Consumes: mọi thứ Task 1 tới 4.

- [ ] **Step 1: Write the acceptance test**

Create `src/backend/tests/test_phase3_payment_shift_acceptance.py`:

```python
def test_shift_with_payments_reconciles_end_to_end(client, staff_headers, db_session):
    from app.clock import now_utc
    from app.models import ParkingSession

    client.post("/shifts/open", json={"opening_cash": 100000}, headers=staff_headers)

    # hai phiên hoàn tất, thu tiền mặt
    total = 0
    for fee in (20000, 15000):
        s = ParkingSession(plate_hash=f"h{fee}", plate_ciphertext="x", vehicle_group="o_to_con",
                           status="completed", exit_time=now_utc(), fee_amount=fee)
        db_session.add(s); db_session.commit(); db_session.refresh(s)
        client.post("/payments", json={"session_id": s.id, "amount": fee, "method": "cash"}, headers=staff_headers)
        total += fee

    # đếm khớp đúng: đầu 100000 cộng 35000
    recon = client.post("/shifts/close", json={"closing_cash": 100000 + total}, headers=staff_headers).json()
    assert recon["system_total"] == total
    assert recon["counted"] == total
    assert recon["difference"] == 0
```

- [ ] **Step 2: Run the acceptance test**

Run: `cd src/backend && python -m pytest tests/test_phase3_payment_shift_acceptance.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Run the full suite**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS toàn bộ.

- [ ] **Step 4: Commit**

```bash
git add src/backend/tests/test_phase3_payment_shift_acceptance.py
git commit -m "test(backend): phase 3 payment and shift reconciliation acceptance"
```

---

## Self-Review

**Spec coverage (spec kiến trúc mục 6.4, 6.6; frontend v2 mục 5.6, 5.7):** ghi nhận thanh toán (Task 4), phương thức và hoàn và điều chỉnh qua `kind` (Task 4), ca mở đóng (Task 3), đối soát cuối ca (Task 2, 3). Báo cáo theo ca và nhân viên cơ bản có từ `shift_system_total`; báo cáo chi tiết theo nhân viên để phase báo cáo mở rộng, không phải gap.

**Placeholder scan:** không có TBD; mọi bước có code thật.

**Type consistency:** `record_payment(...)`, `current_open_shift`, `close_shift(...) -> dict{shift_id, system_total, counted, difference}` khớp giữa service (Task 2, 4), router (Task 3, 4), và test (Task 2, 5). Tên bảng `payment`, `shift`, `session`, `users` khớp model và migration.
