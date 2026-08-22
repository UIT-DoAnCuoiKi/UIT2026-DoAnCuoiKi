from sqlalchemy import create_engine

from app.db import Base
import app.models  # noqa: F401  đăng ký toàn bộ bảng


EXPECTED = {
    "users", "price_rule", "session", "plate_reading",
    "image_asset", "audit_log", "lane", "feature_toggle",
}


def test_metadata_has_all_tables():
    assert EXPECTED.issubset(set(Base.metadata.tables.keys()))


def test_create_all_on_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    insp_tables = set(Base.metadata.tables.keys())
    assert EXPECTED.issubset(insp_tables)


def test_plate_reading_capture_id_unique():
    col = Base.metadata.tables["plate_reading"].c.capture_id
    assert col.unique is True
