import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.models  # noqa: F401  đăng ký bảng


@pytest.fixture(scope="session", autouse=True)
def _test_keys():
    # gán khóa test thẳng vào singleton settings; crypto và plate đọc thuộc tính
    # này lúc gọi, nên mutate singleton mới có tác dụng (cache_clear không rebind).
    from app.config import settings
    settings.fernet_key = Fernet.generate_key().decode()
    settings.hmac_key = "test-hmac-key-do-not-use-in-prod"
    yield


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


@pytest.fixture()
def staff_headers(client, make_user):
    make_user(username="gate", password="pw", role="staff")
    token = client.post("/auth/login", json={"username": "gate", "password": "pw"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
