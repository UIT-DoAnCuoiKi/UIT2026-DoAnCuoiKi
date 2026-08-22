from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PriceRule(Base):
    __tablename__ = "price_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_group: Mapped[str] = mapped_column(String(16))  # xe_may | o_to_con | xe_tai | xe_khach
    mode: Mapped[str] = mapped_column(String(8))            # flat | block
    unit_price: Mapped[int] = mapped_column(Integer)        # VND
    block_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
