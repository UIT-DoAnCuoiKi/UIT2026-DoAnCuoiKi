from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LaneCamera(Base):
    """Một camera vật lý gắn vào một làn.

    Trước đây `Lane.rtsp_url` là ô nhập tự do mà không có gì đọc lúc chạy
    (edge worker tự lấy nguồn từ CLI/env của chính nó) và chỉ chứa được đúng 1
    camera. Bảng này thay thế: mỗi làn có nhiều dòng, mỗi dòng 1 camera với vai
    trò riêng (trước/sau/toàn cảnh) và nguồn riêng (webcam trình duyệt hay RTSP).
    """

    __tablename__ = "lane_camera"

    id: Mapped[int] = mapped_column(primary_key=True)
    lane_id: Mapped[int] = mapped_column(ForeignKey("lane.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # front | rear | overview
    source_kind: Mapped[str] = mapped_column(String(16))  # browser | rtsp
    # browser: id thiết bị do navigator.mediaDevices trả về (lưu để nhớ lựa chọn,
    #   không đảm bảo ổn định giữa các máy — trình duyệt tự chọn lại nếu không khớp).
    # rtsp: URL luồng, chỉ có tác dụng khi edge worker đọc cấu hình này (chưa nối
    #   ở đợt này, xem "Việc KHÔNG làm" trong kế hoạch).
    device_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rtsp_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
