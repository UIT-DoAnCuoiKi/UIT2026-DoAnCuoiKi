from datetime import datetime

from pydantic import BaseModel


class BarrierOpenIn(BaseModel):
    mode: str                      # auto | manual | emergency
    device_id: int | None = None
    session_id: int | None = None
    reason: str | None = None


class BarrierEventOut(BaseModel):
    id: int
    device_id: int | None = None
    session_id: int | None = None
    action: str
    mode: str
    reason: str | None = None
    user_id: int | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
