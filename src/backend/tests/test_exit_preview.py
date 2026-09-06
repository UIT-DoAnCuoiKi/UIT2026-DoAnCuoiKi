"""POST /sessions/exit/preview — tính thử lượt RA để nhân viên đối chiếu.

Điểm mấu chốt phải giữ: xem trước KHÔNG được ghi gì vào DB. Trước khi có endpoint
này, `compute_fee` chỉ chạy bên trong `_complete_session`, nên muốn biết phí là
phiên đã bị đóng — nhân viên không có cơ hội so ảnh vào/ra rồi mới quyết định.
"""
from app.models import ParkingSession, PriceRule


def _seed_price(db, group="unknown", price=6000):
    db.add(PriceRule(vehicle_group=group, mode="flat", unit_price=price, active=True))
    db.commit()


def _enter(client, headers, make_reading, plate="51F00123", capture="cap-prev-in"):
    reading = make_reading(plate=plate, direction="in", capture_id=capture)
    r = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_preview_returns_fee_and_entry_evidence_without_closing(
    client, db_session, staff_headers, make_reading
):
    _seed_price(db_session)
    sid = _enter(client, staff_headers, make_reading)
    out = make_reading(plate="51F00123", direction="out", capture_id="cap-prev-out")

    r = client.post("/sessions/exit/preview", json={"reading_id": out.id}, headers=staff_headers)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["outcome"] == "match"
    assert body["session"]["id"] == sid
    assert body["fee_amount"] == 6000
    assert body["fee_rule_snapshot"]["mode"] == "flat"
    assert body["minutes"] is not None
    # Bằng chứng 2 đầu để dựng màn đối chiếu ảnh vào | ảnh ra
    assert body["entry_reading"]["id"] is not None
    assert body["exit_reading"]["id"] == out.id

    # Quan trọng nhất: phiên vẫn đang trong bãi, chưa bị đóng, chưa ghi phí
    db_session.expire_all()
    s = db_session.get(ParkingSession, sid)
    assert s.status == "in_lot"
    assert s.exit_time is None
    assert s.fee_amount is None


def test_preview_reports_missing_price_rule_instead_of_failing(
    client, db_session, staff_headers, make_reading
):
    """Không có bảng giá thì báo lỗi mềm để nhân viên vẫn xem được ảnh đối chiếu,
    thay vì trả 422 làm hỏng cả màn hình (confirm_exit mới là chỗ chặn cứng)."""
    sid = _enter(client, staff_headers, make_reading, plate="51F00124", capture="cap-prev-in2")
    out = make_reading(plate="51F00124", direction="out", capture_id="cap-prev-out2")

    body = client.post(
        "/sessions/exit/preview", json={"reading_id": out.id}, headers=staff_headers
    ).json()

    assert body["outcome"] == "match"
    assert body["session"]["id"] == sid
    assert body["fee_amount"] is None
    assert "bảng giá" in body["fee_error"]


def test_preview_no_match_still_returns_exit_evidence(client, staff_headers, make_reading):
    out = make_reading(plate="99Z99999", direction="out", capture_id="cap-prev-nomatch")
    body = client.post(
        "/sessions/exit/preview", json={"reading_id": out.id}, headers=staff_headers
    ).json()

    assert body["outcome"] == "no_match"
    assert body["session"] is None
    assert body["exit_reading"]["id"] == out.id


def test_preview_then_confirm_charges_same_amount(
    client, db_session, staff_headers, make_reading
):
    """Xem trước rồi mới chốt: số tiền hiện cho nhân viên phải khớp số tiền thu."""
    _seed_price(db_session, price=7000)
    _enter(client, staff_headers, make_reading, plate="51F00125", capture="cap-prev-in3")
    out = make_reading(plate="51F00125", direction="out", capture_id="cap-prev-out3")

    preview = client.post(
        "/sessions/exit/preview", json={"reading_id": out.id}, headers=staff_headers
    ).json()
    confirmed = client.post(
        "/sessions/exit", json={"reading_id": out.id}, headers=staff_headers
    ).json()

    assert preview["fee_amount"] == confirmed["session"]["fee_amount"] == 7000


def test_reading_brief_exposes_capture_time_and_lane(client, db_session, staff_headers, make_reading):
    """Màn đối chiếu cần biết ảnh chụp lúc nào/ở làn nào mới phân biệt được 2 ảnh."""
    sid = _enter(client, staff_headers, make_reading, plate="51F00126", capture="cap-prev-in4")
    detail = client.get(f"/sessions/{sid}", headers=staff_headers).json()
    assert detail["entry_reading"]["created_at"] is not None
    assert "lane" in detail["entry_reading"]
