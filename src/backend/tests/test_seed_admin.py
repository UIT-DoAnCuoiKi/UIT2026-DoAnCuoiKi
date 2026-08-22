from sqlalchemy import select

from app.models import User
from scripts.seed_admin import seed_admin


def test_seed_creates_admin_once(db_session, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "admin_username", "root")
    monkeypatch.setattr(settings, "admin_password", "rootpw")

    assert seed_admin(db_session) is True
    admin = db_session.scalars(select(User).where(User.username == "root")).one()
    assert admin.role == "admin"

    assert seed_admin(db_session) is False  # idempotent


def test_seed_skips_without_password(db_session, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "admin_password", "")
    assert seed_admin(db_session) is False
