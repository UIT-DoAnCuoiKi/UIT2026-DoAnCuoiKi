from datetime import datetime, timedelta

from app.models import PriceRule
from app.services.fee import compute_fee, get_active_rule


def test_flat_fee_ignores_duration():
    rule = PriceRule(vehicle_group="xe_may", mode="flat", unit_price=3000, active=True)
    entry = datetime(2026, 8, 22, 8, 0, 0)
    fee, snap = compute_fee(rule, entry, entry + timedelta(hours=5))
    assert fee == 3000
    assert snap["mode"] == "flat"


def test_block_fee_rounds_up():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True)
    entry = datetime(2026, 8, 22, 8, 0, 0)
    fee, snap = compute_fee(rule, entry, entry + timedelta(minutes=90))
    assert fee == 10000  # ceil(1.5) = 2 block
    assert snap["blocks"] == 2


def test_block_minimum_one():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True)
    entry = datetime(2026, 8, 22, 8, 0, 0)
    fee, snap = compute_fee(rule, entry, entry)  # 0 phút
    assert fee == 5000
    assert snap["blocks"] == 1


def test_get_active_rule(db_session):
    db_session.add_all([
        PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60, active=True),
        PriceRule(vehicle_group="o_to_con", mode="block", unit_price=1000, block_minutes=60, active=False),
    ])
    db_session.commit()
    rule = get_active_rule(db_session, "o_to_con")
    assert rule is not None and rule.unit_price == 5000
    assert get_active_rule(db_session, "xe_tai") is None
