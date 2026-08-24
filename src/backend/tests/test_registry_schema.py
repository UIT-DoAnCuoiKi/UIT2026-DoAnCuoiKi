def test_registry_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401
    for t in ("vehicle_owner", "monthly_pass", "plate_whitelist", "plate_blacklist"):
        assert t in Base.metadata.tables


def test_monthly_pass_columns():
    from app.models import MonthlyPass
    cols = MonthlyPass.__table__.columns.keys()
    for c in ("plate_hash", "plate_ciphertext", "vehicle_group", "start_date", "end_date", "active"):
        assert c in cols
