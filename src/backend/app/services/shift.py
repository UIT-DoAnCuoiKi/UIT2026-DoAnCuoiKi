from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import now_utc
from app.models import Payment, Shift


def current_open_shift(db: Session, staff_id: int) -> Shift | None:
    return db.scalars(
        select(Shift).where(Shift.staff_id == staff_id, Shift.status == "open")
    ).first()


def open_shift(db: Session, staff_id: int, opening_cash: int) -> Shift:
    if current_open_shift(db, staff_id) is not None:
        raise ValueError("đã có ca đang mở")
    shift = Shift(staff_id=staff_id, opened_at=now_utc(), opening_cash=opening_cash, status="open")
    db.add(shift); db.commit(); db.refresh(shift)
    return shift


def _sum(db: Session, shift_id: int, kind: str, method: str | None = None) -> int:
    stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.shift_id == shift_id, Payment.kind == kind)
    if method is not None:
        stmt = stmt.where(Payment.method == method)
    return int(db.scalar(stmt) or 0)


def shift_system_total(db: Session, shift_id: int) -> int:
    """Tổng thu ròng mọi phương thức trong ca (báo cáo doanh thu)."""
    return _sum(db, shift_id, "payment") - _sum(db, shift_id, "refund")


def shift_cash_total(db: Session, shift_id: int) -> int:
    """Tiền mặt ròng trong ca. Dùng đối soát ngăn kéo, bỏ qua qr và ewallet."""
    return _sum(db, shift_id, "payment", "cash") - _sum(db, shift_id, "refund", "cash")


def close_shift(db: Session, shift: Shift, closing_cash: int) -> dict:
    shift.closing_cash = closing_cash
    shift.closed_at = now_utc()
    shift.status = "closed"
    db.commit(); db.refresh(shift)
    system_total = shift_cash_total(db, shift.id)
    counted = closing_cash - shift.opening_cash
    return {
        "shift_id": shift.id,
        "system_total": system_total,
        "counted": counted,
        "difference": counted - system_total,
    }
