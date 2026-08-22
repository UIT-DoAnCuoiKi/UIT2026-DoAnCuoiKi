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
