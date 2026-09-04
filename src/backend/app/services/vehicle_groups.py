_MAP = {
    "motorbike": "xe_may",
    "bicycle": "xe_may",
    "car": "o_to_con",
    "truck": "xe_tai",
    "bus": "xe_khach",
}


def group_for(vehicle_type: str | None) -> str | None:
    if vehicle_type is None:
        return None
    return _MAP.get(vehicle_type.lower())


DEFAULT_VEHICLE_GROUPS = [
    {"code": "xe_may", "display_name": "Xe máy", "sort_order": 1},
    {"code": "o_to_con", "display_name": "Ô tô con", "sort_order": 2},
    {"code": "xe_tai", "display_name": "Xe tải", "sort_order": 3},
    {"code": "xe_khach", "display_name": "Xe khách", "sort_order": 4},
    {"code": "unknown", "display_name": "Chưa xác định", "sort_order": 99},
]


def seed_default_vehicle_groups(db) -> int:
    """Seed danh mục nhóm mặc định. Idempotent: bỏ qua code đã tồn tại."""
    from sqlalchemy import select

    from app.models import VehicleGroup

    created = 0
    for row in DEFAULT_VEHICLE_GROUPS:
        exists = db.scalars(select(VehicleGroup).where(VehicleGroup.code == row["code"])).first()
        if exists is None:
            db.add(VehicleGroup(**row))
            created += 1
    db.commit()
    return created
