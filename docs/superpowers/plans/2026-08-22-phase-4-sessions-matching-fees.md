# Phase 4: Session in/out, khớp biển, tính phí

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** vòng đời session đầy đủ: xác nhận vào tạo `in_lot`, xác nhận ra khớp biển (exact, tự nối khi duy nhất và `k <= 1`, gợi ý khi `k == 2` hoặc nhiều ứng viên, `disputed` khi không có), nhập tay hoàn toàn khi AI lỗi, sửa biển tay, xử lý dispute, và tính phí theo nhóm cộng mode.

**Architecture:** service khớp `find_match` thuần, nhận danh sách ứng viên đã giải mã và trả quyết định; service phí `compute_fee` thuần cộng `get_active_rule` đọc DB; router `sessions` và `readings` gọi service, ghi audit khi sửa biển. Thời gian dùng UTC naive qua helper `app.clock.now_utc()` (`datetime.now(timezone.utc)` bỏ tzinfo) cho nhất quán giữa SQLite test và Postgres, và tránh DeprecationWarning của `datetime.utcnow()` trên Python 3.12 trở lên. Tạo `app/clock.py` một lần, dùng lại cho `sessions.py` và job xóa Phase 5.

**Tech Stack:** FastAPI, SQLAlchemy, pytest.

## Global Constraints

Xem `2026-08-22-dashboard-mvp-plan-index.md`. Riêng phase này: khớp exact rồi `k <= 1` tự nối nếu duy nhất, `k == 2` hoặc nhiều thì gợi ý, không có thì `disputed`; lọc ứng viên cùng `vehicle_group`, `color` tham khảo; phí `flat` hoặc `block` làm tròn lên không grace, đọc giá lúc ra, lưu `fee_rule_snapshot`; `disputed` không tự tính phí; đường lùi nhập tay luôn có; audit khi sửa biển; commit chờ người dùng; phase khép bằng acceptance test.

## Interfaces Phase 1 tới 3 dùng lại

- `app.models.ParkingSession`, `PlateReading`, `PriceRule`, `ImageAsset`.
- `app.security.crypto.encrypt_text/decrypt_text`, `app.security.plate.normalize_plate/plate_hash`.
- `app.services.vehicle_groups.group_for`, `app.services.audit.write_audit`.
- `app.deps.get_current_user`, `app.config.settings.retention_days`.
- Fixture test `client`, `db_session`, `make_user`.

## File Structure

- Create: `src/backend/app/services/matching.py` edit distance và quyết định khớp.
- Create: `src/backend/app/services/fee.py` tính phí và đọc bảng giá hiện hành.
- Create: `src/backend/app/schemas/session.py` schema request và response.
- Create: `src/backend/app/routers/sessions.py` entry, exit, manual, dispute, resolve.
- Create: `src/backend/app/routers/readings.py` sửa biển tay.
- Modify: `src/backend/app/main.py` gắn hai router.
- Modify: `src/backend/tests/conftest.py` thêm fixture `staff_headers`.
- Create: `tests/test_matching.py`, `test_fee.py`, `test_session_entry.py`, `test_session_exit.py`, `test_session_manual_dispute.py`, `test_phase4_acceptance.py`.

---

### Task 1: Service khớp biển

**Files:**
- Create: `src/backend/app/services/matching.py`
- Create: `src/backend/tests/test_matching.py`

**Interfaces:**
- Produces: `matching.edit_distance(a: str, b: str) -> int`; dataclass `matching.Candidate(session_id: int, plate_hash: str, plate_norm: str, vehicle_group: str)`; dataclass `matching.MatchResult(kind: str, session_id: int | None, match_flag: str | None, candidate_ids: list[int])` với `kind` thuộc `exact|auto|suggest|none`; `matching.find_match(target_hash: str, target_norm: str, group: str, candidates: list[Candidate]) -> MatchResult`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_matching.py`:

```python
from app.services.matching import Candidate, edit_distance, find_match


def test_edit_distance_basic():
    assert edit_distance("51F12345", "51F12345") == 0
    assert edit_distance("51F12345", "51F12346") == 1
    assert edit_distance("51F12345", "51F12300") == 2


def _c(sid, norm, group="o_to_con", hashv=None):
    return Candidate(session_id=sid, plate_hash=hashv or f"h{sid}", plate_norm=norm, vehicle_group=group)


def test_exact_unique():
    cands = [_c(1, "51F12345", hashv="H")]
    r = find_match("H", "51F12345", "o_to_con", cands)
    assert r.kind == "exact" and r.session_id == 1 and r.match_flag == "exact"


def test_exact_multiple_suggests():
    cands = [_c(1, "51F12345", hashv="H"), _c(2, "51F12345", hashv="H")]
    r = find_match("H", "51F12345", "o_to_con", cands)
    assert r.kind == "suggest" and set(r.candidate_ids) == {1, 2}


def test_fuzzy_unique_k1_auto():
    cands = [_c(1, "51F12346")]  # cách biển đích 1 ký tự
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "auto" and r.session_id == 1 and r.match_flag == "auto_corrected"


def test_fuzzy_k2_only_suggests():
    cands = [_c(1, "51F12300")]  # cách 2 ký tự
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "suggest" and r.candidate_ids == [1]


def test_two_close_candidates_suggest():
    cands = [_c(1, "51F12346"), _c(2, "51F12344")]  # cả hai cách 1
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "suggest" and set(r.candidate_ids) == {1, 2}


def test_group_filter_excludes():
    cands = [_c(1, "51F12346", group="xe_may")]
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "none"


def test_no_candidate_within_two():
    cands = [_c(1, "99Z99999")]
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "none"
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_matching.py -v`
Expected: FAIL vì `app.services.matching` chưa có.

- [ ] **Step 3: Viết matching.py**

```python
from dataclasses import dataclass, field


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


@dataclass(frozen=True)
class Candidate:
    session_id: int
    plate_hash: str
    plate_norm: str
    vehicle_group: str


@dataclass
class MatchResult:
    kind: str  # exact | auto | suggest | none
    session_id: int | None = None
    match_flag: str | None = None
    candidate_ids: list[int] = field(default_factory=list)


def find_match(target_hash: str, target_norm: str, group: str, candidates: list[Candidate]) -> MatchResult:
    exact = [c for c in candidates if target_hash and c.plate_hash == target_hash]
    if len(exact) == 1:
        return MatchResult("exact", session_id=exact[0].session_id, match_flag="exact")
    if len(exact) > 1:
        return MatchResult("suggest", candidate_ids=[c.session_id for c in exact])

    scored = [(c, edit_distance(target_norm, c.plate_norm)) for c in candidates if c.vehicle_group == group]
    scored = [(c, d) for c, d in scored if d <= 2]
    if not scored:
        return MatchResult("none")
    if len(scored) == 1 and scored[0][1] <= 1:
        return MatchResult("auto", session_id=scored[0][0].session_id, match_flag="auto_corrected")
    scored.sort(key=lambda cd: cd[1])
    return MatchResult("suggest", candidate_ids=[c.session_id for c, _ in scored])
```

- [ ] **Step 4: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_matching.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 5: Commit (điểm mốc)**

```bash
git add src/backend/app/services/matching.py src/backend/tests/test_matching.py
git commit -m "feat(backend): plate matching with edit distance and candidate policy"
```

---

### Task 2: Service tính phí

**Files:**
- Create: `src/backend/app/services/fee.py`
- Create: `src/backend/tests/test_fee.py`

**Interfaces:**
- Consumes: `app.models.PriceRule`.
- Produces: `fee.compute_fee(rule: PriceRule, entry_time: datetime, exit_time: datetime) -> tuple[int, dict]`; `fee.get_active_rule(db, vehicle_group: str) -> PriceRule | None`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_fee.py`:

```python
from datetime import datetime, timedelta

from app.models import PriceRule
from app.services.fee import compute_fee, get_active_rule


def test_flat_fee_ignores_duration():
    rule = PriceRule(vehicle_group="xe_may", mode="flat", unit_price=3000, active=True)
    entry = datetime(2026, 8, 22, 8, 0, 0)
    fee, snap = compute_fee(rule, entry, entry + timedelta(hours=5))
    assert fee == 3000
    assert snap["mode"] == "flat"


def test_block_fee_rounds_up():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True)
    entry = datetime(2026, 8, 22, 8, 0, 0)
    fee, snap = compute_fee(rule, entry, entry + timedelta(minutes=90))
    assert fee == 10000  # ceil(1.5) = 2 block
    assert snap["blocks"] == 2


def test_block_minimum_one():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True)
    entry = datetime(2026, 8, 22, 8, 0, 0)
    fee, snap = compute_fee(rule, entry, entry)  # 0 phút
    assert fee == 5000
    assert snap["blocks"] == 1


def test_get_active_rule(db_session):
    db_session.add_all([
        PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True),
        PriceRule(vehicle_group="o_to_con", mode="block", unit_price=1000, block_minutes=60, active=False),
    ])
    db_session.commit()
    rule = get_active_rule(db_session, "o_to_con")
    assert rule is not None and rule.unit_price == 5000
    assert get_active_rule(db_session, "xe_tai") is None
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_fee.py -v`
Expected: FAIL vì `app.services.fee` chưa có.

- [ ] **Step 3: Viết fee.py**

```python
import math
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PriceRule


def compute_fee(rule: PriceRule, entry_time: datetime, exit_time: datetime) -> tuple[int, dict]:
    if rule.mode == "flat":
        return rule.unit_price, {"mode": "flat", "unit_price": rule.unit_price}
    minutes = max(0.0, (exit_time - entry_time).total_seconds() / 60.0)
    blocks = max(1, math.ceil(minutes / rule.block_minutes))
    fee = blocks * rule.unit_price
    return fee, {
        "mode": "block",
        "unit_price": rule.unit_price,
        "block_minutes": rule.block_minutes,
        "blocks": blocks,
        "minutes": round(minutes, 2),
    }


def get_active_rule(db: Session, vehicle_group: str) -> PriceRule | None:
    return db.scalars(
        select(PriceRule)
        .where(PriceRule.vehicle_group == vehicle_group, PriceRule.active.is_(True))
        .order_by(PriceRule.updated_at.desc())
    ).first()
```

- [ ] **Step 4: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_fee.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 5: Commit (điểm mốc)**

```bash
git add src/backend/app/services/fee.py src/backend/tests/test_fee.py
git commit -m "feat(backend): fee computation and active price rule lookup"
```

---

### Task 3: Xác nhận xe vào

**Files:**
- Create: `src/backend/app/schemas/session.py`
- Create: `src/backend/app/routers/sessions.py`
- Modify: `src/backend/app/main.py`
- Modify: `src/backend/tests/conftest.py` (thêm `staff_headers`)
- Create: `src/backend/tests/test_session_entry.py`

**Interfaces:**
- Consumes: `PlateReading`, `group_for`, `crypto`, `get_current_user`.
- Produces: schema `EntryRequest`, `SessionOut`, `SessionBrief`, `ExitRequest`, `ExitResult`, `ManualRequest`, `ResolveRequest`, `PlatePatch`; `POST /sessions/entry` tạo `in_lot` từ `reading_id` (hoặc `pending_manual` nếu reading không có biển), cảnh báo khi trùng biển đang trong bãi; helper `_session_out`. Fixture `staff_headers`.

- [ ] **Step 1: Viết schemas/session.py**

```python
from datetime import datetime

from pydantic import BaseModel


class EntryRequest(BaseModel):
    reading_id: int


class ExitRequest(BaseModel):
    reading_id: int
    session_id: int | None = None  # nhân viên chọn ứng viên khi gợi ý


class ManualRequest(BaseModel):
    action: str  # entry | exit
    plate_text: str | None = None
    vehicle_group: str | None = None
    session_id: int | None = None


class ResolveRequest(BaseModel):
    fee_amount: int


class PlatePatch(BaseModel):
    plate_text: str


class SessionOut(BaseModel):
    id: int
    status: str
    vehicle_group: str | None = None
    plate_text: str | None = None
    entry_time: datetime | None = None
    exit_time: datetime | None = None
    fee_amount: int | None = None
    match_flag: str | None = None
    warning: str | None = None


class SessionBrief(BaseModel):
    id: int
    plate_text: str | None = None
    vehicle_group: str
    entry_time: datetime | None = None


class ExitResult(BaseModel):
    outcome: str  # completed | suggest | disputed
    session: SessionOut | None = None
    candidates: list[SessionBrief] = []
    match_flag: str | None = None
```

- [ ] **Step 2: Thêm fixture staff_headers vào conftest.py**

Thêm vào cuối `src/backend/tests/conftest.py`:

```python
@pytest.fixture()
def staff_headers(client, make_user):
    make_user(username="gate", password="pw", role="staff")
    token = client.post("/auth/login", json={"username": "gate", "password": "pw"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 3: Viết test thất bại cho entry**

`src/backend/tests/test_session_entry.py`:

```python
from app.models import ParkingSession, PlateReading
from app.security import crypto, plate


def _insert_reading(db, *, direction="in", plate_text="51F-123.45", vehicle_type="car", cid=None):
    r = PlateReading(
        capture_id=cid or f"cap-{plate_text}-{direction}",
        direction=direction,
        plate_text_ciphertext=crypto.encrypt_text(plate_text) if plate_text else None,
        plate_hash=plate.plate_hash(plate_text) if plate_text else None,
        plate_valid=True,
        vehicle_type=vehicle_type,
        review_state="confident" if plate_text else "needs_review",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_entry_creates_in_lot(client, db_session, staff_headers):
    reading = _insert_reading(db_session)
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "in_lot"
    assert body["vehicle_group"] == "o_to_con"
    assert body["plate_text"] == "51F-123.45"


def test_entry_no_plate_pending_manual(client, db_session, staff_headers):
    reading = _insert_reading(db_session, plate_text=None)
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert r.json()["status"] == "pending_manual"


def test_entry_duplicate_plate_warns_not_blocks(client, db_session, staff_headers):
    r1 = _insert_reading(db_session, cid="c1")
    client.post("/sessions/entry", json={"reading_id": r1.id}, headers=staff_headers)
    r2 = _insert_reading(db_session, cid="c2")
    resp = client.post("/sessions/entry", json={"reading_id": r2.id}, headers=staff_headers)
    assert resp.status_code == 200
    assert resp.json()["warning"] is not None
    assert db_session.query(ParkingSession).count() == 2


def test_entry_requires_auth(client, db_session):
    reading = _insert_reading(db_session)
    assert client.post("/sessions/entry", json={"reading_id": reading.id}).status_code in (401, 403)
```

- [ ] **Step 4: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_session_entry.py -v`
Expected: FAIL vì route `/sessions/entry` chưa có.

- [ ] **Step 5: Viết routers/sessions.py (entry cộng helper)**

```python
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import ImageAsset, ParkingSession, PlateReading, User
from app.schemas.session import EntryRequest, SessionOut
from app.security import crypto
from app.services.vehicle_groups import group_for

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _session_out(s: ParkingSession, warning: str | None = None) -> SessionOut:
    text = crypto.decrypt_text(s.plate_ciphertext) if s.plate_ciphertext else None
    return SessionOut(
        id=s.id,
        status=s.status,
        vehicle_group=s.vehicle_group or None,
        plate_text=text,
        entry_time=s.entry_time,
        exit_time=s.exit_time,
        fee_amount=s.fee_amount,
        match_flag=s.match_flag,
        warning=warning,
    )


@router.post("/entry", response_model=SessionOut)
def confirm_entry(body: EntryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    reading = db.get(PlateReading, body.reading_id)
    if reading is None or reading.direction != "in":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading vào hợp lệ")

    group = group_for(reading.vehicle_type) or "unknown"
    has_plate = bool(reading.plate_hash)
    warning = None
    if has_plate:
        dup = db.scalars(
            select(ParkingSession).where(
                ParkingSession.plate_hash == reading.plate_hash,
                ParkingSession.status == "in_lot",
            )
        ).first()
        if dup is not None:
            warning = "biển trùng một xe đang trong bãi"

    session = ParkingSession(
        plate_hash=reading.plate_hash or "",
        plate_ciphertext=reading.plate_text_ciphertext or "",
        vehicle_group=group,
        vehicle_type=reading.vehicle_type,
        status="in_lot" if has_plate else "pending_manual",
        entry_time=datetime.utcnow(),
        entry_reading_id=reading.id,
        match_flag="exact" if has_plate else None,
        created_by=user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_out(session, warning=warning)
```

- [ ] **Step 6: Gắn router sessions vào main.py**

Sửa `src/backend/app/main.py` để thêm import và include (giữ nguyên các router cũ):

```python
from fastapi import FastAPI

from app.routers import auth, captures, sessions, users


def create_app() -> FastAPI:
    app = FastAPI(title="Parking backend")
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(captures.router)
    app.include_router(sessions.router)
    return app


app = create_app()
```

- [ ] **Step 7: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_session_entry.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 8: Commit (điểm mốc)**

```bash
git add src/backend/app/schemas/session.py src/backend/app/routers/sessions.py src/backend/app/main.py src/backend/tests/conftest.py src/backend/tests/test_session_entry.py
git commit -m "feat(backend): confirm vehicle entry endpoint"
```

---

### Task 4: Xác nhận xe ra và khớp phiên

**Files:**
- Modify: `src/backend/app/routers/sessions.py` (thêm exit và helper hoàn tất)
- Create: `src/backend/tests/test_session_exit.py`

**Interfaces:**
- Consumes: `find_match`, `Candidate`, `compute_fee`, `get_active_rule`, `normalize_plate`, `crypto`, `settings.retention_days`.
- Produces: `POST /sessions/exit` trả `ExitResult` (`completed` khi exact hoặc auto hoặc nhân viên chọn `session_id`; `suggest` kèm `candidates`; `disputed` khi không ứng viên); helper `_complete_session` set phí, `exit_time`, `match_flag`, `retention_delete_after` cho ảnh.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_session_exit.py`:

```python
from app.models import ParkingSession, PlateReading, PriceRule
from app.security import crypto, plate


def _seed_price(db):
    db.add(PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True))
    db.commit()


def _reading(db, *, direction, plate_text, vehicle_type="car", cid):
    r = PlateReading(
        capture_id=cid, direction=direction,
        plate_text_ciphertext=crypto.encrypt_text(plate_text) if plate_text else None,
        plate_hash=plate.plate_hash(plate_text) if plate_text else None,
        plate_valid=True, vehicle_type=vehicle_type, review_state="confident",
    )
    db.add(r); db.commit(); db.refresh(r); return r


def _enter(client, db, headers, plate_text, cid):
    reading = _reading(db, direction="in", plate_text=plate_text, cid=cid)
    return client.post("/sessions/entry", json={"reading_id": reading.id}, headers=headers).json()


def test_exit_exact_completes_with_fee(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.45", "in1")
    out = _reading(db_session, direction="out", plate_text="51F-123.45", cid="out1")
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    body = r.json()
    assert body["outcome"] == "completed"
    assert body["match_flag"] == "exact"
    assert body["session"]["status"] == "completed"
    assert body["session"]["fee_amount"] == 5000


def test_exit_fuzzy_k1_auto(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.45", "in2")
    out = _reading(db_session, direction="out", plate_text="51F-123.46", cid="out2")  # sai 1 ký tự
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    assert r.json()["outcome"] == "completed"
    assert r.json()["match_flag"] == "auto_corrected"


def test_exit_two_candidates_suggests(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.46", "in3a")
    _enter(client, db_session, staff_headers, "51F-123.44", "in3b")  # cả hai cách biển ra 1 ký tự
    out = _reading(db_session, direction="out", plate_text="51F-123.45", cid="out3")
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    body = r.json()
    assert body["outcome"] == "suggest"
    assert len(body["candidates"]) == 2


def test_exit_choose_candidate_completes(client, db_session, staff_headers):
    _seed_price(db_session)
    s = _enter(client, db_session, staff_headers, "51F-123.46", "in4")
    out = _reading(db_session, direction="out", plate_text="51F-999.99", cid="out4")
    r = client.post("/sessions/exit", json={"reading_id": out.id, "session_id": s["id"]}, headers=staff_headers)
    assert r.json()["outcome"] == "completed"
    assert r.json()["match_flag"] == "manual"


def test_exit_no_candidate_disputed(client, db_session, staff_headers):
    _seed_price(db_session)
    _enter(client, db_session, staff_headers, "51F-123.45", "in5")
    out = _reading(db_session, direction="out", plate_text="99Z-999.99", cid="out5")
    r = client.post("/sessions/exit", json={"reading_id": out.id}, headers=staff_headers)
    body = r.json()
    assert body["outcome"] == "disputed"
    assert body["session"]["fee_amount"] is None
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_session_exit.py -v`
Expected: FAIL vì route `/sessions/exit` chưa có.

- [ ] **Step 3: Thêm exit và helper vào routers/sessions.py**

Thêm import ở đầu file (nối vào khối import hiện có):

```python
from app.models import PriceRule  # noqa: F401  dùng gián tiếp qua fee service
from app.schemas.session import ExitRequest, ExitResult, SessionBrief
from app.security.plate import normalize_plate
from app.services.fee import compute_fee, get_active_rule
from app.services.matching import Candidate, find_match
```

Thêm vào cuối file:

```python
def _set_retention(db: Session, session: ParkingSession) -> None:
    if session.exit_time is None:
        return
    delete_after = session.exit_time + timedelta(days=settings.retention_days)
    for rid in (session.entry_reading_id, session.exit_reading_id):
        if not rid:
            continue
        reading = db.get(PlateReading, rid)
        if reading and reading.image_asset_id:
            asset = db.get(ImageAsset, reading.image_asset_id)
            if asset:
                asset.retention_delete_after = delete_after


def _complete_session(db: Session, session: ParkingSession, exit_reading_id: int | None, match_flag: str, user: User) -> None:
    rule = get_active_rule(db, session.vehicle_group)
    if rule is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "chưa có bảng giá cho nhóm xe này")
    session.exit_reading_id = exit_reading_id
    session.exit_time = datetime.utcnow()
    session.match_flag = match_flag
    fee, snapshot = compute_fee(rule, session.entry_time, session.exit_time)
    session.fee_amount = fee
    session.fee_rule_snapshot = snapshot
    session.status = "completed"
    session.closed_by = user.id
    _set_retention(db, session)


@router.post("/exit", response_model=ExitResult)
def confirm_exit(body: ExitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ExitResult:
    reading = db.get(PlateReading, body.reading_id)
    if reading is None or reading.direction != "out":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading ra hợp lệ")

    in_lot = list(db.scalars(select(ParkingSession).where(ParkingSession.status == "in_lot")).all())

    if body.session_id is not None:
        chosen = next((s for s in in_lot if s.id == body.session_id), None)
        if chosen is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session được chọn không còn trong bãi")
        _complete_session(db, chosen, reading.id, match_flag="manual", user=user)
        db.commit()
        db.refresh(chosen)
        return ExitResult(outcome="completed", session=_session_out(chosen), match_flag="manual")

    target_norm = normalize_plate(crypto.decrypt_text(reading.plate_text_ciphertext)) if reading.plate_text_ciphertext else ""
    group = group_for(reading.vehicle_type) or "unknown"
    candidates = [
        Candidate(
            session_id=s.id,
            plate_hash=s.plate_hash,
            plate_norm=normalize_plate(crypto.decrypt_text(s.plate_ciphertext)) if s.plate_ciphertext else "",
            vehicle_group=s.vehicle_group,
        )
        for s in in_lot
    ]
    result = find_match(reading.plate_hash or "", target_norm, group, candidates)

    if result.kind in ("exact", "auto"):
        matched = next(s for s in in_lot if s.id == result.session_id)
        _complete_session(db, matched, reading.id, match_flag=result.match_flag, user=user)
        db.commit()
        db.refresh(matched)
        return ExitResult(outcome="completed", session=_session_out(matched), match_flag=result.match_flag)

    if result.kind == "suggest":
        briefs = [
            SessionBrief(
                id=s.id,
                plate_text=crypto.decrypt_text(s.plate_ciphertext) if s.plate_ciphertext else None,
                vehicle_group=s.vehicle_group,
                entry_time=s.entry_time,
            )
            for s in in_lot if s.id in result.candidate_ids
        ]
        return ExitResult(outcome="suggest", candidates=briefs)

    disputed = ParkingSession(
        plate_hash=reading.plate_hash or "",
        plate_ciphertext=reading.plate_text_ciphertext or "",
        vehicle_group=group,
        vehicle_type=reading.vehicle_type,
        status="disputed",
        exit_time=datetime.utcnow(),
        exit_reading_id=reading.id,
        closed_by=user.id,
    )
    db.add(disputed)
    db.commit()
    db.refresh(disputed)
    return ExitResult(outcome="disputed", session=_session_out(disputed))
```

- [ ] **Step 4: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_session_exit.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 5: Commit (điểm mốc)**

```bash
git add src/backend/app/routers/sessions.py src/backend/tests/test_session_exit.py
git commit -m "feat(backend): confirm exit with plate matching and fee"
```

---

### Task 5: Nhập tay hoàn toàn, sửa biển, dispute

**Files:**
- Modify: `src/backend/app/routers/sessions.py` (thêm manual, dispute, resolve)
- Create: `src/backend/app/routers/readings.py` (PATCH sửa biển)
- Modify: `src/backend/app/main.py` (gắn router readings)
- Create: `src/backend/tests/test_session_manual_dispute.py`

**Interfaces:**
- Consumes: `plate_hash`, `crypto`, `write_audit`, `compute_fee`, `get_active_rule`.
- Produces: `POST /sessions/manual` (action `entry` tạo `in_lot` từ biển gõ tay; action `exit` đóng `session_id` thủ công); `POST /sessions/{id}/dispute` chuyển `disputed`; `POST /sessions/{id}/resolve` nhập phí tay và `completed`; `PATCH /readings/{id}/plate` sửa biển cộng ghi audit.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_session_manual_dispute.py`:

```python
from sqlalchemy import select

from app.models import AuditLog, ParkingSession, PlateReading, PriceRule
from app.security import crypto, plate


def _seed_price(db):
    db.add(PriceRule(vehicle_group="xe_may", mode="flat", unit_price=3000, active=True))
    db.commit()


def test_manual_entry_then_exit(client, db_session, staff_headers):
    _seed_price(db_session)
    r = client.post("/sessions/manual", json={"action": "entry", "plate_text": "59X1-234.56", "vehicle_group": "xe_may"}, headers=staff_headers)
    assert r.status_code == 200
    sid = r.json()["id"]
    assert r.json()["status"] == "in_lot"
    assert r.json()["match_flag"] == "manual"

    r2 = client.post("/sessions/manual", json={"action": "exit", "session_id": sid}, headers=staff_headers)
    assert r2.json()["status"] == "completed"
    assert r2.json()["fee_amount"] == 3000


def test_patch_plate_updates_and_audits(client, db_session, staff_headers):
    reading = PlateReading(capture_id="patch1", direction="in", plate_text_ciphertext=crypto.encrypt_text("51F-000.00"),
                           plate_hash=plate.plate_hash("51F-000.00"), review_state="needs_review", vehicle_type="car")
    db_session.add(reading); db_session.commit(); db_session.refresh(reading)

    r = client.patch(f"/readings/{reading.id}/plate", json={"plate_text": "51F-123.45"}, headers=staff_headers)
    assert r.status_code == 200
    db_session.refresh(reading)
    assert reading.plate_hash == plate.plate_hash("51F12345")
    assert reading.review_state == "manual"
    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "edit_plate")).all()
    assert len(logs) == 1


def test_dispute_then_resolve(client, db_session, staff_headers):
    session = ParkingSession(plate_hash="h", plate_ciphertext=crypto.encrypt_text("51F-123.45"),
                             vehicle_group="o_to_con", status="in_lot")
    db_session.add(session); db_session.commit(); db_session.refresh(session)

    assert client.post(f"/sessions/{session.id}/dispute", headers=staff_headers).json()["status"] == "disputed"

    r = client.post(f"/sessions/{session.id}/resolve", json={"fee_amount": 8000}, headers=staff_headers)
    assert r.json()["status"] == "completed"
    assert r.json()["fee_amount"] == 8000
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_session_manual_dispute.py -v`
Expected: FAIL vì các route chưa có.

- [ ] **Step 3: Thêm manual, dispute, resolve vào routers/sessions.py**

Thêm import (nối vào khối import):

```python
from datetime import datetime as _dt  # đã có datetime; giữ nguyên, dòng này không bắt buộc nếu datetime đã import
from app.schemas.session import ManualRequest, ResolveRequest
```

Thêm vào cuối file:

```python
@router.post("/manual", response_model=SessionOut)
def manual_session(body: ManualRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    if body.action == "entry":
        if not body.plate_text or not body.vehicle_group:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nhập tay cần plate_text và vehicle_group")
        session = ParkingSession(
            plate_hash=plate_hash(body.plate_text),
            plate_ciphertext=crypto.encrypt_text(body.plate_text),
            vehicle_group=body.vehicle_group,
            status="in_lot",
            entry_time=datetime.utcnow(),
            match_flag="manual",
            created_by=user.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return _session_out(session)

    if body.action == "exit":
        if body.session_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nhập tay ra cần session_id")
        session = db.get(ParkingSession, body.session_id)
        if session is None or session.status != "in_lot":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session không ở trạng thái in_lot")
        _complete_session(db, session, exit_reading_id=None, match_flag="manual", user=user)
        db.commit()
        db.refresh(session)
        return _session_out(session)

    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "action phải là entry hoặc exit")


@router.post("/{session_id}/dispute", response_model=SessionOut)
def dispute_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    session = db.get(ParkingSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    session.status = "disputed"
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.post("/{session_id}/resolve", response_model=SessionOut)
def resolve_session(session_id: int, body: ResolveRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SessionOut:
    session = db.get(ParkingSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy session")
    session.fee_amount = body.fee_amount
    session.status = "completed"
    session.closed_by = user.id
    if session.exit_time is None:
        session.exit_time = datetime.utcnow()
    _set_retention(db, session)
    db.commit()
    db.refresh(session)
    return _session_out(session)
```

Thêm import `plate_hash` vào đầu file (nếu chưa có): sửa dòng import plate thành:

```python
from app.security.plate import normalize_plate, plate_hash
```

- [ ] **Step 4: Viết routers/readings.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import PlateReading, User
from app.schemas.session import PlatePatch, SessionOut  # SessionOut không dùng, giữ import gọn
from app.security import crypto
from app.security.plate import plate_hash
from app.services.audit import write_audit

router = APIRouter(prefix="/readings", tags=["readings"])


@router.patch("/{reading_id}/plate")
def patch_plate(reading_id: int, body: PlatePatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    reading = db.get(PlateReading, reading_id)
    if reading is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading")
    reading.plate_text_ciphertext = crypto.encrypt_text(body.plate_text)
    reading.plate_hash = plate_hash(body.plate_text)
    reading.review_state = "manual"
    write_audit(db, user_id=user.id, action="edit_plate", entity_type="reading", entity_id=str(reading.id))
    db.commit()
    return {"reading_id": reading.id, "plate_text": body.plate_text, "review_state": "manual"}
```

Ghi chú: bỏ `SessionOut` khỏi dòng import nếu linter báo thừa; giữ `PlatePatch`.

- [ ] **Step 5: Gắn router readings vào main.py**

Sửa `src/backend/app/main.py`:

```python
from fastapi import FastAPI

from app.routers import auth, captures, readings, sessions, users


def create_app() -> FastAPI:
    app = FastAPI(title="Parking backend")
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(captures.router)
    app.include_router(sessions.router)
    app.include_router(readings.router)
    return app


app = create_app()
```

- [ ] **Step 6: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_session_manual_dispute.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/backend/app/routers/sessions.py src/backend/app/routers/readings.py src/backend/app/main.py src/backend/tests/test_session_manual_dispute.py
git commit -m "feat(backend): manual session, plate correction and dispute handling"
```

---

### Task 6: Test nghiệm thu Phase 4

Kiểm chứng vòng đời đầy đủ trên một luồng: vào bằng AI, ra khớp exact tính phí đúng; ra OCR sai một ký tự tự nối; ra biển lạ chuyển `disputed`.

**Files:**
- Create: `src/backend/tests/test_phase4_acceptance.py`

**Interfaces:**
- Consumes: endpoint `/sessions/entry`, `/sessions/exit`; `PlateReading`, `PriceRule`.
- Produces: cổng nghiệm thu.

- [ ] **Step 1: Viết test nghiệm thu**

`src/backend/tests/test_phase4_acceptance.py`:

```python
from app.models import PlateReading, PriceRule
from app.security import crypto, plate


def _reading(db, *, direction, plate_text, cid, vehicle_type="car"):
    r = PlateReading(capture_id=cid, direction=direction,
                     plate_text_ciphertext=crypto.encrypt_text(plate_text),
                     plate_hash=plate.plate_hash(plate_text), plate_valid=True,
                     vehicle_type=vehicle_type, review_state="confident")
    db.add(r); db.commit(); db.refresh(r); return r


def test_full_lifecycle(client, db_session, staff_headers):
    db_session.add(PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True))
    db_session.commit()

    # xe A vào rồi ra khớp exact
    ra = _reading(db_session, direction="in", plate_text="51F-123.45", cid="a-in")
    client.post("/sessions/entry", json={"reading_id": ra.id}, headers=staff_headers)
    ao = _reading(db_session, direction="out", plate_text="51F-123.45", cid="a-out")
    resp = client.post("/sessions/exit", json={"reading_id": ao.id}, headers=staff_headers)
    assert resp.json()["outcome"] == "completed"
    assert resp.json()["match_flag"] == "exact"
    assert resp.json()["session"]["fee_amount"] == 5000

    # xe B vào rồi ra OCR sai 1 ký tự tự nối
    rb = _reading(db_session, direction="in", plate_text="30A-678.90", cid="b-in")
    client.post("/sessions/entry", json={"reading_id": rb.id}, headers=staff_headers)
    bo = _reading(db_session, direction="out", plate_text="30A-678.91", cid="b-out")
    resp = client.post("/sessions/exit", json={"reading_id": bo.id}, headers=staff_headers)
    assert resp.json()["outcome"] == "completed"
    assert resp.json()["match_flag"] == "auto_corrected"

    # xe lạ ra không có phiên vào chuyển disputed
    co = _reading(db_session, direction="out", plate_text="99Z-999.99", cid="c-out")
    resp = client.post("/sessions/exit", json={"reading_id": co.id}, headers=staff_headers)
    assert resp.json()["outcome"] == "disputed"
    assert resp.json()["session"]["fee_amount"] is None
```

- [ ] **Step 2: Chạy test nghiệm thu**

Run: `cd src/backend && pytest tests/test_phase4_acceptance.py -v`
Expected: PASS.

- [ ] **Step 3: Chạy toàn bộ suite (Phase 1 tới 4)**

Run: `cd src/backend && pytest -v`
Expected: PASS toàn bộ, không lỗi và không skip.

- [ ] **Step 4: Commit (điểm mốc)**

```bash
git add src/backend/tests/test_phase4_acceptance.py
git commit -m "test(backend): phase 4 acceptance for session lifecycle"
```

---

## Self-Review (đã chạy khi soạn plan)

- **Spec coverage phase 4:** vào tạo `in_lot` cộng cảnh báo trùng biển (mục 4) phủ Task 3; khớp exact rồi `k <= 1` tự nối rồi `k == 2` gợi ý rồi `disputed` (mục 4) phủ Task 1 và 4; nhập tay hoàn toàn (mục 4, nguyên tắc bắt buộc) phủ Task 5; sửa biển tay cộng audit (mục 4, 9) phủ Task 5; tính phí flat và block đọc giá lúc ra cộng `fee_rule_snapshot` (mục 5) phủ Task 2 và 4; `disputed` không tự tính phí (mục 4, 5) phủ Task 4 và 5; set `retention_delete_after` từ `exit_time` (mục 10) phủ Task 4 helper.
- **Placeholder scan:** không có; mọi step có code hoặc lệnh.
- **Type consistency:** `find_match` trả `MatchResult` với `kind` và `match_flag` dùng nhất quán ở router exit; `_complete_session` và `_set_retention` và `_session_out` chữ ký thống nhất trong `sessions.py`; `compute_fee` và `get_active_rule` khớp giữa fee service và router; schema `ExitResult`, `SessionOut`, `SessionBrief` khớp giữa router và test; `plate_hash` và `normalize_plate` import từ `app.security.plate`.
- **Ghi chú:** dùng helper `app.clock.now_utc()` (UTC naive) thay `datetime.utcnow()` ở mọi nơi ghi thời gian, để tránh lỗi trừ aware và naive giữa SQLite và Postgres, và tránh DeprecationWarning trên Python 3.12 trở lên.
- **Ghi chú tz (bắt buộc cho Postgres):** cột `DateTime(timezone=True)` trả datetime **aware** trên Postgres nhưng **naive** trên SQLite. `compute_fee` phải coerce cả `entry_time` và `exit_time` về naive bằng `app.clock.to_naive` trước khi trừ, nếu không trên Postgres sẽ `TypeError: can't subtract offset-naive and offset-aware` → 500 khi xác nhận ra. Unit test SQLite không bắt được lỗi này; chỉ e2e trên Postgres mới lộ.

## Điểm nối sang Phase 5

Phase 5 đọc `ParkingSession` và `PlateReading` và `ImageAsset` cho tra cứu, thống kê, ảnh; dùng `_session_out` mẫu để trả chi tiết; dùng `retention_delete_after` đã set ở phase này cho job xóa; thêm CRUD `price_rule`, `lane`, `feature_toggle`, endpoint `GET /images/{id}` chặn auth cộng audit, và `WS /ws/gate`.
