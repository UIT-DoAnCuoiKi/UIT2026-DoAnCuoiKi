from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import ParkingSession, Payment, User
from app.schemas.payment import PaymentIn, PaymentOut
from app.services.payment import record_payment

router = APIRouter(tags=["payments"])


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.get(ParkingSession, body.session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy phiên")
    return record_payment(
        db, session_id=body.session_id, amount=body.amount, method=body.method,
        staff_id=user.id, kind=body.kind, note=body.note,
    )


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(
        select(Payment).where(Payment.session_id == session_id).order_by(Payment.id)
    ).all())
