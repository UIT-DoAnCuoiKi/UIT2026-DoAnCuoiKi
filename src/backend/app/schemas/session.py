from datetime import datetime

from pydantic import BaseModel


class EntryRequest(BaseModel):
    reading_id: int


class ExitRequest(BaseModel):
    reading_id: int
    session_id: int | None = None  # nhân viên chọn ứng viên khi gợi ý


class ManualRequest(BaseModel):
    action: str  # entry | exit
    plate_text: str | None = None
    vehicle_group: str | None = None
    session_id: int | None = None


class ResolveRequest(BaseModel):
    fee_amount: int


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


class SessionDetail(SessionOut):
    vehicle_type: str | None = None
    entry_reading: ReadingBrief | None = None
    exit_reading: ReadingBrief | None = None


class SessionListResponse(BaseModel):
    total: int
    items: list[SessionOut]
