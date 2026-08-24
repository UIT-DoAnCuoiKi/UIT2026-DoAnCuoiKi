def test_new_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401
    for t in ("device", "barrier_event", "incident"):
        assert t in Base.metadata.tables


def test_device_columns():
    from app.models import Device
    cols = Device.__table__.columns.keys()
    for c in ("lot_id", "kind", "name", "status", "last_heartbeat"):
        assert c in cols


def test_barrier_and_incident_columns():
    from app.models import BarrierEvent, Incident
    for c in ("action", "mode", "reason", "user_id"):
        assert c in BarrierEvent.__table__.columns.keys()
    for c in ("kind", "description", "image_asset_id", "user_id"):
        assert c in Incident.__table__.columns.keys()
