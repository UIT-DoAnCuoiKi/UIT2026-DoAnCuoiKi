from datetime import datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FeatureToggle(Base):
    __tablename__ = "feature_toggle"

    id: Mapped[int] = mapped_column(primary_key=True)
    read_plate: Mapped[bool] = mapped_column(Boolean, default=True)
    plate_color: Mapped[bool] = mapped_column(Boolean, default=True)
    vehicle_class: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
