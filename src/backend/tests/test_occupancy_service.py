def _add_in_lot(db, lot_id, zone_id=None, plate="h"):
    from app.models import ParkingSession
    db.add(ParkingSession(
        plate_hash=plate, plate_ciphertext="x", vehicle_group="o_to_con",
        status="in_lot", lot_id=lot_id, zone_id=zone_id,
    ))
    db.commit()


def test_lot_and_zone_occupancy_counts_only_in_lot(db_session):
    from app.models import ParkingLot, Zone
    from app.services.occupancy import lot_occupancy, zone_occupancy
    lot = ParkingLot(name="A", capacity=10)
    db_session.add(lot); db_session.commit(); db_session.refresh(lot)
    zone = Zone(lot_id=lot.id, name="Z1", capacity=5)
    db_session.add(zone); db_session.commit(); db_session.refresh(zone)

    _add_in_lot(db_session, lot.id, zone.id, "h1")
    _add_in_lot(db_session, lot.id, zone.id, "h2")
    # phiên đã hoàn tất không tính
    from app.models import ParkingSession
    db_session.add(ParkingSession(
        plate_hash="h3", plate_ciphertext="x", vehicle_group="o_to_con",
        status="completed", lot_id=lot.id, zone_id=zone.id,
    ))
    db_session.commit()

    assert lot_occupancy(db_session, lot.id) == 2
    assert zone_occupancy(db_session, zone.id) == 2


def test_lot_is_full_respects_capacity_and_unlimited(db_session):
    from app.models import ParkingLot
    from app.services.occupancy import lot_is_full
    limited = ParkingLot(name="L", capacity=1)
    unlimited = ParkingLot(name="U", capacity=0)
    db_session.add_all([limited, unlimited]); db_session.commit()
    db_session.refresh(limited); db_session.refresh(unlimited)

    assert lot_is_full(db_session, limited.id) is False
    _add_in_lot(db_session, limited.id, None, "h1")
    assert lot_is_full(db_session, limited.id) is True
    # capacity 0 nghĩa là không giới hạn
    _add_in_lot(db_session, unlimited.id, None, "h2")
    assert lot_is_full(db_session, unlimited.id) is False


def test_occupancy_report_shape(db_session):
    from app.models import ParkingLot, Zone
    from app.services.occupancy import occupancy_report
    lot = ParkingLot(name="A", capacity=4)
    db_session.add(lot); db_session.commit(); db_session.refresh(lot)
    zone = Zone(lot_id=lot.id, name="Z1", capacity=2)
    db_session.add(zone); db_session.commit(); db_session.refresh(zone)
    _add_in_lot(db_session, lot.id, zone.id, "h1")

    report = occupancy_report(db_session)
    row = next(r for r in report if r["lot_id"] == lot.id)
    assert row["occupancy"] == 1
    assert row["available"] == 3
    assert row["full"] is False
    z = row["zones"][0]
    assert z["zone_id"] == zone.id
    assert z["occupancy"] == 1
    assert z["available"] == 1
