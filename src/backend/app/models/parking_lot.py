from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ParkingLot(Base):
    __tablename__ = "parking_lot"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=0)  # 0 = không giới hạn
    active: Mapped[bool] = mapped_column(Boolean, default=True)
