from datetime import date, timedelta


def _add_pass(db, ph, start, end, active=True):
    from app.models import MonthlyPass
    db.add(MonthlyPass(plate_hash=ph, plate_ciphertext="x", vehicle_group="o_to_con",
                       start_date=start, end_date=end, active=active))
    db.commit()


def test_has_valid_pass_within_window(db_session):
    from app.services.registry import has_valid_pass
    today = date(2026, 8, 15)
    _add_pass(db_session, "ph1", today - timedelta(days=5), today + timedelta(days=5))
    assert has_valid_pass(db_session, "ph1", on=today) is True
    assert has_valid_pass(db_session, "ph1", on=today + timedelta(days=10)) is False


def test_inactive_pass_not_valid(db_session):
    from app.services.registry import has_valid_pass
    today = date(2026, 8, 15)
    _add_pass(db_session, "ph2", today, today + timedelta(days=30), active=False)
    assert has_valid_pass(db_session, "ph2", on=today) is False


def test_whitelist_and_blacklist_and_exempt(db_session):
    from app.models import PlateBlacklist, PlateWhitelist
    from app.services.registry import is_blacklisted, is_exempt, is_whitelisted
    db_session.add(PlateWhitelist(plate_hash="wh", plate_ciphertext="x", active=True))
    db_session.add(PlateBlacklist(plate_hash="bl", plate_ciphertext="x", active=True))
    db_session.commit()
    assert is_whitelisted(db_session, "wh") is True
    assert is_exempt(db_session, "wh") is True
    assert is_blacklisted(db_session, "bl") is True
    assert is_exempt(db_session, "bl") is False
