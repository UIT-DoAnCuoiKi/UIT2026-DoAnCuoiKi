"""Regression tests cho các bug review chỉ ra ở phase 1 tới 6.

Mỗi test khoá đúng nhánh mà suite cũ bỏ sót: giá block thiếu block_minutes,
đối soát ca lẫn tiền không phải mặt, cảnh báo vào bị ghi đè, vé tháng theo UTC.
"""
from datetime import datetime, timedelta

import pytest


# --- Bug 1: price rule mode=block thiếu block_minutes ---------------------

def test_price_rule_block_requires_block_minutes(client, admin_headers):
    r = client.post(
        "/price-rules",
        json={"vehicle_group": "o_to_con", "mode": "block", "unit_price": 5000},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_price_rule_block_with_block_minutes_ok(client, admin_headers):
    from app.deps import get_db
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(next(client.app.dependency_overrides[get_db]()))
    r = client.post(
        "/price-rules",
        json={"vehicle_group": "o_to_con", "mode": "block", "unit_price": 5000, "block_minutes": 60},
        headers=admin_headers,
    )
    assert r.status_code == 201


def test_price_rule_patch_to_block_requires_block_minutes(client, admin_headers):
    from app.deps import get_db
    from app.services.vehicle_groups import seed_default_vehicle_groups
    seed_default_vehicle_groups(next(client.app.dependency_overrides[get_db]()))
    rid = client.post(
        "/price-rules",
        json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000},
        headers=admin_headers,
    ).json()["id"]
    r = client.patch(f"/price-rules/{rid}", json={"mode": "block"}, headers=admin_headers)
    assert r.status_code == 422


def test_compute_fee_block_missing_block_minutes_raises():
    from app.models import PriceRule
    from app.services.fee import compute_fee

    rule = PriceRule(vehicle_group="o_to_con", mode="block", unit_price=5000)
    rule.grace_minutes = 0
    rule.daily_cap = None
    with pytest.raises(ValueError):
        compute_fee(rule, datetime(2026, 8, 1, 8, 0), datetime(2026, 8, 1, 10, 0))


# --- Bug 2: đối soát ca chỉ tính tiền mặt ---------------------------------

def test_reconciliation_ignores_non_cash(db_session):
    from app.clock import now_utc
    from app.models import Payment, User
    from app.services.shift import close_shift, open_shift

    u = User(username="cashier", password_hash="x", role="staff")
    db_session.add(u); db_session.commit(); db_session.refresh(u)
    shift = open_shift(db_session, u.id, 100000)

    # 20000 tiền mặt vào ngăn kéo, 50000 qr không vào ngăn kéo
    db_session.add(Payment(session_id=1, amount=20000, method="cash", kind="payment",
                           shift_id=shift.id, staff_id=u.id, paid_at=now_utc()))
    db_session.add(Payment(session_id=2, amount=50000, method="qr", kind="payment",
                           shift_id=shift.id, staff_id=u.id, paid_at=now_utc()))
    db_session.commit()

    recon = close_shift(db_session, shift, closing_cash=120000)
    assert recon["system_total"] == 20000  # qr bị loại
    assert recon["counted"] == 20000
    assert recon["difference"] == 0


# --- Bug 3: cảnh báo vào gộp danh sách đen và biển trùng ------------------

def test_entry_warning_combines_blacklist_and_duplicate(client, admin_headers, staff_headers, make_reading, db_session):
    from app.clock import now_utc
    from app.models import ParkingSession
    from app.security import crypto
    from app.security.plate import plate_hash

    plate = "88C88888"
    client.post("/blacklist", json={"plate_text": plate}, headers=admin_headers)
    db_session.add(ParkingSession(
        plate_hash=plate_hash(plate), plate_ciphertext=crypto.encrypt_text(plate),
        vehicle_group="o_to_con", status="in_lot", entry_time=now_utc(),
    ))
    db_session.commit()

    reading = make_reading(plate=plate, direction="in")
    warning = client.post(
        "/sessions/entry",
        json={"reading_id": reading.id, "override_duplicate": True},
        headers=staff_headers,
    ).json()["warning"]
    assert "đen" in warning
    assert "trùng" in warning


# --- Bug 4: vé tháng dùng ngày UTC ----------------------------------------

def test_has_valid_pass_uses_utc_today(db_session):
    from app.clock import now_utc
    from app.models import MonthlyPass
    from app.security.plate import plate_hash
    from app.services.registry import has_valid_pass

    ph = plate_hash("30A12345")
    today = now_utc().date()
    db_session.add(MonthlyPass(
        plate_hash=ph, plate_ciphertext="x", vehicle_group="o_to_con",
        start_date=today, end_date=today + timedelta(days=30), active=True,
    ))
    db_session.commit()
    assert has_valid_pass(db_session, ph) is True
    # vé đã hết hạn không tính
    assert has_valid_pass(db_session, ph, on=today + timedelta(days=60)) is False
