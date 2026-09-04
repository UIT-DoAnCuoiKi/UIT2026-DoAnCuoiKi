from app.models import ImageAsset, PlateReading


def test_reading_can_link_a_plate_crop_asset(db_session):
    asset = ImageAsset(path="/x.enc", encrypted=True, sha256="a", direction="in")
    db_session.add(asset)
    db_session.flush()
    reading = PlateReading(
        capture_id="cap-crop", direction="in", review_state="confident",
        plate_crop_asset_id=asset.id,
    )
    db_session.add(reading)
    db_session.commit()
    db_session.refresh(reading)
    assert reading.plate_crop_asset_id == asset.id
