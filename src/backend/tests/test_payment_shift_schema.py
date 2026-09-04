def test_payment_and_shift_tables_registered():
    from app.db import Base
    import app.models  # noqa: F401
    assert "payment" in Base.metadata.tables
    assert "shift" in Base.metadata.tables


def test_payment_columns():
    from app.models import Payment
    cols = Payment.__table__.columns.keys()
    for c in ("session_id", "amount", "method", "kind", "shift_id", "staff_id", "paid_at"):
        assert c in cols


def test_shift_columns():
    from app.models import Shift
    cols = Shift.__table__.columns.keys()
    for c in ("staff_id", "opened_at", "closed_at", "opening_cash", "closing_cash", "status"):
        assert c in cols
