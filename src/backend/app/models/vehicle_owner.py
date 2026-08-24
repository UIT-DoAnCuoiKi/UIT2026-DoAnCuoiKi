from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class VehicleOwner(Base):
    __tablename__ = "vehicle_owner"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plate_hash: Mapped[str] = mapped_column(String(64), index=True)
    plate_ciphertext: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
