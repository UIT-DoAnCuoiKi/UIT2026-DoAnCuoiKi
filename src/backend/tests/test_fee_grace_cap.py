from datetime import datetime

from app.models import PriceRule
from app.services.fee import compute_fee


def test_grace_period_makes_short_stay_free():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60)
    rule.grace_minutes = 15
    rule.daily_cap = None
    entry = datetime(2026, 8, 1, 8, 0)
    exit_ = datetime(2026, 8, 1, 8, 10)  # 10 phút, trong grace
    fee, snap = compute_fee(rule, entry, exit_)
    assert fee == 0
    assert snap["free"] is True


def test_daily_cap_limits_block_fee():
    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000, block_minutes=60)
    rule.grace_minutes = 0
    rule.daily_cap = 30000
    entry = datetime(2026, 8, 1, 0, 0)
    exit_ = datetime(2026, 8, 1, 20, 0)  # 20 giờ = 20 block * 5000 = 100000, trần 30000
    fee, snap = compute_fee(rule, entry, exit_)
    assert fee == 30000
    assert snap["capped"] is True


def test_no_grace_no_cap_unchanged():
    rule = PriceRule(vehicle_group="o_to_con", mode="flat", unit_price=10000)
    rule.grace_minutes = 0
    rule.daily_cap = None
    fee, snap = compute_fee(rule, datetime(2026, 8, 1, 8, 0), datetime(2026, 8, 1, 9, 0))
    assert fee == 10000
    assert snap["mode"] == "flat"
