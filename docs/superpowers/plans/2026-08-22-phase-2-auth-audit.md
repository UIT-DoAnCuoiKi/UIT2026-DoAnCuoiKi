# Phase 2: Auth, phân vai, audit log

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** đăng nhập JWT, băm mật khẩu, dependency phân vai `staff` và `admin`, ghi `audit_log`, và CRUD tài khoản (chỉ admin), trên nền Phase 1.

**Architecture:** app factory `create_app()` gắn router `auth` và `users`. Xác thực bằng JWT bearer; `get_current_user` giải token và nạp `User`; `require_role(*roles)` chặn theo vai. Mọi hành động nhạy cảm ghi một dòng `AuditLog` trong cùng transaction. Test dùng FastAPI TestClient trên SQLite StaticPool, override `get_db`.

**Tech Stack:** FastAPI, bcrypt (trực tiếp, không passlib), PyJWT, SQLAlchemy 2.0, pytest, httpx TestClient.

## Global Constraints

Xem `2026-08-22-dashboard-mvp-plan-index.md`. Riêng phase này: vai `staff` và `admin`; audit ghi ít nhất `login`, `create_user`, `update_user`; JWT secret và thời hạn nạp từ env (`settings.jwt_secret`, `settings.jwt_expire_minutes`); commit chờ người dùng; phase khép bằng acceptance test.

## Interfaces Phase 1 dùng lại

- `app.db.Base`, `app.db.get_db`, `app.db.SessionLocal`.
- `app.models.User` (`id`, `username`, `password_hash`, `role`, `active`), `app.models.AuditLog` (`user_id`, `action`, `entity_type`, `entity_id`, `detail`).
- `app.config.settings.jwt_secret`, `settings.jwt_expire_minutes`.

## File Structure

- Modify: `src/backend/requirements.txt` (ghim `bcrypt`).
- Create: `src/backend/app/security/passwords.py` băm và kiểm mật khẩu.
- Create: `src/backend/app/security/tokens.py` tạo và giải JWT.
- Create: `src/backend/app/services/__init__.py`, `src/backend/app/services/audit.py` ghi audit.
- Create: `src/backend/app/deps.py` `get_current_user`, `require_role`.
- Create: `src/backend/app/schemas/__init__.py`, `schemas/auth.py`, `schemas/user.py`.
- Create: `src/backend/app/routers/__init__.py`, `routers/auth.py`, `routers/users.py`.
- Create: `src/backend/app/main.py` app factory.
- Modify: `src/backend/tests/conftest.py` thêm fixture `db_session`, `client`, `make_user`.
- Create: `tests/test_passwords.py`, `test_tokens.py`, `test_audit.py`, `test_auth_login.py`, `test_rbac_users.py`, `test_phase2_acceptance.py`.

---

### Task 1: Băm mật khẩu và JWT

**Files:**
- Modify: `src/backend/requirements.txt`
- Create: `src/backend/app/security/passwords.py`
- Create: `src/backend/app/security/tokens.py`
- Create: `src/backend/tests/test_passwords.py`
- Create: `src/backend/tests/test_tokens.py`

**Interfaces:**
- Produces: `passwords.hash_password(p: str) -> str`, `passwords.verify_password(p: str, h: str) -> bool`; `tokens.create_access_token(sub: str, username: str, role: str) -> str`, `tokens.decode_token(token: str) -> dict`.

- [ ] **Step 1: Xác nhận bcrypt trong requirements.txt**

`requirements.txt` (Phase 1) dùng `bcrypt>=4.1,<6` và băm mật khẩu gọi thẳng thư viện `bcrypt`, không dùng passlib. Lý do: passlib 1.7.4 hết bảo trì và hỏng với bcrypt hiện đại (5.x) trên Python 3.13 (báo sai "password > 72 bytes"). Bảo đảm dòng `bcrypt>=4.1,<6` có trong `requirements.txt`; không cài passlib.

- [ ] **Step 2: Viết test thất bại cho passwords**

`src/backend/tests/test_passwords.py`:

```python
from app.security import passwords


def test_hash_differs_and_verifies():
    h = passwords.hash_password("secret123")
    assert h != "secret123"
    assert passwords.verify_password("secret123", h) is True
    assert passwords.verify_password("wrong", h) is False
```

- [ ] **Step 3: Viết test thất bại cho tokens**

`src/backend/tests/test_tokens.py`:

```python
import jwt
import pytest

from app.security import tokens


def test_create_and_decode():
    t = tokens.create_access_token("1", "admin1", "admin")
    payload = tokens.decode_token(t)
    assert payload["sub"] == "1"
    assert payload["username"] == "admin1"
    assert payload["role"] == "admin"


def test_expired_token_rejected(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "jwt_expire_minutes", -1)
    t = tokens.create_access_token("1", "admin1", "admin")
    with pytest.raises(jwt.ExpiredSignatureError):
        tokens.decode_token(t)
```

- [ ] **Step 4: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_passwords.py tests/test_tokens.py -v`
Expected: FAIL vì `passwords` và `tokens` chưa có.

- [ ] **Step 5: Viết passwords.py**

```python
import bcrypt

# bcrypt giới hạn mật khẩu 72 byte; cắt trước để tránh ValueError với bcrypt mới.
_MAX = 72


def hash_password(plaintext: str) -> str:
    pw = plaintext.encode("utf-8")[:_MAX]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    pw = plaintext.encode("utf-8")[:_MAX]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except ValueError:
        return False
```

- [ ] **Step 6: Viết tokens.py**

```python
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_ALGO = "HS256"


def create_access_token(sub: str, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])
```

- [ ] **Step 7: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_passwords.py tests/test_tokens.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 8: Commit (điểm mốc)**

```bash
git add src/backend/requirements.txt src/backend/app/security/passwords.py src/backend/app/security/tokens.py src/backend/tests/test_passwords.py src/backend/tests/test_tokens.py
git commit -m "feat(backend): password hashing and JWT utilities"
```

---

### Task 2: Fixture DB test và service ghi audit

**Files:**
- Modify: `src/backend/tests/conftest.py`
- Create: `src/backend/app/services/__init__.py`
- Create: `src/backend/app/services/audit.py`
- Create: `src/backend/tests/test_audit.py`

**Interfaces:**
- Consumes: `app.models.AuditLog`.
- Produces: `audit.write_audit(db, *, user_id, action, entity_type=None, entity_id=None, detail=None) -> None` (flush, không commit; caller commit). Fixture pytest `db_session` (một `Session` SQLite StaticPool đã tạo bảng).

- [ ] **Step 1: Thêm fixture db_session vào conftest.py**

Thêm vào cuối `src/backend/tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.models  # noqa: F401  đăng ký bảng


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
```

- [ ] **Step 2: Viết test thất bại cho audit**

`src/backend/tests/test_audit.py`:

```python
from sqlalchemy import select

from app.models import AuditLog
from app.services.audit import write_audit


def test_write_audit_inserts_row(db_session):
    write_audit(db_session, user_id=None, action="login")
    db_session.commit()
    rows = db_session.scalars(select(AuditLog)).all()
    assert len(rows) == 1
    assert rows[0].action == "login"


def test_write_audit_records_entity(db_session):
    write_audit(db_session, user_id=1, action="edit_plate", entity_type="reading", entity_id="7", detail="fix")
    db_session.commit()
    row = db_session.scalars(select(AuditLog)).one()
    assert row.entity_type == "reading"
    assert row.entity_id == "7"
    assert row.detail == "fix"
```

- [ ] **Step 3: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_audit.py -v`
Expected: FAIL vì `app.services.audit` chưa có.

- [ ] **Step 4: Tạo package marker services**

`src/backend/app/services/__init__.py`: file rỗng.

- [ ] **Step 5: Viết audit.py**

```python
from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    ))
    db.flush()
```

- [ ] **Step 6: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_audit.py -v`
Expected: PASS cả hai test.

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/backend/tests/conftest.py src/backend/app/services/__init__.py src/backend/app/services/audit.py src/backend/tests/test_audit.py
git commit -m "feat(backend): audit writer and DB test fixture"
```

---

### Task 3: App factory, deps xác thực, đăng nhập

**Files:**
- Create: `src/backend/app/deps.py`
- Create: `src/backend/app/schemas/__init__.py`
- Create: `src/backend/app/schemas/auth.py`
- Create: `src/backend/app/routers/__init__.py`
- Create: `src/backend/app/routers/auth.py`
- Create: `src/backend/app/main.py`
- Modify: `src/backend/tests/conftest.py` (thêm fixture `client`, `make_user`)
- Create: `src/backend/tests/test_auth_login.py`

**Interfaces:**
- Consumes: `tokens`, `passwords`, `audit`, `app.models.User`, `app.db.get_db`.
- Produces: `deps.get_current_user() -> User`, `deps.require_role(*roles) -> Callable`; `create_app() -> FastAPI`; endpoint `POST /auth/login` trả `{access_token, token_type, role}`. Fixture `client` (TestClient override `get_db`), `make_user(username, password, role, active) -> User`.

- [ ] **Step 1: Viết schemas/auth.py**

`src/backend/app/schemas/__init__.py`: file rỗng. `src/backend/app/schemas/auth.py`:

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
```

- [ ] **Step 2: Viết deps.py**

```python
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security.tokens import decode_token

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token không hợp lệ")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "tài khoản không hợp lệ")
    return user


def require_role(*roles: str) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "không đủ quyền")
        return user
    return checker
```

- [ ] **Step 3: Viết routers/auth.py**

`src/backend/app/routers/__init__.py`: file rỗng. `src/backend/app/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.security.passwords import verify_password
from app.security.tokens import create_access_token
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalars(select(User).where(User.username == body.username)).first()
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sai tài khoản hoặc mật khẩu")
    token = create_access_token(str(user.id), user.username, user.role)
    write_audit(db, user_id=user.id, action="login")
    db.commit()
    return TokenResponse(access_token=token, role=user.role)
```

- [ ] **Step 4: Viết main.py**

```python
from fastapi import FastAPI

from app.routers import auth


def create_app() -> FastAPI:
    app = FastAPI(title="Parking backend")
    app.include_router(auth.router)
    return app


app = create_app()
```

- [ ] **Step 5: Thêm fixture client và make_user vào conftest.py**

Thêm vào cuối `src/backend/tests/conftest.py`:

```python
@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from app.deps import get_db
    from app.main import create_app

    def _override_get_db():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


@pytest.fixture()
def make_user(db_session):
    from app.models import User
    from app.security.passwords import hash_password

    def _make(username="u", password="pw", role="staff", active=True) -> "User":
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            active=active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make
```

- [ ] **Step 6: Viết test đăng nhập**

`src/backend/tests/test_auth_login.py`:

```python
from sqlalchemy import select

from app.models import AuditLog


def test_login_success_and_audit(client, make_user, db_session):
    make_user(username="admin1", password="pw", role="admin")
    r = client.post("/auth/login", json={"username": "admin1", "password": "pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["role"] == "admin"
    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "login")).all()
    assert len(logs) == 1


def test_login_wrong_password(client, make_user):
    make_user(username="staff1", password="pw", role="staff")
    r = client.post("/auth/login", json={"username": "staff1", "password": "bad"})
    assert r.status_code == 401


def test_login_locked_user(client, make_user):
    make_user(username="locked", password="pw", role="staff", active=False)
    r = client.post("/auth/login", json={"username": "locked", "password": "pw"})
    assert r.status_code == 401
```

- [ ] **Step 7: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_auth_login.py -v`
Expected: PASS cả ba test.

- [ ] **Step 8: Commit (điểm mốc)**

```bash
git add src/backend/app/deps.py src/backend/app/schemas src/backend/app/routers src/backend/app/main.py src/backend/tests/conftest.py src/backend/tests/test_auth_login.py
git commit -m "feat(backend): app factory, JWT auth deps and login endpoint"
```

---

### Task 4: CRUD tài khoản và phân vai

**Files:**
- Create: `src/backend/app/schemas/user.py`
- Create: `src/backend/app/routers/users.py`
- Modify: `src/backend/app/main.py` (gắn router users)
- Create: `src/backend/tests/test_rbac_users.py`

**Interfaces:**
- Consumes: `deps.require_role`, `passwords.hash_password`, `audit.write_audit`, `app.models.User`.
- Produces: `POST /users` (tạo, 201), `GET /users` (liệt kê), `PATCH /users/{id}` (khóa qua `active`, đổi vai, đặt lại mật khẩu). Tất cả yêu cầu vai `admin`. Schema `UserCreate`, `UserUpdate`, `UserOut`.

- [ ] **Step 1: Viết schemas/user.py**

```python
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # staff | admin


class UserUpdate(BaseModel):
    active: bool | None = None
    role: str | None = None
    password: str | None = None


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    active: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Viết test thất bại cho RBAC và CRUD**

`src/backend/tests/test_rbac_users.py`:

```python
def _token(client, username, password):
    return client.post("/auth/login", json={"username": username, "password": password}).json()["access_token"]


def test_no_token_rejected(client):
    assert client.get("/users").status_code in (401, 403)


def test_staff_cannot_access_users(client, make_user):
    make_user(username="staff1", password="pw", role="staff")
    token = _token(client, "staff1", "pw")
    r = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_admin_crud_and_lock(client, make_user):
    make_user(username="admin1", password="pw", role="admin")
    h = {"Authorization": f"Bearer {_token(client, 'admin1', 'pw')}"}

    r = client.post("/users", json={"username": "newstaff", "password": "pw2", "role": "staff"}, headers=h)
    assert r.status_code == 201
    new_id = r.json()["id"]

    r = client.get("/users", headers=h)
    assert len(r.json()) == 2

    assert client.post("/auth/login", json={"username": "newstaff", "password": "pw2"}).status_code == 200

    r = client.patch(f"/users/{new_id}", json={"active": False}, headers=h)
    assert r.status_code == 200 and r.json()["active"] is False

    assert client.post("/auth/login", json={"username": "newstaff", "password": "pw2"}).status_code == 401
```

- [ ] **Step 3: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_rbac_users.py -v`
Expected: FAIL vì route `/users` chưa tồn tại (404 hoặc lỗi import).

- [ ] **Step 4: Viết routers/users.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_role
from app.models import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.security.passwords import hash_password
from app.services.audit import write_audit

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_role("admin")
_ROLES = ("staff", "admin")


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> User:
    if body.role not in _ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "role không hợp lệ")
    if db.scalars(select(User).where(User.username == body.username)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "username đã tồn tại")
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role, active=True)
    db.add(user)
    db.flush()
    write_audit(db, user_id=admin.id, action="create_user", entity_type="user", entity_id=str(user.id))
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy user")
    changed: list[str] = []
    if body.active is not None:
        user.active = body.active
        changed.append("active")
    if body.role is not None:
        if body.role not in _ROLES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "role không hợp lệ")
        user.role = body.role
        changed.append("role")
    if body.password is not None:
        user.password_hash = hash_password(body.password)
        changed.append("password")
    write_audit(db, user_id=admin.id, action="update_user", entity_type="user", entity_id=str(user.id), detail=",".join(changed))
    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Step 5: Gắn router users vào main.py**

Sửa `src/backend/app/main.py`:

```python
from fastapi import FastAPI

from app.routers import auth, users


def create_app() -> FastAPI:
    app = FastAPI(title="Parking backend")
    app.include_router(auth.router)
    app.include_router(users.router)
    return app


app = create_app()
```

- [ ] **Step 6: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_rbac_users.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/backend/app/schemas/user.py src/backend/app/routers/users.py src/backend/app/main.py src/backend/tests/test_rbac_users.py
git commit -m "feat(backend): admin user CRUD with role guard and audit"
```

---

### Task 5: Test nghiệm thu Phase 2

Kiểm chứng deliverable cả phase: admin đăng nhập, tạo staff, staff đăng nhập bị chặn route admin, và audit ghi đủ `login` cộng `create_user`.

**Files:**
- Create: `src/backend/tests/test_phase2_acceptance.py`

**Interfaces:**
- Consumes: endpoint `POST /auth/login`, `POST /users`, `GET /users`; `app.models.AuditLog`.
- Produces: cổng nghiệm thu, không API mới.

- [ ] **Step 1: Viết test nghiệm thu**

`src/backend/tests/test_phase2_acceptance.py`:

```python
from sqlalchemy import func, select

from app.models import AuditLog


def test_end_to_end_auth_flow(client, make_user, db_session):
    make_user(username="root", password="rootpw", role="admin")

    r = client.post("/auth/login", json={"username": "root", "password": "rootpw"})
    assert r.status_code == 200
    ah = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post("/users", json={"username": "gate1", "password": "gatepw", "role": "staff"}, headers=ah)
    assert r.status_code == 201

    r = client.post("/auth/login", json={"username": "gate1", "password": "gatepw"})
    assert r.status_code == 200
    sh = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/users", headers=sh).status_code == 403

    logins = db_session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "login"))
    creates = db_session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "create_user"))
    assert logins == 2
    assert creates == 1
```

- [ ] **Step 2: Chạy test nghiệm thu**

Run: `cd src/backend && pytest tests/test_phase2_acceptance.py -v`
Expected: PASS.

- [ ] **Step 3: Chạy toàn bộ suite (Phase 1 cộng Phase 2)**

Run: `cd src/backend && pytest -v`
Expected: PASS toàn bộ, không lỗi và không skip.

- [ ] **Step 4: Commit (điểm mốc)**

```bash
git add src/backend/tests/test_phase2_acceptance.py
git commit -m "test(backend): phase 2 acceptance for auth, roles and audit"
```

---

## Self-Review (đã chạy khi soạn plan)

- **Spec coverage phase 2:** đăng nhập JWT và vai staff cộng admin (mục 9 spec) phủ Task 3 và 4; audit login và hành động admin (mục 9, 10) phủ Task 2 tới 4; băm mật khẩu và khóa từ env (mục 10) phủ Task 1; tạo và khóa và đổi mật khẩu tài khoản (mục cấu hình) phủ Task 4 `PATCH /users`.
- **Placeholder scan:** không có; mọi step có code hoặc lệnh cụ thể.
- **Type consistency:** `get_current_user` và `require_role` dùng nhất quán giữa deps, routers, test; `write_audit` chữ ký keyword giống nhau ở service và mọi caller; `TokenResponse` các trường `access_token`, `token_type`, `role` khớp giữa router và test; override key `get_db` là cùng function object của `app.db.get_db`.
- **Ghi chú kỹ thuật:** `HTTPBearer(auto_error=True)` trả 403 khi thiếu header, nên test không token chấp nhận 401 hoặc 403.

## Điểm nối sang Phase 3

Phase 3 dùng `create_app()`, `deps.get_current_user` và `require_role` để bảo vệ endpoint capture và ảnh, `write_audit` cho truy cập ảnh, và các fixture `client`, `make_user`, `db_session` trong conftest. Không sửa file phase 2 trừ khi mở rộng schema, khi đó thêm migration mới.
