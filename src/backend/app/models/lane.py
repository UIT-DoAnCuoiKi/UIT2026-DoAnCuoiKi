from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lane(Base):
    __tablename__ = "lane"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    rtsp_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Khi làn có 2 camera: "primary" chỉ chạy nhận dạng trên camera chính (nhanh,
    # 1 lần suy luận); "best_of" chạy cả 2 rồi lấy kết quả ocr_conf cao hơn (chậm
    # hơn nhưng bù được trường hợp 1 camera bị khuất/lóa).
    recognition_mode: Mapped[str] = mapped_column(String(16), default="primary")
