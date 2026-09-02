from app.clock import now_utc
from app.models import ImageAsset, PlateReading, ParkingSession
from app.routers.sessions import _set_retention


def test_set_retention_marks_crop_asset(db_session):
    origin = ImageAsset(path="/o.enc", encrypted=True, sha256="o", direction="out")
    crop = ImageAsset(path="/c.enc", encrypted=True, sha256="c", direction="out")
    db_session.add_all([origin, crop])
    db_session.flush()
    reading = PlateReading(
        capture_id="cap-ret", direction="out", review_state="confident",
        image_asset_id=origin.id, plate_crop_asset_id=crop.id,
    )
    db_session.add(reading)
    db_session.flush()
    session = ParkingSession(
        plate_hash="h", plate_ciphertext="x", vehicle_group="xe_may",
        status="completed", exit_time=now_utc(), exit_reading_id=reading.id,
    )
    db_session.add(session)
    db_session.flush()

    _set_retention(db_session, session)

    assert db_session.get(ImageAsset, crop.id).retention_delete_after is not None
    assert db_session.get(ImageAsset, origin.id).retention_delete_after is not None
