from datetime import datetime

from pydantic import BaseModel


class ShiftOpenIn(BaseModel):
    opening_cash: int = 0


class ShiftCloseIn(BaseModel):
    closing_cash: int = 0


class ShiftOut(BaseModel):
    id: int
    staff_id: int
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: int
    closing_cash: int | None = None
    status: str
    model_config = {"from_attributes": True}


class ReconciliationOut(BaseModel):
    shift_id: int
    system_total: int
    counted: int
    difference: int
