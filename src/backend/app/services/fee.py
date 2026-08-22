import math
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import to_naive
from app.models import PriceRule


def compute_fee(rule: PriceRule, entry_time: datetime, exit_time: datetime) -> tuple[int, dict]:
    if rule.mode == "flat":
        return rule.unit_price, {"mode": "flat", "unit_price": rule.unit_price}
    minutes = max(0.0, (to_naive(exit_time) - to_naive(entry_time)).total_seconds() / 60.0)
    blocks = max(1, math.ceil(minutes / rule.block_minutes))
    fee = blocks * rule.unit_price
    return fee, {
        "mode": "block",
        "unit_price": rule.unit_price,
        "block_minutes": rule.block_minutes,
        "blocks": blocks,
        "minutes": round(minutes, 2),
    }


def get_active_rule(db: Session, vehicle_group: str) -> PriceRule | None:
    return db.scalars(
        select(PriceRule)
        .where(PriceRule.vehicle_group == vehicle_group, PriceRule.active.is_(True))
        .order_by(PriceRule.updated_at.desc())
    ).first()
