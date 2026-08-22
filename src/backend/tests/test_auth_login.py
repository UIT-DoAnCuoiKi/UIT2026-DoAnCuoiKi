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
