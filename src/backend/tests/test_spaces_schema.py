def test_space_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401  đăng ký bảng
    for t in ("parking_lot", "floor", "zone"):
        assert t in Base.metadata.tables


def test_session_has_lot_and_zone_columns():
    from app.models import ParkingSession
    cols = ParkingSession.__table__.columns.keys()
    assert "lot_id" in cols
    assert "zone_id" in cols


def test_zone_floor_id_is_nullable():
    from app.models import Zone
    assert Zone.__table__.columns["floor_id"].nullable is True
