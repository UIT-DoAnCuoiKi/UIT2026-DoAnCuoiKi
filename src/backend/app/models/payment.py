from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("session.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)          # VND
    method: Mapped[str] = mapped_column(String(16))       # cash | qr | ewallet
    kind: Mapped[str] = mapped_column(String(16), default="payment")  # payment | refund | adjustment
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shift.id"), nullable=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
