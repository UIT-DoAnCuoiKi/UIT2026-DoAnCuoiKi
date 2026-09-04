from sqlalchemy.orm import Session

from app.clock import now_utc
from app.models import Payment
from app.services.shift import current_open_shift


def record_payment(
    db: Session, *, session_id: int, amount: int, method: str,
    staff_id: int, kind: str = "payment", note: str | None = None,
) -> Payment:
    shift = current_open_shift(db, staff_id)
    payment = Payment(
        session_id=session_id, amount=amount, method=method, kind=kind, note=note,
        shift_id=shift.id if shift else None, staff_id=staff_id, paid_at=now_utc(),
    )
    db.add(payment); db.commit(); db.refresh(payment)
    return payment
