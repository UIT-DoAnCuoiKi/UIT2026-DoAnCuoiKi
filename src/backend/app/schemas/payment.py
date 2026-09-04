from datetime import datetime

from pydantic import BaseModel


class PaymentIn(BaseModel):
    session_id: int
    amount: int
    method: str          # cash | qr | ewallet
    kind: str = "payment"  # payment | refund | adjustment
    note: str | None = None


class PaymentOut(BaseModel):
    id: int
    session_id: int
    amount: int
    method: str
    kind: str
    note: str | None = None
    shift_id: int | None = None
    staff_id: int
    paid_at: datetime
    model_config = {"from_attributes": True}
