from sqlalchemy import select

from app.models import User
from scripts.migrate_admin_to_root import migrate_admin_to_root


def _token(client, make_user, username, role):
    make_user(username=username, password="pw", role=role)
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["access_token"]


def test_staff_cannot_get_stats(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'gate', 'staff')}"}
    assert client.get("/stats", headers=h).status_code == 403


def test_manager_can_get_stats(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'mgr', 'manager')}"}
    assert client.get("/stats", headers=h).status_code == 200


def test_manager_cannot_crud_users(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'mgr', 'manager')}"}
    assert client.get("/users", headers=h).status_code == 403


def test_root_can_crud_users(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'boss', 'root')}"}
    r = client.post("/users", json={"username": "s1", "password": "pw", "role": "staff"}, headers=h)
    assert r.status_code == 201


def test_manager_can_configure(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'mgr', 'manager')}"}
    r = client.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=h)
    assert r.status_code == 201


def test_migrate_admin_to_root(db_session, make_user):
    make_user(username="old", password="pw", role="admin")
    n = migrate_admin_to_root(db_session)
    assert n == 1
    assert db_session.scalars(select(User).where(User.username == "old")).one().role == "root"
