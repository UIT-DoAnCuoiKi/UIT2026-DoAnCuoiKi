from sqlalchemy import select

from app.models import VehicleGroup
from app.services.vehicle_groups import seed_default_vehicle_groups


def _token(client, make_user, role):
    make_user(username=role, password="pw", role=role)
    return client.post("/auth/login", json={"username": role, "password": "pw"}).json()["access_token"]


def _seed(client):
    # client và db_session dùng chung engine (conftest override get_db)
    from app.services.vehicle_groups import seed_default_vehicle_groups
    from app.deps import get_db

    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    seed_default_vehicle_groups(db)


def test_seed_creates_five_groups(db_session):
    created = seed_default_vehicle_groups(db_session)
    assert created == 5
    codes = set(db_session.scalars(select(VehicleGroup.code)).all())
    assert codes == {"xe_may", "o_to_con", "xe_tai", "xe_khach", "unknown"}
    xe_may = db_session.scalars(select(VehicleGroup).where(VehicleGroup.code == "xe_may")).one()
    assert xe_may.display_name == "Xe máy"


def test_seed_is_idempotent(db_session):
    seed_default_vehicle_groups(db_session)
    again = seed_default_vehicle_groups(db_session)
    assert again == 0
    total = len(db_session.scalars(select(VehicleGroup)).all())
    assert total == 5


def test_list_vehicle_groups_any_user(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.get("/vehicle-groups", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert [g["code"] for g in body][:2] == ["xe_may", "o_to_con"]  # theo sort_order


def test_create_vehicle_group_manager(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'manager')}"}
    r = client.post("/vehicle-groups", json={"code": "xe_dien", "display_name": "Xe điện", "sort_order": 5}, headers=h)
    assert r.status_code == 201
    assert r.json()["display_name"] == "Xe điện"


def test_create_vehicle_group_staff_forbidden(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'staff')}"}
    r = client.post("/vehicle-groups", json={"code": "xe_dien", "display_name": "Xe điện"}, headers=h)
    assert r.status_code == 403


def test_create_duplicate_code_conflict(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
    r = client.post("/vehicle-groups", json={"code": "xe_may", "display_name": "Trùng"}, headers=h)
    assert r.status_code == 409


def test_patch_vehicle_group(client, make_user, db_session):
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(db_session)
    from app.models import VehicleGroup
    from sqlalchemy import select
    gid = db_session.scalars(select(VehicleGroup).where(VehicleGroup.code == "xe_tai")).one().id
    h = {"Authorization": f"Bearer {_token(client, make_user, 'manager')}"}
    r = client.patch(f"/vehicle-groups/{gid}", json={"display_name": "Xe tải nhẹ", "active": False}, headers=h)
    assert r.status_code == 200
    assert r.json()["display_name"] == "Xe tải nhẹ"
    assert r.json()["active"] is False
