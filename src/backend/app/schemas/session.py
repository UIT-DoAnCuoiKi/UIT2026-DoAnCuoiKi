from datetime import datetime

from pydantic import BaseModel


class EntryRequest(BaseModel):
    reading_id: int
    zone_id: int | None = None


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
    plate_text: str


class SessionOut(BaseModel):
    id: int
    status: str
    vehicle_group: str | None = None
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
