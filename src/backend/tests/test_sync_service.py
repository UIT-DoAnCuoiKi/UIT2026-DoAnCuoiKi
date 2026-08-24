def _session(db, uuid="u-1", lot_id=1):
    from app.clock import now_utc
    from app.models import ParkingSession
    s = ParkingSession(uuid=uuid, lot_id=lot_id, plate_hash="h", plate_ciphertext="x",
                       vehicle_group="o_to_con", status="completed", entry_time=now_utc(),
                       exit_time=now_utc(), fee_amount=20000, match_flag="exact")
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_serialize_is_json_safe(db_session):
    import json
    from app.services.sync import serialize_session
    s = _session(db_session)
    payload = serialize_session(s)
    json.dumps(payload)  # không lỗi
    assert payload["uuid"] == "u-1"
    assert isinstance(payload["entry_time"], str)


def test_enqueue_and_batch_and_mark(db_session):
    from app.services.sync import enqueue_session, mark_synced, unsynced_batch
    s = _session(db_session)
    enqueue_session(db_session, s)
    batch = unsynced_batch(db_session)
    assert len(batch) == 1 and batch[0].entity_uuid == "u-1"
    mark_synced(db_session, [batch[0].id])
    assert unsynced_batch(db_session) == []


def test_upsert_is_idempotent(db_session):
    from app.services.sync import serialize_session, upsert_session_from_sync
    s = _session(db_session, uuid="u-9")
    payload = serialize_session(s)

    # giả lập tầng nhận: db mới
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db import Base
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    cloud = sessionmaker(bind=engine)()

    upsert_session_from_sync(cloud, payload)
    upsert_session_from_sync(cloud, payload)  # lần hai không tạo bản trùng
    from app.models import ParkingSession
    assert cloud.query(ParkingSession).filter(ParkingSession.uuid == "u-9").count() == 1
    cloud.close(); engine.dispose()
