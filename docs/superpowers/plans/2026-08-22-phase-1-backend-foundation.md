# Phase 1: Backend foundation và data layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dựng khung backend FastAPI, cấu hình từ biến môi trường, tầng dữ liệu PostgreSQL với 8 model, migration Alembic, và tiện ích mã hóa cộng chuẩn hóa biển, làm nền cho mọi phase sau.

**Architecture:** package `src/backend/app` chứa config, engine DB, model SQLAlchemy 2.0, tiện ích bảo mật. Test chạy trên SQLite in memory cho nhanh vì mã hóa và hash ở tầng ứng dụng, không phụ thuộc Postgres. Runtime và migration dùng PostgreSQL.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 sync, Alembic, psycopg2, pydantic-settings, cryptography (Fernet), pytest.

## Global Constraints

Xem `2026-08-22-dashboard-mvp-plan-index.md` mục Global Constraints. Riêng phase này quan tâm: mã hóa tầng cột khóa từ env; nhóm xe `xe_may`, `o_to_con`, `xe_tai`, `xe_khach`; `capture_id` UNIQUE; `review_state` bốn giá trị; quy tắc commit chờ người dùng.

## File Structure

- Create: `src/backend/requirements.txt` phụ thuộc backend.
- Create: `src/backend/app/__init__.py` package marker.
- Create: `src/backend/app/config.py` Settings đọc env.
- Create: `src/backend/app/db.py` Base, engine, SessionLocal, get_db.
- Create: `src/backend/app/security/__init__.py`.
- Create: `src/backend/app/security/crypto.py` mã hóa Fernet cho text và bytes.
- Create: `src/backend/app/security/plate.py` chuẩn hóa biển và HMAC hash.
- Create: `src/backend/app/models/__init__.py` gom import 8 model để đăng ký vào `Base.metadata` và bày tên cho phase sau.
- Create: `src/backend/app/models/user.py`, `price_rule.py`, `parking_session.py`, `plate_reading.py`, `image_asset.py`, `audit_log.py`, `lane.py`, `feature_toggle.py`.
- Create: `src/backend/alembic.ini`, `src/backend/alembic/env.py`, thư mục `src/backend/alembic/versions/`.
- Create: `src/backend/tests/conftest.py`, `test_crypto.py`, `test_plate.py`, `test_models_schema.py`.

---

### Task 1: Scaffold package và cấu hình env

**Files:**
- Create: `src/backend/requirements.txt`
- Create: `src/backend/app/__init__.py`
- Create: `src/backend/app/config.py`
- Create: `src/backend/tests/conftest.py`

**Interfaces:**
- Produces: `app.config.Settings` với thuộc tính `database_url: str`, `fernet_key: str`, `hmac_key: str`, `jwt_secret: str`, `jwt_expire_minutes: int`, `image_storage_dir: str`, `retention_days: int`. Instance dùng chung `app.config.settings`.

- [ ] **Step 1: Viết requirements.txt**

```
fastapi==0.115.*
uvicorn[standard]==0.30.*
SQLAlchemy==2.0.*
alembic==1.13.*
psycopg2-binary==2.9.*
pydantic==2.*
pydantic-settings==2.*
cryptography==43.*
bcrypt>=4.1,<6
PyJWT==2.9.*
python-multipart==0.0.*
pytest==8.*
httpx==0.27.*
```

- [ ] **Step 2: Tạo package marker**

`src/backend/app/__init__.py`: file rỗng.

- [ ] **Step 3: Viết config.py**

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://parking:parking@localhost:5432/parking"
    fernet_key: str = ""          # bắt buộc set ở runtime, sinh bằng Fernet.generate_key()
    hmac_key: str = ""            # bắt buộc set ở runtime
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 480
    image_storage_dir: str = "./data/images"
    retention_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 4: Viết conftest.py đặt khóa test**

Gán khóa thẳng vào singleton `settings`; `crypto` và `plate` đọc thuộc tính lúc gọi, nên phải mutate singleton (chỉ `cache_clear` không rebind object đã import).

```python
import pytest
from cryptography.fernet import Fernet


@pytest.fixture(scope="session", autouse=True)
def _test_keys():
    from app.config import settings
    settings.fernet_key = Fernet.generate_key().decode()
    settings.hmac_key = "test-hmac-key-do-not-use-in-prod"
    yield
```

- [ ] **Step 5: Tạo file cấu hình pytest**

`src/backend/pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 6: Xác minh cài đặt và import config**

Run: `cd src/backend && python -m pip install -r requirements.txt && python -c "from app.config import settings; print(settings.retention_days)"`
Expected: in ra `30`, không lỗi import.

- [ ] **Step 7: Commit (điểm mốc, chờ người dùng)**

```bash
git add src/backend/requirements.txt src/backend/app/__init__.py src/backend/app/config.py src/backend/tests/conftest.py src/backend/pytest.ini
git commit -m "chore(backend): scaffold package and env config"
```

---

### Task 2: Tiện ích mã hóa Fernet

**Files:**
- Create: `src/backend/app/security/__init__.py`
- Create: `src/backend/app/security/crypto.py`
- Create: `src/backend/tests/test_crypto.py`

**Interfaces:**
- Consumes: `app.config.settings.fernet_key`.
- Produces: `encrypt_text(plaintext: str) -> str`, `decrypt_text(token: str) -> str`, `encrypt_bytes(data: bytes) -> bytes`, `decrypt_bytes(token: bytes) -> bytes` trong `app.security.crypto`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_crypto.py`:

```python
from app.security import crypto


def test_text_round_trip():
    token = crypto.encrypt_text("51F-123.45")
    assert token != "51F-123.45"
    assert crypto.decrypt_text(token) == "51F-123.45"


def test_bytes_round_trip():
    data = b"\x89PNG fake image bytes"
    token = crypto.encrypt_bytes(data)
    assert token != data
    assert crypto.decrypt_bytes(token) == data
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd src/backend && pytest tests/test_crypto.py -v`
Expected: FAIL với `ModuleNotFoundError` hoặc `AttributeError` vì `crypto` chưa có.

- [ ] **Step 3: Tạo package marker security**

`src/backend/app/security/__init__.py`: file rỗng.

- [ ] **Step 4: Viết crypto.py**

```python
from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    if not settings.fernet_key:
        raise RuntimeError("FERNET_KEY chưa được cấu hình")
    return Fernet(settings.fernet_key.encode())


def encrypt_text(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_text(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _fernet().decrypt(token)
```

- [ ] **Step 5: Chạy test để xác nhận pass**

Run: `cd src/backend && pytest tests/test_crypto.py -v`
Expected: PASS cả hai test.

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add src/backend/app/security/__init__.py src/backend/app/security/crypto.py src/backend/tests/test_crypto.py
git commit -m "feat(backend): column-level Fernet encryption utility"
```

---

### Task 3: Chuẩn hóa biển và HMAC hash

**Files:**
- Create: `src/backend/app/security/plate.py`
- Create: `src/backend/tests/test_plate.py`

**Interfaces:**
- Consumes: `app.config.settings.hmac_key`.
- Produces: `normalize_plate(raw: str) -> str`, `plate_hash(raw: str) -> str` (hex sha256) trong `app.security.plate`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_plate.py`:

```python
from app.security import plate


def test_normalize_strips_separators_and_uppercases():
    assert plate.normalize_plate("51f-123.45") == "51F12345"
    assert plate.normalize_plate("  30A 678.90 ") == "30A67890"


def test_hash_is_deterministic_over_normalization():
    assert plate.plate_hash("51F-123.45") == plate.plate_hash("51f 123 45")


def test_hash_differs_for_different_plates():
    assert plate.plate_hash("51F-123.45") != plate.plate_hash("51F-123.46")
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd src/backend && pytest tests/test_plate.py -v`
Expected: FAIL vì `app.security.plate` chưa có.

- [ ] **Step 3: Viết plate.py**

```python
import hashlib
import hmac
import re

from app.config import settings

_NON_ALNUM = re.compile(r"[^A-Z0-9]")


def normalize_plate(raw: str) -> str:
    return _NON_ALNUM.sub("", raw.upper())


def plate_hash(raw: str) -> str:
    norm = normalize_plate(raw)
    return hmac.new(settings.hmac_key.encode(), norm.encode(), hashlib.sha256).hexdigest()
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `cd src/backend && pytest tests/test_plate.py -v`
Expected: PASS cả ba test.

- [ ] **Step 5: Commit (điểm mốc)**

```bash
git add src/backend/app/security/plate.py src/backend/tests/test_plate.py
git commit -m "feat(backend): plate normalization and HMAC hash for matching"
```

---

### Task 4: DB base, engine, session

**Files:**
- Create: `src/backend/app/db.py`

**Interfaces:**
- Consumes: `app.config.settings.database_url`.
- Produces: `app.db.Base` (DeclarativeBase), `app.db.engine`, `app.db.SessionLocal`, `app.db.get_db()` (generator yield một `Session`).

- [ ] **Step 1: Viết db.py**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Xác minh import không lỗi**

Run: `cd src/backend && python -c "from app.db import Base, engine, SessionLocal, get_db; print('ok')"`
Expected: in ra `ok`.

- [ ] **Step 3: Commit (điểm mốc)**

```bash
git add src/backend/app/db.py
git commit -m "feat(backend): SQLAlchemy base, engine and session factory"
```

---

### Task 5: Tám model SQLAlchemy

**Files:**
- Create: `src/backend/app/models/__init__.py`
- Create: `src/backend/app/models/user.py`
- Create: `src/backend/app/models/price_rule.py`
- Create: `src/backend/app/models/parking_session.py`
- Create: `src/backend/app/models/plate_reading.py`
- Create: `src/backend/app/models/image_asset.py`
- Create: `src/backend/app/models/audit_log.py`
- Create: `src/backend/app/models/lane.py`
- Create: `src/backend/app/models/feature_toggle.py`
- Create: `src/backend/tests/test_models_schema.py`

**Interfaces:**
- Consumes: `app.db.Base`.
- Produces: các lớp `User`, `PriceRule`, `ParkingSession` (bảng `session`), `PlateReading`, `ImageAsset`, `AuditLog`, `Lane`, `FeatureToggle`. `app.models` export tất cả và `Base.metadata` chứa đủ 8 bảng: `users`, `price_rule`, `session`, `plate_reading`, `image_asset`, `audit_log`, `lane`, `feature_toggle`.

- [ ] **Step 1: Viết test thất bại**

`src/backend/tests/test_models_schema.py`:

```python
from sqlalchemy import create_engine

from app.db import Base
import app.models  # noqa: F401  đăng ký toàn bộ bảng


EXPECTED = {
    "users", "price_rule", "session", "plate_reading",
    "image_asset", "audit_log", "lane", "feature_toggle",
}


def test_metadata_has_all_tables():
    assert EXPECTED.issubset(set(Base.metadata.tables.keys()))


def test_create_all_on_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    insp_tables = set(Base.metadata.tables.keys())
    assert EXPECTED.issubset(insp_tables)


def test_plate_reading_capture_id_unique():
    col = Base.metadata.tables["plate_reading"].c.capture_id
    assert col.unique is True
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd src/backend && pytest tests/test_models_schema.py -v`
Expected: FAIL vì `app.models` chưa có.

- [ ] **Step 3: Viết model user.py**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))  # staff | admin
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Viết model price_rule.py**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PriceRule(Base):
    __tablename__ = "price_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_group: Mapped[str] = mapped_column(String(16))  # xe_may | o_to_con | xe_tai | xe_khach
    mode: Mapped[str] = mapped_column(String(8))            # flat | block
    unit_price: Mapped[int] = mapped_column(Integer)        # VND
    block_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 5: Viết model image_asset.py**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ImageAsset(Base):
    __tablename__ = "image_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(512))
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    sha256: Mapped[str] = mapped_column(String(64))
    direction: Mapped[str | None] = mapped_column(String(4), nullable=True)  # in | out
    retention_delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 6: Viết model plate_reading.py**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PlateReading(Base):
    __tablename__ = "plate_reading"

    id: Mapped[int] = mapped_column(primary_key=True)
    capture_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(4))  # in | out
    lane: Mapped[str | None] = mapped_column(String(32), nullable=True)

    plate_text_ciphertext: Mapped[str | None] = mapped_column(String(512), nullable=True)
    plate_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    plate_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    det_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    layout: Mapped[str | None] = mapped_column(String(8), nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    color_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vehicle_style: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vehicle_style_conf: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_pipeline_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_asset_id: Mapped[int | None] = mapped_column(ForeignKey("image_asset.id"), nullable=True)
    review_state: Mapped[str] = mapped_column(String(16))  # confident | needs_review | disputed | manual
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 7: Viết model parking_session.py**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ParkingSession(Base):
    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    vehicle_group: Mapped[str] = mapped_column(String(16))
    vehicle_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # in_lot | pending_manual | completed | disputed

    entry_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entry_reading_id: Mapped[int | None] = mapped_column(ForeignKey("plate_reading.id"), nullable=True)
    exit_reading_id: Mapped[int | None] = mapped_column(ForeignKey("plate_reading.id"), nullable=True)

    fee_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_rule_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match_flag: Mapped[str | None] = mapped_column(String(16), nullable=True)  # exact | auto_corrected | manual

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 8: Viết model audit_log.py**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(32))  # login | view_image | edit_plate | delete | ...
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 9: Viết model lane.py**

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lane(Base):
    __tablename__ = "lane"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    rtsp_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 10: Viết model feature_toggle.py**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FeatureToggle(Base):
    __tablename__ = "feature_toggle"

    id: Mapped[int] = mapped_column(primary_key=True)
    read_plate: Mapped[bool] = mapped_column(Boolean, default=True)
    plate_color: Mapped[bool] = mapped_column(Boolean, default=True)
    vehicle_class: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 11: Viết models/__init__.py export tất cả**

```python
from app.models.audit_log import AuditLog
from app.models.feature_toggle import FeatureToggle
from app.models.image_asset import ImageAsset
from app.models.lane import Lane
from app.models.parking_session import ParkingSession
from app.models.plate_reading import PlateReading
from app.models.price_rule import PriceRule
from app.models.user import User

__all__ = [
    "AuditLog", "FeatureToggle", "ImageAsset", "Lane",
    "ParkingSession", "PlateReading", "PriceRule", "User",
]
```

- [ ] **Step 12: Chạy test để xác nhận pass**

Run: `cd src/backend && pytest tests/test_models_schema.py -v`
Expected: PASS cả ba test.

- [ ] **Step 13: Commit (điểm mốc)**

```bash
git add src/backend/app/models
git add src/backend/tests/test_models_schema.py
git commit -m "feat(backend): SQLAlchemy models for eight core tables"
```

---

### Task 6: Alembic migration tạo schema

**Files:**
- Create: `src/backend/alembic.ini`
- Create: `src/backend/alembic/env.py`
- Create: `src/backend/alembic/script.py.mako`
- Create: `src/backend/alembic/versions/` (thư mục, giữ bằng `.gitkeep`)
- Create: migration đầu tiên trong `src/backend/alembic/versions/` do autogenerate sinh

**Interfaces:**
- Consumes: `app.db.Base.metadata`, `app.config.settings.database_url`, `app.models`.
- Produces: một revision Alembic tạo đủ 8 bảng; lệnh `alembic upgrade head` chạy được trên PostgreSQL.

- [ ] **Step 1: Khởi tạo bộ khung Alembic**

Run: `cd src/backend && alembic init alembic`
Expected: tạo `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2: Trỏ alembic.ini sang URL từ env (bỏ URL hardcode)**

Trong `src/backend/alembic.ini`, đặt dòng `sqlalchemy.url` rỗng:

```ini
sqlalchemy.url =
```

- [ ] **Step 3: Sửa alembic/env.py nạp metadata và URL từ app**

Thay phần đầu và hàm run của `src/backend/alembic/env.py` bằng:

```python
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from app.config import settings
from app.db import Base
import app.models  # noqa: F401  đăng ký bảng

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Giữ thư mục versions trong git**

Tạo `src/backend/alembic/versions/.gitkeep` rỗng.

- [ ] **Step 5: Chuẩn bị Postgres để autogenerate và migrate**

Run: `podman run --name parking-pg -e POSTGRES_USER=parking -e POSTGRES_PASSWORD=parking -e POSTGRES_DB=parking -p 5432:5432 -d postgres:16`
Expected: container chạy; `settings.database_url` mặc định trỏ đúng DB này.

- [ ] **Step 6: Sinh migration đầu tiên**

Run: `cd src/backend && FERNET_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())") HMAC_KEY=x alembic revision --autogenerate -m "create core tables"`
Expected: tạo một file revision trong `alembic/versions/` chứa `op.create_table` cho 8 bảng.

- [ ] **Step 7: Áp migration**

Run: `cd src/backend && FERNET_KEY=x HMAC_KEY=x alembic upgrade head`
Expected: kết thúc không lỗi; log `Running upgrade -> <rev>, create core tables`.

- [ ] **Step 8: Xác minh 8 bảng tồn tại trong Postgres**

Run: `podman exec parking-pg psql -U parking -d parking -c "\dt"`
Expected: liệt kê `users`, `price_rule`, `session`, `plate_reading`, `image_asset`, `audit_log`, `lane`, `feature_toggle`, cộng `alembic_version`.

- [ ] **Step 9: Commit (điểm mốc)**

```bash
git add src/backend/alembic.ini src/backend/alembic/env.py src/backend/alembic/script.py.mako src/backend/alembic/versions
git commit -m "feat(backend): alembic migration creating core schema"
```

---

### Task 7: Test nghiệm thu Phase 1

Kiểm chứng deliverable của cả phase: mã hóa, hash biển, và schema hoạt động cùng nhau; lưu một `PlateReading` với biển mã hóa rồi tra khớp bằng hash; ràng buộc `capture_id` UNIQUE có hiệu lực.

**Files:**
- Create: `src/backend/tests/test_phase1_acceptance.py`

**Interfaces:**
- Consumes: `app.db.Base`, `app.models`, `app.security.crypto`, `app.security.plate`.
- Produces: không có API mới; đây là cổng nghiệm thu.

- [ ] **Step 1: Viết test nghiệm thu**

`src/backend/tests/test_phase1_acceptance.py`:

```python
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
import app.models as m
from app.security import crypto, plate


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_store_encrypted_plate_then_match_by_hash():
    db = _session()
    raw = "51F-123.45"
    db.add(m.PlateReading(
        capture_id="cap-1",
        direction="in",
        plate_text_ciphertext=crypto.encrypt_text(raw),
        plate_hash=plate.plate_hash(raw),
        review_state="confident",
    ))
    db.commit()

    # biển đọc lại viết khác cách nhưng cùng biển, phải khớp qua hash
    q = select(m.PlateReading).where(m.PlateReading.plate_hash == plate.plate_hash("51f 123 45"))
    found = db.scalars(q).one()
    assert crypto.decrypt_text(found.plate_text_ciphertext) == raw


def test_capture_id_uniqueness_enforced():
    db = _session()
    db.add(m.PlateReading(capture_id="dup", direction="in", review_state="manual"))
    db.commit()
    db.add(m.PlateReading(capture_id="dup", direction="out", review_state="manual"))
    with pytest.raises(IntegrityError):
        db.commit()
```

- [ ] **Step 2: Chạy test nghiệm thu**

Run: `cd src/backend && pytest tests/test_phase1_acceptance.py -v`
Expected: PASS cả hai test.

- [ ] **Step 3: Chạy toàn bộ suite phase 1**

Run: `cd src/backend && pytest -v`
Expected: PASS toàn bộ (`test_crypto`, `test_plate`, `test_models_schema`, `test_phase1_acceptance`), không lỗi và không skip.

- [ ] **Step 4: Commit (điểm mốc)**

```bash
git add src/backend/tests/test_phase1_acceptance.py
git commit -m "test(backend): phase 1 acceptance for encrypted storage and hash matching"
```

---

## Self-Review (đã chạy khi soạn plan)

- **Spec coverage phase 1:** schema 8 bảng (mục 3 spec) phủ ở Task 5; mã hóa tầng cột (mục 10) phủ ở Task 2; `plate_hash` chuẩn hóa (mục 3) phủ ở Task 3; trạng thái `session` và `capture_id` UNIQUE và `review_state` phủ trong model Task 5; khóa từ env (mục 10) phủ ở Task 1 và 2. Config `retention_days = 30` ở Task 1.
- **Placeholder scan:** không có TODO hay mô tả trống; mọi step có code hoặc lệnh cụ thể.
- **Type consistency:** tên lớp `ParkingSession` bảng `session`, `PlateReading.capture_id` UNIQUE, `review_state` bốn giá trị, nhóm xe bốn giá trị dùng nhất quán; `plate_hash(raw)` một tham số dùng cùng chữ ký ở test và impl.

## Điểm nối sang Phase 2

Phase 2 dùng `app.db.Base`, `app.db.get_db`, `app.models.User`, `app.models.AuditLog`, và `app.config.settings.jwt_secret` cộng `jwt_expire_minutes`. Không sửa file phase 1 trừ khi thêm cột, khi đó thêm migration Alembic mới.
