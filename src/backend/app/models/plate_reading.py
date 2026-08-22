from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PlateReading(Base):
    __tablename__ = "plate_reading"

    id: Mapped[int] = mapped_column(primary_key=True)
    capture_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(4))  # in | out
    lane: Mapped[str | None] = mapped_column(String(32), nullable=True)

    plate_text_ciphertext: Mapped[str | None] = mapped_column(String(512), nullable=True)
    plate_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    plate_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    det_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    layout: Mapped[str | None] = mapped_column(String(8), nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    color_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vehicle_style: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vehicle_style_conf: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_pipeline_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_asset_id: Mapped[int | None] = mapped_column(ForeignKey("image_asset.id"), nullable=True)
    review_state: Mapped[str] = mapped_column(String(16))  # confident | needs_review | disputed | manual
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
