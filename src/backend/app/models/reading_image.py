from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ReadingImage(Base):
    """Ảnh phụ (thường là camera thứ 2) của một lượt chụp.

    `PlateReading.image_asset_id` vẫn giữ nguyên là ảnh chính (đi qua nhận
    dạng) để code cũ không phải đổi gì; bảng này chỉ cộng thêm cho trường hợp
    làn có 2-3 camera (trước/sau xe) và cần lưu đủ ảnh của mọi camera, không
    chỉ ảnh dùng để đọc biển.
    """

    __tablename__ = "reading_image"

    id: Mapped[int] = mapped_column(primary_key=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("plate_reading.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # front | rear | overview
    image_asset_id: Mapped[int] = mapped_column(ForeignKey("image_asset.id"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
