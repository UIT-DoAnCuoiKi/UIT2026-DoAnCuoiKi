from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BarrierEvent(Base):
    __tablename__ = "barrier_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("device.id"), nullable=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("session.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(8))   # open | close
    mode: Mapped[str] = mapped_column(String(12))    # auto | manual | emergency
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
