from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.shift import ReconciliationOut, ShiftCloseIn, ShiftOpenIn, ShiftOut
from app.services.shift import close_shift, current_open_shift, open_shift

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.post("/open", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def open_current(body: ShiftOpenIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return open_shift(db, user.id, body.opening_cash)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/current", response_model=ShiftOut)
def get_current(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    shift = current_open_shift(db, user.id)
    if shift is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không có ca đang mở")
    return shift


@router.post("/close", response_model=ReconciliationOut)
def close_current(body: ShiftCloseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    shift = current_open_shift(db, user.id)
    if shift is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không có ca đang mở")
    return close_shift(db, shift, body.closing_cash)
