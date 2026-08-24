from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PlateWhitelist(Base):
    __tablename__ = "plate_whitelist"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlateBlacklist(Base):
    __tablename__ = "plate_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
