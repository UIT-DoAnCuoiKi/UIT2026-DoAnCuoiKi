from sqlalchemy import select

from app.models import VehicleGroup
from app.services.vehicle_groups import seed_default_vehicle_groups


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
