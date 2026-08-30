# Mảng D — Quản lý phiên: lọc mở rộng + chi tiết đầy đủ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mở rộng bộ lọc danh sách phiên (nhóm xe, khoảng giờ vào, match_flag), làm giàu response danh sách và chi tiết (loại xe, nhân viên, phương thức thanh toán, lịch sử thanh toán, bãi/khu, snapshot giá), và dọn hai backlog liên quan (role-guard redirect, positive assert display_name ở detail).

**Architecture:** Backend giữ nguyên schema (không migration); chỉ thêm query param, schema response mới (`SessionListItem`, `PaymentBrief`), và join đọc theo lô để tránh N+1. Biển vẫn khớp `plate_hash` tuyệt đối, không partial search. Frontend regen client rồi thêm thanh lọc, cột bảng, và các khối chi tiết.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (`select`/`func`), Pydantic v2; React + TanStack Table, orval codegen, Vitest + Testing Library.

## Global Constraints

- Không partial plate search; không đổi schema/migration; không sửa `SessionOut` của luồng cổng.
- Không dùng dấu gạch ngang làm dấu câu trong văn bản tiếng Việt (giữ trong code/path/mã kỹ thuật).
- Backend đổi endpoint thì phải regen client: `.venv/bin/python scripts/export_openapi.py` tại `src/backend` rồi `npm run gen:api` tại `src/frontend`.
- Test backend: `.venv/bin/pytest` tại `src/backend`. Test frontend: `npm run test` và `npm run build` tại `src/frontend`.
- `src/api/generated/` và `openapi.json` bị gitignore (orval clean); mỗi lần đổi endpoint phải chạy `gen:api` trước khi build. Không commit thư mục generated.
- RBAC chốt ở guard backend; frontend chỉ ẩn/hiện. Hiển thị nhóm xe qua `useVehicleGroupMap`/`groupLabel`; phân biệt `vehicle_type` (lớp ML) với `vehicle_group` (nhóm tính tiền).
- Commit theo từng task (subagent-driven-development; implementer stage, controller commit).

---

## File Structure

**Backend**
- `src/backend/app/routers/sessions.py` — thêm filter vào `list_sessions`; helper `_list_items`; làm giàu `session_detail`.
- `src/backend/app/schemas/session.py` — thêm `SessionListItem`, `PaymentBrief`; mở rộng `SessionDetail`; đổi `SessionListResponse.items`.
- `src/backend/tests/test_session_query.py` — test filter + list item + detail.

**Frontend**
- `src/frontend/src/features/sessions/sessions-page.tsx` — thanh lọc.
- `src/frontend/src/features/sessions/sessions-columns.tsx` — 3 cột mới.
- `src/frontend/src/features/sessions/session-detail-page.tsx` — nhân viên/bãi/khu, bảng thanh toán, snapshot.
- `src/frontend/src/app/role-guard.tsx` — tách nhánh role null.
- Test tương ứng: `sessions-page.test.tsx`, `session-detail-page.test.tsx`, `app/role-guard.test.tsx`.

---

## Task 1: Backend — filter mở rộng cho `list_sessions`

**Files:**
- Modify: `src/backend/app/routers/sessions.py` (imports dòng 1-3; `list_sessions` dòng 294-310)
- Test: `src/backend/tests/test_session_query.py`

**Interfaces:**
- Consumes: `ParkingSession` model (đã có `vehicle_group`, `entry_time`, `match_flag`).
- Produces: `GET /sessions` chấp nhận thêm `vehicle_group`, `entry_from`, `entry_to`, `match_flag`; `total` đếm trên query đã lọc. Items vẫn `SessionOut` (đổi ở Task 2).

- [ ] **Step 1: Viết test filter (fail trước)**

Thêm vào cuối `src/backend/tests/test_session_query.py`:

```python
from datetime import datetime, timezone


def _mk(db, plate_text, *, status="in_lot", group="o_to_con", entry=None, match_flag=None):
    s = ParkingSession(
        plate_hash=plate.plate_hash(plate_text),
        plate_ciphertext=crypto.encrypt_text(plate_text),
        vehicle_group=group, status=status, entry_time=entry, match_flag=match_flag,
    )
    db.add(s); db.commit(); db.refresh(s); return s


def test_list_filters_by_vehicle_group(client, db_session, staff_headers):
    _mk(db_session, "51F-111.11", group="xe_may")
    _mk(db_session, "51F-222.22", group="o_to_con")
    r = client.get("/sessions", params={"vehicle_group": "xe_may"}, headers=staff_headers)
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle_group"] == "xe_may"


def test_list_filters_by_entry_range(client, db_session, staff_headers):
    _mk(db_session, "51F-111.11", entry=datetime(2026, 8, 20, 8, tzinfo=timezone.utc))
    _mk(db_session, "51F-222.22", entry=datetime(2026, 8, 25, 8, tzinfo=timezone.utc))
    r = client.get("/sessions", params={
        "entry_from": "2026-08-24T00:00:00Z", "entry_to": "2026-08-26T00:00:00Z",
    }, headers=staff_headers)
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["plate_text"] == "51F-222.22"


def test_list_filters_by_match_flag(client, db_session, staff_headers):
    _mk(db_session, "51F-111.11", match_flag="manual")
    _mk(db_session, "51F-222.22", match_flag="exact")
    r = client.get("/sessions", params={"match_flag": "manual"}, headers=staff_headers)
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["match_flag"] == "manual"
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `.venv/bin/pytest tests/test_session_query.py -v` (tại `src/backend`)
Expected: 3 test mới FAIL (filter chưa có nên trả cả 2 dòng, `total == 2`).

- [ ] **Step 3: Thêm import datetime + func**

Trong `src/backend/app/routers/sessions.py`, đổi dòng 1 và dòng 4:

```python
from datetime import datetime, timedelta
```

```python
from sqlalchemy import func, select
```

- [ ] **Step 4: Thêm filter vào `list_sessions`**

Thay thân `list_sessions` (dòng 294-310) bằng:

```python
@router.get("", response_model=SessionListResponse)
def list_sessions(
    plate: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    vehicle_group: str | None = Query(None),
    entry_from: datetime | None = Query(None),
    entry_to: datetime | None = Query(None),
    match_flag: str | None = Query(None),
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
    if vehicle_group:
        stmt = stmt.where(ParkingSession.vehicle_group == vehicle_group)
    if entry_from is not None:
        stmt = stmt.where(ParkingSession.entry_time >= entry_from)
    if entry_to is not None:
        stmt = stmt.where(ParkingSession.entry_time < entry_to)
    if match_flag:
        stmt = stmt.where(ParkingSession.match_flag == match_flag)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(ParkingSession.id.desc()).limit(limit).offset(offset)).all()
    return SessionListResponse(total=total, items=[_session_out(s) for s in rows])
```

- [ ] **Step 5: Chạy test, xác nhận pass**

Run: `.venv/bin/pytest tests/test_session_query.py -v`
Expected: PASS toàn bộ (kể cả 2 test cũ `test_list_filters_by_plate`, `test_list_filters_by_status_and_paginates`).

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/routers/sessions.py src/backend/tests/test_session_query.py
git commit -m "feat(sessions): filter list by vehicle_group, entry range, match_flag"
```

---

## Task 2: Backend — `SessionListItem` + enrichment danh sách

**Files:**
- Modify: `src/backend/app/schemas/session.py` (thêm `SessionListItem`; đổi `SessionListResponse`)
- Modify: `src/backend/app/routers/sessions.py` (import `Payment`, `SessionListItem`; helper `_list_items`; `list_sessions` return)
- Test: `src/backend/tests/test_session_query.py`

**Interfaces:**
- Consumes: `list_sessions` từ Task 1.
- Produces: `SessionListItem(SessionOut)` với `vehicle_type: str | None`, `closed_by_name: str | None`, `payment_method: str | None`. `_list_items(db, rows) -> list[SessionListItem]`.

- [ ] **Step 1: Viết test list item (fail trước)**

Thêm vào `src/backend/tests/test_session_query.py`:

```python
def test_list_item_has_type_staff_method(client, db_session, staff_headers, make_user):
    from app.clock import now_utc
    from app.models import Payment
    closer = make_user(username="closer", role="staff")
    s = ParkingSession(
        plate_hash=plate.plate_hash("51F-900.00"),
        plate_ciphertext=crypto.encrypt_text("51F-900.00"),
        vehicle_group="o_to_con", vehicle_type="o_to_con",
        status="completed", closed_by=closer.id,
    )
    db_session.add(s); db_session.commit(); db_session.refresh(s)
    db_session.add(Payment(session_id=s.id, amount=5000, method="cash", kind="payment",
                           staff_id=closer.id, paid_at=now_utc()))
    db_session.commit()
    r = client.get("/sessions", headers=staff_headers)
    item = next(i for i in r.json()["items"] if i["id"] == s.id)
    assert item["vehicle_type"] == "o_to_con"
    assert item["closed_by_name"] == "closer"
    assert item["payment_method"] == "cash"
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `.venv/bin/pytest tests/test_session_query.py::test_list_item_has_type_staff_method -v`
Expected: FAIL KeyError/None (field chưa tồn tại trong response).

- [ ] **Step 3: Thêm schema `SessionListItem`**

Trong `src/backend/app/schemas/session.py`, sau `class SessionDetail` (dòng 71-74) thêm và đổi `SessionListResponse`:

```python
class SessionListItem(SessionOut):
    vehicle_type: str | None = None
    closed_by_name: str | None = None
    payment_method: str | None = None


class SessionListResponse(BaseModel):
    total: int
    items: list[SessionListItem]
```

Xóa định nghĩa `SessionListResponse` cũ (dòng 77-79) để không trùng.

- [ ] **Step 4: Import + helper + return trong router**

Trong `src/backend/app/routers/sessions.py`, thêm `Payment` vào import model (dòng 11):

```python
from app.models import ImageAsset, ParkingSession, Payment, PlateReading, User, Zone
```

Thêm `SessionListItem` vào import schema (dòng 12-15):

```python
from app.schemas.session import (
    EntryRequest, ExitRequest, ExitResult, LostTicketRequest, ManualRequest, ReadingBrief, ResolveRequest,
    SessionBrief, SessionDetail, SessionListItem, SessionListResponse, SessionOut,
)
```

Thêm helper ngay trước `list_sessions`:

```python
def _list_items(db: Session, rows: list[ParkingSession]) -> list[SessionListItem]:
    staff_ids = {s.closed_by for s in rows if s.closed_by}
    names: dict[int, str] = {}
    if staff_ids:
        names = dict(db.execute(select(User.id, User.username).where(User.id.in_(staff_ids))).all())
    session_ids = [s.id for s in rows]
    methods: dict[int, str] = {}
    if session_ids:
        pay_rows = db.execute(
            select(Payment.session_id, Payment.method)
            .where(Payment.session_id.in_(session_ids), Payment.kind == "payment")
            .order_by(Payment.paid_at)
        ).all()
        for sid, method in pay_rows:
            methods[sid] = method  # order_by paid_at asc: bản ghi cuối = mới nhất
    items: list[SessionListItem] = []
    for s in rows:
        base = _session_out(s)
        items.append(SessionListItem(
            **base.model_dump(),
            vehicle_type=s.vehicle_type,
            closed_by_name=names.get(s.closed_by),
            payment_method=methods.get(s.id),
        ))
    return items
```

Đổi dòng return của `list_sessions`:

```python
    rows = list(db.scalars(stmt.order_by(ParkingSession.id.desc()).limit(limit).offset(offset)).all())
    return SessionListResponse(total=total, items=_list_items(db, rows))
```

- [ ] **Step 5: Chạy test, xác nhận pass**

Run: `.venv/bin/pytest tests/test_session_query.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/schemas/session.py src/backend/app/routers/sessions.py src/backend/tests/test_session_query.py
git commit -m "feat(sessions): enrich list rows with vehicle_type, closed_by_name, payment_method"
```

---

## Task 3: Backend — làm giàu `session_detail`

**Files:**
- Modify: `src/backend/app/schemas/session.py` (thêm `PaymentBrief`; mở rộng `SessionDetail`)
- Modify: `src/backend/app/routers/sessions.py` (import `ParkingLot`, `PaymentBrief`; `session_detail`)
- Test: `src/backend/tests/test_session_query.py`

**Interfaces:**
- Consumes: `session_detail`, `_reading_brief` (đã có).
- Produces: `SessionDetail` thêm `created_by_name`, `closed_by_name`, `lot_name`, `zone_name`, `fee_rule_snapshot: dict | None`, `payments: list[PaymentBrief]`. `PaymentBrief` gồm `id, amount, method, kind, note, staff_name, paid_at`.

- [ ] **Step 1: Viết test detail (fail trước)**

Thêm vào `src/backend/tests/test_session_query.py`:

```python
def test_detail_returns_payments_names_snapshot(client, db_session, staff_headers, make_user):
    from app.clock import now_utc
    from app.models import Payment
    creator = make_user(username="creator", role="staff")
    closer = make_user(username="closer2", role="staff")
    s = ParkingSession(
        plate_hash=plate.plate_hash("51F-700.00"),
        plate_ciphertext=crypto.encrypt_text("51F-700.00"),
        vehicle_group="o_to_con", status="completed",
        created_by=creator.id, closed_by=closer.id,
        fee_rule_snapshot={"mode": "flat", "unit_price": 5000},
    )
    db_session.add(s); db_session.commit(); db_session.refresh(s)
    db_session.add(Payment(session_id=s.id, amount=5000, method="qr", kind="payment",
                           staff_id=closer.id, paid_at=now_utc()))
    db_session.commit()
    r = client.get(f"/sessions/{s.id}", headers=staff_headers)
    body = r.json()
    assert body["created_by_name"] == "creator"
    assert body["closed_by_name"] == "closer2"
    assert body["fee_rule_snapshot"]["unit_price"] == 5000
    assert len(body["payments"]) == 1
    assert body["payments"][0]["method"] == "qr"
    assert body["payments"][0]["staff_name"] == "closer2"
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `.venv/bin/pytest tests/test_session_query.py::test_detail_returns_payments_names_snapshot -v`
Expected: FAIL (field mới chưa có).

- [ ] **Step 3: Thêm `PaymentBrief` + mở rộng `SessionDetail`**

Trong `src/backend/app/schemas/session.py`, thay `class SessionDetail(SessionOut)` (dòng 71-74) bằng:

```python
class PaymentBrief(BaseModel):
    id: int
    amount: int
    method: str
    kind: str
    note: str | None = None
    staff_name: str | None = None
    paid_at: datetime


class SessionDetail(SessionOut):
    vehicle_type: str | None = None
    entry_reading: ReadingBrief | None = None
    exit_reading: ReadingBrief | None = None
    created_by_name: str | None = None
    closed_by_name: str | None = None
    lot_name: str | None = None
    zone_name: str | None = None
    fee_rule_snapshot: dict | None = None
    payments: list[PaymentBrief] = []
```

- [ ] **Step 4: Cập nhật router `session_detail`**

Trong `src/backend/app/routers/sessions.py`, thêm `ParkingLot` vào import model (dòng 11):

```python
from app.models import ImageAsset, ParkingLot, ParkingSession, Payment, PlateReading, User, Zone
```

Thêm `PaymentBrief` vào import schema:

```python
from app.schemas.session import (
    EntryRequest, ExitRequest, ExitResult, LostTicketRequest, ManualRequest, PaymentBrief, ReadingBrief,
    ResolveRequest, SessionBrief, SessionDetail, SessionListItem, SessionListResponse, SessionOut,
)
```

Thay thân `session_detail` (dòng 326-337) bằng:

```python
@router.get("/{session_id}", response_model=SessionDetail)
def session_detail(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionDetail:
    s = db.get(ParkingSession, session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    base = _session_out(s)
    pay_rows = list(db.scalars(
        select(Payment).where(Payment.session_id == s.id).order_by(Payment.paid_at)
    ).all())
    staff_ids = {p.staff_id for p in pay_rows}
    for uid in (s.created_by, s.closed_by):
        if uid:
            staff_ids.add(uid)
    names: dict[int, str] = {}
    if staff_ids:
        names = dict(db.execute(select(User.id, User.username).where(User.id.in_(staff_ids))).all())
    payments = [
        PaymentBrief(
            id=p.id, amount=p.amount, method=p.method, kind=p.kind, note=p.note,
            staff_name=names.get(p.staff_id), paid_at=p.paid_at,
        )
        for p in pay_rows
    ]
    lot_name = None
    if s.lot_id:
        lot = db.get(ParkingLot, s.lot_id)
        lot_name = lot.name if lot else None
    zone_name = None
    if s.zone_id:
        zone = db.get(Zone, s.zone_id)
        zone_name = zone.name if zone else None
    return SessionDetail(
        **base.model_dump(),
        vehicle_type=s.vehicle_type,
        entry_reading=_reading_brief(db, s.entry_reading_id),
        exit_reading=_reading_brief(db, s.exit_reading_id),
        created_by_name=names.get(s.created_by),
        closed_by_name=names.get(s.closed_by),
        lot_name=lot_name,
        zone_name=zone_name,
        fee_rule_snapshot=s.fee_rule_snapshot,
        payments=payments,
    )
```

- [ ] **Step 5: Chạy test, xác nhận pass**

Run: `.venv/bin/pytest tests/test_session_query.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 6: Chạy full backend suite (không hồi quy)**

Run: `.venv/bin/pytest` (tại `src/backend`)
Expected: PASS toàn bộ (session_detail dùng chung schema; kiểm tra không vỡ test khác).

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/schemas/session.py src/backend/app/routers/sessions.py src/backend/tests/test_session_query.py
git commit -m "feat(sessions): detail returns payments, staff names, lot/zone, fee snapshot"
```

---

## Task 4: Frontend — regen client + thanh lọc `sessions-page`

**Files:**
- Regen: `src/frontend/src/api/generated/` (qua `gen:api`, gitignored)
- Modify: `src/frontend/src/features/sessions/sessions-page.tsx`
- Test: `src/frontend/src/features/sessions/sessions-page.test.tsx`

**Interfaces:**
- Consumes: `ListSessionsParams` (regen: thêm `vehicle_group`, `entry_from`, `entry_to`, `match_flag`), `useVehicleGroupMap`.
- Produces: thanh lọc gọi API với các param mới; reset offset khi đổi filter. Control có `aria-label`: "Lọc nhóm xe", "Lọc cách khớp", "Giờ vào từ", "Giờ vào đến".

- [ ] **Step 1: Regen API client**

Run (tại `src/backend`): `.venv/bin/python scripts/export_openapi.py`
Run (tại `src/frontend`): `npm run gen:api`
Expected: `src/frontend/src/api/generated/model/listSessionsParams.ts` chứa `vehicle_group`, `entry_from`, `entry_to`, `match_flag`; model có `SessionListItem`, `PaymentBrief`, `SessionDetail` các field mới.

Verify: `grep -R "entry_from" src/frontend/src/api/generated/model` cho ra kết quả.

- [ ] **Step 2: Viết test thanh lọc (fail trước)**

Sửa `src/frontend/src/features/sessions/sessions-page.test.tsx`. Đổi test bảng display_name cũ (dòng 41-48) để tránh trùng chuỗi với option dropdown, và thêm test control:

```tsx
test("renders vehicle group display_name in sessions table", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  expect(screen.getAllByText("Xe máy").length).toBeGreaterThan(0);
});

test("renders filter controls", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  expect(screen.getByLabelText("Lọc nhóm xe")).toBeInTheDocument();
  expect(screen.getByLabelText("Lọc cách khớp")).toBeInTheDocument();
  expect(screen.getByLabelText("Giờ vào từ")).toBeInTheDocument();
  expect(screen.getByLabelText("Giờ vào đến")).toBeInTheDocument();
});
```

- [ ] **Step 3: Chạy test, xác nhận fail**

Run: `npm run test -- sessions-page` (tại `src/frontend`)
Expected: `renders filter controls` FAIL (chưa có control).

- [ ] **Step 4: Thêm thanh lọc vào `sessions-page.tsx`**

Thay toàn bộ file bằng:

```tsx
import { useMemo, useState } from "react";
import { useListSessions } from "@/api/generated/sessions/sessions";
import type { ListSessionsParams } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { sessionColumns } from "./sessions-columns";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SurfaceCard } from "@/components/surface-card";
import { useVehicleGroupMap } from "@/lib/vehicle-groups";

const PAGE = 20;
const STATUSES = ["", "in_lot", "completed", "disputed", "pending_manual"];
const MATCH_FLAGS = ["", "exact", "auto_corrected", "manual", "lost_ticket"];
const SELECT_CLASS =
  "h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm";

export function SessionsPage() {
  const [plate, setPlate] = useState("");
  const [status, setStatus] = useState("");
  const [group, setGroup] = useState("");
  const [matchFlag, setMatchFlag] = useState("");
  const [entryFrom, setEntryFrom] = useState("");
  const [entryTo, setEntryTo] = useState("");
  const [offset, setOffset] = useState(0);
  const groupMap = useVehicleGroupMap();

  const params: ListSessionsParams = useMemo(
    () => ({
      plate: plate || null,
      status: status || null,
      vehicle_group: group || null,
      match_flag: matchFlag || null,
      entry_from: entryFrom ? new Date(entryFrom).toISOString() : null,
      entry_to: entryTo ? new Date(entryTo).toISOString() : null,
      limit: PAGE,
      offset,
    }),
    [plate, status, group, matchFlag, entryFrom, entryTo, offset],
  );
  const { data, isLoading } = useListSessions(params);
  const total = data?.total ?? 0;

  const reset = () => setOffset(0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          placeholder="Tra biển số"
          value={plate}
          onChange={(e) => {
            setPlate(e.target.value);
            reset();
          }}
          aria-label="Tra biển số"
        />
        <select
          className={SELECT_CLASS}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            reset();
          }}
          aria-label="Lọc trạng thái"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s || "Tất cả trạng thái"}
            </option>
          ))}
        </select>
        <select
          className={SELECT_CLASS}
          value={group}
          onChange={(e) => {
            setGroup(e.target.value);
            reset();
          }}
          aria-label="Lọc nhóm xe"
        >
          <option value="">Tất cả nhóm xe</option>
          {Object.entries(groupMap).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
        <select
          className={SELECT_CLASS}
          value={matchFlag}
          onChange={(e) => {
            setMatchFlag(e.target.value);
            reset();
          }}
          aria-label="Lọc cách khớp"
        >
          {MATCH_FLAGS.map((m) => (
            <option key={m} value={m}>
              {m || "Tất cả cách khớp"}
            </option>
          ))}
        </select>
        <input
          type="date"
          className={SELECT_CLASS}
          value={entryFrom}
          onChange={(e) => {
            setEntryFrom(e.target.value);
            reset();
          }}
          aria-label="Giờ vào từ"
        />
        <input
          type="date"
          className={SELECT_CLASS}
          value={entryTo}
          onChange={(e) => {
            setEntryTo(e.target.value);
            reset();
          }}
          aria-label="Giờ vào đến"
        />
      </div>
      <SurfaceCard variant="white">
        <DataTable
          columns={sessionColumns}
          data={data?.items ?? []}
          loading={isLoading}
          empty="Chưa có phiên"
        />
      </SurfaceCard>
      <div className="flex items-center justify-end gap-2 text-sm">
        <Button
          variant="outline"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE))}
        >
          Trước
        </Button>
        <span className="tnum text-muted">
          {offset + 1}–{Math.min(offset + PAGE, total)} / {total}
        </span>
        <Button
          variant="outline"
          disabled={offset + PAGE >= total}
          onClick={() => setOffset((o) => o + PAGE)}
        >
          Sau
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Chạy test, xác nhận pass**

Run: `npm run test -- sessions-page`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/features/sessions/sessions-page.tsx src/frontend/src/features/sessions/sessions-page.test.tsx
git commit -m "feat(sessions): filter bar for group, entry range, match_flag"
```

---

## Task 5: Frontend — 3 cột mới trong `sessions-columns`

**Files:**
- Modify: `src/frontend/src/features/sessions/sessions-columns.tsx`
- Test: `src/frontend/src/features/sessions/sessions-page.test.tsx`

**Interfaces:**
- Consumes: `SessionListItem` (regen, có `vehicle_type`, `closed_by_name`, `payment_method`).
- Produces: bảng thêm cột "Loại xe", "Nhân viên", "Phương thức".

- [ ] **Step 1: Cập nhật mock + test cột (fail trước)**

Trong `src/frontend/src/features/sessions/sessions-page.test.tsx`, thêm 3 field vào object row của mock `useListSessions` (khối `vi.mock("@/api/generated/sessions/sessions", ...)`):

```tsx
          vehicle_type: "o_to_con",
          closed_by_name: "closer",
          payment_method: "cash",
```

Thêm test:

```tsx
test("renders vehicle_type, staff, payment method columns", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("o_to_con")).toBeInTheDocument();
  expect(screen.getByText("closer")).toBeInTheDocument();
  expect(screen.getByText("cash")).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `npm run test -- sessions-page`
Expected: `renders vehicle_type, staff, payment method columns` FAIL.

- [ ] **Step 3: Thêm cột vào `sessions-columns.tsx`**

Đổi import type (dòng 3) và type mảng (dòng 13), thêm 3 cột trước cột "Trạng thái":

```tsx
import type { SessionListItem } from "@/api/generated/model";
```

```tsx
export const sessionColumns: ColumnDef<SessionListItem, unknown>[] = [
```

Thêm sau cột "Phí" (giữ nguyên các cột hiện có), trước cột "Trạng thái":

```tsx
  { header: "Loại xe", cell: ({ row }) => row.original.vehicle_type ?? "—" },
  { header: "Nhân viên", cell: ({ row }) => row.original.closed_by_name ?? "—" },
  { header: "Phương thức", cell: ({ row }) => row.original.payment_method ?? "—" },
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `npm run test -- sessions-page`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/sessions/sessions-columns.tsx src/frontend/src/features/sessions/sessions-page.test.tsx
git commit -m "feat(sessions): add vehicle_type, staff, payment method columns"
```

---

## Task 6: Frontend — chi tiết phiên đầy đủ + positive assert display_name

**Files:**
- Modify: `src/frontend/src/features/sessions/session-detail-page.tsx`
- Test: `src/frontend/src/features/sessions/session-detail-page.test.tsx`

**Interfaces:**
- Consumes: `SessionDetail` (regen: `created_by_name`, `closed_by_name`, `lot_name`, `zone_name`, `fee_rule_snapshot`, `payments`).
- Produces: fields nhân viên/bãi/khu; bảng thanh toán; khối snapshot; hiển thị display_name nhóm xe (đã có, thêm assert dương).

- [ ] **Step 1: Cập nhật mock + test (fail trước)**

Trong `src/frontend/src/features/sessions/session-detail-page.test.tsx`, đổi `vehicle_group` mock từ `"car"` sang `"xe_may"`, và thêm các field mới vào object `data`:

```tsx
      vehicle_group: "xe_may",
      created_by_name: "creator",
      closed_by_name: "closer2",
      lot_name: "Bãi A",
      zone_name: "Khu 1",
      fee_rule_snapshot: { mode: "flat", unit_price: 5000 },
      payments: [
        { id: 1, amount: 5000, method: "qr", kind: "payment", staff_name: "closer2", paid_at: "2026-08-23T09:00:00Z" },
      ],
```

Thêm test:

```tsx
test("shows staff, payments and vehicle group display_name", () => {
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText("Xe máy")).toBeInTheDocument();
  expect(screen.getByText("creator")).toBeInTheDocument();
  expect(screen.getByText("qr")).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `npm run test -- session-detail-page`
Expected: `shows staff, payments and vehicle group display_name` FAIL (chưa render creator/qr).

- [ ] **Step 3: Thêm fields + bảng thanh toán + snapshot**

Trong `src/frontend/src/features/sessions/session-detail-page.tsx`, thêm 4 `Field` vào `dl` (sau field "Cảnh báo", dòng 58):

```tsx
          <Field label="Nhân viên vào">{data.created_by_name ?? "—"}</Field>
          <Field label="Nhân viên ra">{data.closed_by_name ?? "—"}</Field>
          <Field label="Bãi">{data.lot_name ?? "—"}</Field>
          <Field label="Khu">{data.zone_name ?? "—"}</Field>
```

Thêm khối thanh toán + snapshot ngay sau lưới ảnh vào/ra (sau `</div>` đóng grid ảnh, trước đoạn ghi chú audit dòng 79):

```tsx
      <SurfaceCard variant="white" className="space-y-2">
        <p className="text-sm font-semibold">Thanh toán</p>
        {data.payments && data.payments.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted">
                <th className="py-1">Số tiền</th>
                <th>Phương thức</th>
                <th>Loại</th>
                <th>Nhân viên</th>
                <th>Giờ</th>
              </tr>
            </thead>
            <tbody>
              {data.payments.map((p) => (
                <tr key={p.id} className="tnum">
                  <td className="py-1">{formatVnd(p.amount)}</td>
                  <td>{p.method}</td>
                  <td>{p.kind}</td>
                  <td>{p.staff_name ?? "—"}</td>
                  <td>{formatDateTime(p.paid_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-muted">Chưa có thanh toán</p>
        )}
      </SurfaceCard>

      {data.fee_rule_snapshot && (
        <SurfaceCard variant="white" className="space-y-1">
          <p className="text-sm font-semibold">Cách tính phí</p>
          <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-3">
            {Object.entries(data.fee_rule_snapshot).map(([k, v]) => (
              <div key={k}>
                <dt className="text-[13px] text-muted">{k}</dt>
                <dd className="tnum">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </SurfaceCard>
      )}
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `npm run test -- session-detail-page`
Expected: PASS (cả test cũ "shows detail fields and retention notice").

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/sessions/session-detail-page.tsx src/frontend/src/features/sessions/session-detail-page.test.tsx
git commit -m "feat(sessions): detail shows staff, lot/zone, payments, fee snapshot"
```

---

## Task 7: Frontend — fix role-guard redirect khi role không hợp lệ

**Files:**
- Modify: `src/frontend/src/app/role-guard.tsx`
- Test: `src/frontend/src/app/role-guard.test.tsx`

**Interfaces:**
- Consumes: `getToken`, `getRole`, `isExpired`, `clearToken` từ `@/lib/auth`.
- Produces: `RequireRole` với `!role` (token role không hợp lệ) thì `clearToken()` + `Navigate /login`; role hợp lệ nhưng thiếu quyền thì `Navigate /gate`.

- [ ] **Step 1: Viết test nhánh role null (fail trước)**

Trong `src/frontend/src/app/role-guard.test.tsx`, thêm `getToken` vào import (dòng 4):

```tsx
import { saveToken, clearToken, getToken } from "@/lib/auth";
```

Thêm test:

```tsx
test("invalid role clears token and redirects to login", () => {
  clearToken();
  saveToken(jwt("admin")); // role cũ không hợp lệ
  render(tree("/config"));
  expect(screen.getByText("LOGIN")).toBeInTheDocument();
  expect(getToken()).toBeNull();
});
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `npm run test -- role-guard` (tại `src/frontend`)
Expected: FAIL (hiện redirect `/gate`, thấy "GATE" thay vì "LOGIN"; token còn).

- [ ] **Step 3: Tách nhánh trong `role-guard.tsx`**

Thay toàn bộ `src/frontend/src/app/role-guard.tsx` bằng:

```tsx
import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { getToken, getRole, isExpired, clearToken, type Role } from "@/lib/auth";

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const token = getToken();
  if (!token || isExpired()) return <Navigate to="/login" replace />;
  const role = getRole();
  if (!role) {
    clearToken();
    return <Navigate to="/login" replace />;
  }
  if (!roles.includes(role)) return <Navigate to="/gate" replace />;
  return <>{children}</>;
}
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `npm run test -- role-guard`
Expected: PASS toàn bộ (kể cả "staff blocked from config route -> gate" vẫn `/gate`).

- [ ] **Step 5: Chạy full frontend suite + build**

Run: `npm run test` rồi `npm run build` (tại `src/frontend`)
Expected: toàn bộ test PASS; build PASS (tsc clean).

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/app/role-guard.tsx src/frontend/src/app/role-guard.test.tsx
git commit -m "fix(auth): invalid role clears token and redirects to login, not gate"
```

---

## Self-Review

**Spec coverage:**
- §3.1 filter mở rộng → Task 1.
- §3.2 SessionListItem + §3.3 enrichment lô → Task 2.
- §3.4 detail làm giàu → Task 3.
- §4.1 thanh lọc → Task 4.
- §4.2 cột bảng → Task 5.
- §4.3 detail UI + §5.1 positive assert display_name (detail) → Task 6.
- §5.2 role-guard → Task 7.
- §5.1 gate/sessions-page display_name: đã có sẵn (`decision-panel.test.tsx:55`, `sessions-page.test.tsx:41`); không cần task mới. Chỉ detail thiếu, làm ở Task 6.

**Placeholder scan:** không có TBD/TODO; mọi step có code hoặc command thật.

**Type consistency:** `SessionListItem` (Task 2) dùng ở columns (Task 5) và list response; `PaymentBrief` (Task 3) dùng ở detail (Task 6); `_list_items` tên nhất quán; param `entry_from`/`entry_to`/`vehicle_group`/`match_flag` khớp giữa backend (Task 1) và frontend params (Task 4). `clearToken` (Task 7) có trong `@/lib/auth`.

**Non-goals giữ nguyên:** không partial search, không migration, không sửa `SessionOut` của luồng cổng (chỉ thêm `SessionListItem` kế thừa).
