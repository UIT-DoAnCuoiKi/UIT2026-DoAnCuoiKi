"""E2E regression cho bug review, chạy vào backend HTTP thật + Postgres thật.

Chạy: rebuild backend với code vá, rồi
    set -a; . ./.env; set +a
    BASE_URL=http://localhost:8000 pytest src/backend/tests_e2e/test_review_regressions.py
Module tự skip nếu backend không chạy (fixture api trong conftest).
"""
from tests_e2e.test_api_flow import _capture, _uid


# --- Bug 1: giá block thiếu block_minutes bị chặn -------------------------

def test_price_rule_block_requires_block_minutes_e2e(api, admin_h):
    r = api.post(
        "/price-rules",
        json={"vehicle_group": "o_to_con", "mode": "block", "unit_price": 5000},
        headers=admin_h,
    )
    assert r.status_code == 422, r.text


# --- Bug 2: đối soát ca bỏ qua qr/ewallet ---------------------------------

def test_shift_reconciliation_ignores_non_cash_e2e(api, staff_h):
    o = api.post("/shifts/open", json={"opening_cash": 100000}, headers=staff_h)
    if o.status_code == 409:  # còn ca mở từ test khác, đóng cho sạch rồi mở lại
        api.post("/shifts/close", json={"closing_cash": 0}, headers=staff_h)
        o = api.post("/shifts/open", json={"opening_cash": 100000}, headers=staff_h)
    assert o.status_code == 201, o.text

    uid = _uid()
    s = api.post(
        "/sessions/manual",
        json={"action": "entry", "plate_text": f"51K-{uid[:3]}.{uid[3:5]}", "vehicle_group": "o_to_con"},
        headers=staff_h,
    )
    assert s.status_code == 200, s.text
    sid = s.json()["id"]

    assert api.post("/payments", json={"session_id": sid, "amount": 20000, "method": "cash"}, headers=staff_h).status_code == 201
    assert api.post("/payments", json={"session_id": sid, "amount": 50000, "method": "qr"}, headers=staff_h).status_code == 201

    recon = api.post("/shifts/close", json={"closing_cash": 120000}, headers=staff_h).json()
    assert recon["system_total"] == 20000, recon   # qr bị loại khỏi đối soát ngăn kéo
    assert recon["counted"] == 20000
    assert recon["difference"] == 0


# --- Bug 3: cảnh báo vào gộp danh sách đen và biển trùng ------------------

def test_entry_warning_combines_blacklist_and_duplicate_e2e(api, admin_h, staff_h):
    uid = _uid()
    plate = f"88C-{uid[:3]}.{uid[3:5]}"
    assert api.post("/blacklist", json={"plate_text": plate}, headers=admin_h).status_code == 201

    r1 = _capture(api, f"e2e-bl1-{uid}", "in", plate)
    assert r1.status_code == 200, r1.text
    e1 = api.post("/sessions/entry", json={"reading_id": r1.json()["reading_id"]}, headers=staff_h)
    assert e1.status_code == 200, e1.text  # xe vào bãi, cảnh báo đen

    r2 = _capture(api, f"e2e-bl2-{uid}", "in", plate)
    w = api.post("/sessions/entry", json={"reading_id": r2.json()["reading_id"]}, headers=staff_h).json()["warning"]
    assert w and "đen" in w and "trùng" in w, w
