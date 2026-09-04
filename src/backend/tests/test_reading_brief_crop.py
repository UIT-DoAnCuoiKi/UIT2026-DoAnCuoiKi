from app.models import ImageAsset, PlateReading
from app.routers.sessions import _reading_brief


def test_reading_brief_includes_plate_crop_asset_id(db_session):
    origin = ImageAsset(path="/o.enc", encrypted=True, sha256="o", direction="in")
    crop = ImageAsset(path="/c.enc", encrypted=True, sha256="c", direction="in")
    db_session.add_all([origin, crop])
    db_session.flush()
    reading = PlateReading(
        capture_id="cap-brief", direction="in", review_state="confident",
        image_asset_id=origin.id, plate_crop_asset_id=crop.id,
    )
    db_session.add(reading)
    db_session.flush()

    brief = _reading_brief(db_session, reading.id)
    assert brief.plate_crop_asset_id == crop.id
    assert brief.image_asset_id == origin.id
