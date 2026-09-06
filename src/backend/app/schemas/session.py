from datetime import datetime

from pydantic import BaseModel

from app.schemas.capture import ReadingImageOut


class EntryRequest(BaseModel):
    reading_id: int
    zone_id: int | None = None
    override_duplicate: bool = False  # cho phép vào dù biển đang trong bãi
    vehicle_group: str | None = None  # nhân viên chọn nhóm phí thủ công, ghi đè suy luận từ loại xe


class ExitRequest(BaseModel):
    reading_id: int
    session_id: int | None = None  # nhân viên chọn ứng viên khi gợi ý


class ManualRequest(BaseModel):
    action: str  # entry | exit
    plate_text: str | None = None
    vehicle_group: str | None = None
    session_id: int | None = None
    reading_id: int | None = None  # entry: bắt buộc, phải là reading có biển đã nhận dạng từ ảnh


class ResolveRequest(BaseModel):
    fee_amount: int


class LostTicketRequest(BaseModel):
    reading_id: int
    penalty_amount: int
    vehicle_group: str | None = None


class PlatePatch(BaseModel):
    plate_text: str | None = None
    vehicle_type: str | None = None
    color: str | None = None


class SessionPatch(BaseModel):
    """Nhân viên chỉnh loại xe / màu biển của một phiên đã ghi nhận."""
    vehicle_type: str | None = None
    color: str | None = None


class SessionOut(BaseModel):
    id: int
    status: str
    vehicle_group: str | None = None
    color: str | None = None
    plate_text: str | None = None
    entry_time: datetime | None = None
    exit_time: datetime | None = None
    fee_amount: int | None = None
    match_flag: str | None = None
    warning: str | None = None


class SessionBrief(BaseModel):
    id: int
    plate_text: str | None = None
    vehicle_group: str
    entry_time: datetime | None = None


class ExitResult(BaseModel):
    outcome: str  # completed | suggest | disputed
    session: SessionOut | None = None
    candidates: list[SessionBrief] = []
    match_flag: str | None = None


class ReadingBrief(BaseModel):
    id: int | None = None
    direction: str | None = None
    plate_text: str | None = None
    review_state: str | None = None
    image_asset_id: int | None = None
    plate_crop_asset_id: int | None = None
    # Có sẵn trên model nhưng trước đây không lộ ra: màn đối chiếu vào/ra cần
    # ghi rõ ảnh chụp lúc nào và ở làn nào, nếu không 2 ảnh cạnh nhau không có
    # gì để phân biệt ngoài vị trí đặt.
    created_at: datetime | None = None
    lane: str | None = None
    # Ảnh của mọi camera đã lưu cho lượt này (làn đa camera); rỗng nếu làn chỉ
    # có 1 camera. `image_asset_id` ở trên vẫn luôn là ảnh camera chính.
    images: list[ReadingImageOut] = []


class ExitPreview(BaseModel):
    """Kết quả tính thử khi xe RA, KHÔNG ghi gì vào DB.

    Tách khỏi `ExitResult` vì mục đích khác hẳn: `ExitResult` là kết quả đã chốt
    (phiên đã đóng, phí đã ghi), còn cái này để nhân viên đối chiếu ảnh vào/ra và
    xem phí dự tính TRƯỚC khi quyết định thu tiền. `outcome` dùng lại đúng bộ giá
    trị của `ExitResult` để frontend xử lý một kiểu.
    """
    outcome: str  # match | suggest | no_match
    session: SessionOut | None = None
    candidates: list[SessionBrief] = []
    match_flag: str | None = None
    entry_reading: ReadingBrief | None = None
    exit_reading: ReadingBrief | None = None
    minutes: float | None = None          # thời lượng gửi, phút
    fee_amount: int | None = None         # phí dự tính, chưa ghi
    fee_rule_snapshot: dict | None = None  # diễn giải cách tính
    fee_error: str | None = None          # vd chưa có bảng giá cho nhóm xe này


class PaymentBrief(BaseModel):
    id: int
    amount: int
    method: str
    kind: str
    note: str | None = None
    staff_name: str | None = None
    paid_at: datetime


class SessionDetail(SessionOut):
    vehicle_type: str | None = None
    entry_reading: ReadingBrief | None = None
    exit_reading: ReadingBrief | None = None
    created_by_name: str | None = None
    closed_by_name: str | None = None
    lot_name: str | None = None
    zone_name: str | None = None
    fee_rule_snapshot: dict | None = None
    payments: list[PaymentBrief] = []


class SessionListItem(SessionOut):
    vehicle_type: str | None = None
    closed_by_name: str | None = None
    payment_method: str | None = None


class SessionListResponse(BaseModel):
    total: int
    items: list[SessionListItem]
