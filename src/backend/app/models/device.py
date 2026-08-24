from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Device(Base):
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("parking_lot.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))   # barrier | camera | led
    name: Mapped[str] = mapped_column(String(64))
    lane: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(8), default="online")  # online | offline
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
