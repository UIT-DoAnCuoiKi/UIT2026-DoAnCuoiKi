from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ParkingSession(Base):
    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    vehicle_group: Mapped[str] = mapped_column(String(16))
    vehicle_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # in_lot | pending_manual | completed | disputed

    entry_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entry_reading_id: Mapped[int | None] = mapped_column(ForeignKey("plate_reading.id"), nullable=True)
    exit_reading_id: Mapped[int | None] = mapped_column(ForeignKey("plate_reading.id"), nullable=True)

    fee_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_rule_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match_flag: Mapped[str | None] = mapped_column(String(16), nullable=True)  # exact | auto_corrected | manual

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
