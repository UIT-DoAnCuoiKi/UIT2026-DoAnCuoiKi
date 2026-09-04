import pytest


def _staff(db):
    from app.models import User
    u = User(username="s", password_hash="x", role="staff")
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_open_shift_rejects_second_open(db_session):
    from app.services.shift import open_shift
    u = _staff(db_session)
    open_shift(db_session, u.id, 100000)
    with pytest.raises(ValueError):
        open_shift(db_session, u.id, 50000)


def test_close_shift_reconciles(db_session):
    from app.models import Payment
    from app.clock import now_utc
    from app.services.shift import close_shift, open_shift, shift_system_total
    u = _staff(db_session)
    shift = open_shift(db_session, u.id, 100000)

    db_session.add(Payment(session_id=1, amount=20000, method="cash", kind="payment",
                           shift_id=shift.id, staff_id=u.id, paid_at=now_utc()))
    db_session.add(Payment(session_id=2, amount=5000, method="cash", kind="refund",
                           shift_id=shift.id, staff_id=u.id, paid_at=now_utc()))
    db_session.commit()

    assert shift_system_total(db_session, shift.id) == 15000
    # đếm được 120000, đầu ca 100000 nên counted 20000; hệ thống 15000; chênh 5000
    recon = close_shift(db_session, shift, closing_cash=120000)
    assert recon["system_total"] == 15000
    assert recon["counted"] == 20000
    assert recon["difference"] == 5000
    assert shift.status == "closed"
