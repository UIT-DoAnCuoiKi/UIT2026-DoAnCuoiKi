from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ImageAsset(Base):
    __tablename__ = "image_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(512))
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    sha256: Mapped[str] = mapped_column(String(64))
    direction: Mapped[str | None] = mapped_column(String(4), nullable=True)  # in | out
    retention_delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
