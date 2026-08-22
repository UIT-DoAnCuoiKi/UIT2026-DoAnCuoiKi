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
