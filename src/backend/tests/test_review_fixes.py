"""Regression cho các lỗi tìm được khi review branch feat/duc-dashboard-backend.

Mỗi test dưới đây gắn với đúng một lỗi đã sửa; nếu ai đó vô tình quay lại hành vi
cũ thì test tương ứng fail chứ không im lặng.
"""
from sqlalchemy import select

from app.models import AuditLog, Outbox, ParkingLot, ParkingSession, PlateBlacklist, PriceRule
from app.security import crypto, plate


def _lot(db, capacity: int = 1, active: bool = True) -> ParkingLot:
    lot = ParkingLot(name="Bãi chính", capacity=capacity, active=active)
    db.add(lot); db.commit(); db.refresh(lot)
    return lot


def _session_in_lot(db, plate_text="51F-999.99", status="in_lot") -> ParkingSession:
    s = ParkingSession(plate_hash=plate.plate_hash(plate_text),
                       plate_ciphertext=crypto.encrypt_text(plate_text),
                       vehicle_group="o_to_con", status=status)
    db.add(s); db.commit(); db.refresh(s)
    return s


# --- Bãi đầy chặn được xe vào dù màn cổng không gửi zone_id ---

def test_entry_blocked_when_default_lot_is_full(client, db_session, staff_headers, make_reading):
    """Trước đây lot_is_full chỉ chạy khi có zone_id, mà frontend không bao giờ
    gửi zone_id, nên bãi đầy vẫn nhận xe."""
    _lot(db_session, capacity=1)
    r1 = make_reading(plate="51F00011", direction="in", capture_id="cap-full-1")
    r2 = make_reading(plate="51F00022", direction="in", capture_id="cap-full-2")

    first = client.post("/sessions/entry", json={"reading_id": r1.id}, headers=staff_headers)
    assert first.status_code == 200

    second = client.post("/sessions/entry", json={"reading_id": r2.id}, headers=staff_headers)
    assert second.status_code == 409
    assert second.json()["detail"]["error_code"] == "lot_full"


def test_entry_assigns_default_lot_id(client, db_session, staff_headers, make_reading):
    """Phiên phải mang lot_id, nếu không sẽ vô hình với báo cáo occupancy."""
    lot = _lot(db_session, capacity=10)
    reading = make_reading(plate="51F00033", direction="in", capture_id="cap-lot-1")

    sid = client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers).json()["id"]
    assert db_session.get(ParkingSession, sid).lot_id == lot.id


def test_entry_without_any_lot_still_works(client, staff_headers, make_reading):
    """Chưa cấu hình bãi nào thì vẫn cho vào, chỉ là không kiểm sức chứa."""
    reading = make_reading(plate="51F00044", direction="in", capture_id="cap-nolot-1")
    assert client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers).status_code == 200


# --- Nhập tay VÀO chịu chung guard với xác nhận VÀO ---

def test_manual_entry_blocked_when_lot_full(client, db_session, staff_headers, make_reading):
    _lot(db_session, capacity=1)
    reading_in = make_reading(plate="51F00055", direction="in", capture_id="cap-mf-1")
    assert client.post("/sessions/entry", json={"reading_id": reading_in.id}, headers=staff_headers).status_code == 200

    reading_manual = make_reading(plate="59X12345", direction="in", capture_id="cap-mf-2")
    r = client.post(
        "/sessions/manual",
        json={"action": "entry", "plate_text": "59X1-234.56", "vehicle_group": "xe_may",
              "reading_id": reading_manual.id},
        headers=staff_headers,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "lot_full"


def test_manual_entry_blocked_on_duplicate_plate(client, staff_headers, make_reading):
    reading_in = make_reading(plate="59X12399", direction="in", capture_id="cap-md-1")
    assert client.post("/sessions/entry", json={"reading_id": reading_in.id}, headers=staff_headers).status_code == 200

    reading_manual = make_reading(plate="59X12399", direction="in", capture_id="cap-md-2")
    r = client.post(
        "/sessions/manual",
        json={"action": "entry", "plate_text": "59X1-239.9", "vehicle_group": "xe_may",
              "reading_id": reading_manual.id},
        headers=staff_headers,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "duplicate_plate"


def test_manual_entry_warns_on_blacklist(client, db_session, staff_headers, make_reading):
    plate_text = "59X1-777.77"
    db_session.add(PlateBlacklist(plate_hash=plate.plate_hash(plate_text),
                                  plate_ciphertext=crypto.encrypt_text(plate_text), active=True))
    db_session.commit()

    reading = make_reading(plate="59X17777", direction="in", capture_id="cap-mb-1")
    r = client.post(
        "/sessions/manual",
        json={"action": "entry", "plate_text": plate_text, "vehicle_group": "xe_may", "reading_id": reading.id},
        headers=staff_headers,
    )
    assert r.status_code == 200
    assert "danh sách đen" in (r.json()["warning"] or "")


# --- Phân quyền và kiểm soát trạng thái ---

def test_dispute_requires_manager_role(client, db_session, staff_headers):
    s = _session_in_lot(db_session)
    assert client.post(f"/sessions/{s.id}/dispute", headers=staff_headers).status_code == 403


def test_resolve_requires_manager_role(client, db_session, staff_headers, admin_headers):
    s = _session_in_lot(db_session)
    client.post(f"/sessions/{s.id}/dispute", headers=admin_headers)
    r = client.post(f"/sessions/{s.id}/resolve", json={"fee_amount": 5000}, headers=staff_headers)
    assert r.status_code == 403


def test_cannot_dispute_an_already_disputed_session(client, db_session, admin_headers):
    s = _session_in_lot(db_session, status="disputed")
    assert client.post(f"/sessions/{s.id}/dispute", headers=admin_headers).status_code == 409


def test_cannot_resolve_a_session_that_is_not_disputed(client, db_session, admin_headers):
    """Trước đây resolve ép được cả phiên đang trong bãi thành completed, bỏ qua
    hoàn toàn bảng giá."""
    s = _session_in_lot(db_session, status="in_lot")
    r = client.post(f"/sessions/{s.id}/resolve", json={"fee_amount": 1000}, headers=admin_headers)
    assert r.status_code == 409


def test_resolve_rejects_negative_fee(client, db_session, admin_headers):
    s = _session_in_lot(db_session, status="disputed")
    r = client.post(f"/sessions/{s.id}/resolve", json={"fee_amount": -1}, headers=admin_headers)
    assert r.status_code == 422


def test_dispute_and_resolve_write_audit(client, db_session, admin_headers):
    s = _session_in_lot(db_session)
    client.post(f"/sessions/{s.id}/dispute", headers=admin_headers)
    client.post(f"/sessions/{s.id}/resolve", json={"fee_amount": 7000}, headers=admin_headers)

    actions = {log.action: log for log in db_session.scalars(select(AuditLog)).all()}
    assert "dispute_session" in actions and "resolve_session" in actions
    assert actions["dispute_session"].entity_id == str(s.id)
    assert actions["resolve_session"].entity_id == str(s.id)
    assert "7000" in (actions["resolve_session"].detail or "")


def test_lost_ticket_audit_links_to_session(client, db_session, staff_headers, make_reading):
    """entity_id từng luôn rỗng nên không truy ngược được phiên bị phạt."""
    reading = make_reading(plate="51F00066", direction="out", capture_id="cap-lt-1")
    sid = client.post("/sessions/lost-ticket",
                      json={"reading_id": reading.id, "penalty_amount": 50000},
                      headers=staff_headers).json()["id"]

    log = db_session.scalars(select(AuditLog).where(AuditLog.action == "lost_ticket")).first()
    assert log is not None and log.entity_id == str(sid)


# --- Outbox: mọi thay đổi phiên đều phải được đẩy đi đồng bộ ---

def _outbox_count(db) -> int:
    return len(list(db.scalars(select(Outbox)).all()))


def test_manual_entry_enqueues_outbox(client, db_session, staff_headers, make_reading):
    reading = make_reading(plate="59X15555", direction="in", capture_id="cap-ob-1")
    before = _outbox_count(db_session)
    client.post("/sessions/manual",
                json={"action": "entry", "plate_text": "59X1-555.55", "vehicle_group": "xe_may",
                      "reading_id": reading.id},
                headers=staff_headers)
    assert _outbox_count(db_session) > before


def test_disputed_exit_enqueues_outbox(client, db_session, staff_headers, make_reading):
    """Xe ra không khớp phiên nào tạo phiên disputed, trước đây không đồng bộ."""
    reading = make_reading(plate="51F00077", direction="out", capture_id="cap-ob-2")
    before = _outbox_count(db_session)
    assert client.post("/sessions/exit", json={"reading_id": reading.id},
                       headers=staff_headers).json()["outcome"] == "disputed"
    assert _outbox_count(db_session) > before


def test_dispute_and_resolve_enqueue_outbox(client, db_session, admin_headers):
    s = _session_in_lot(db_session)
    before = _outbox_count(db_session)
    client.post(f"/sessions/{s.id}/dispute", headers=admin_headers)
    after_dispute = _outbox_count(db_session)
    assert after_dispute > before

    client.post(f"/sessions/{s.id}/resolve", json={"fee_amount": 4000}, headers=admin_headers)
    assert _outbox_count(db_session) > after_dispute


def test_lost_ticket_enqueues_outbox(client, db_session, staff_headers, make_reading):
    reading = make_reading(plate="51F00088", direction="out", capture_id="cap-ob-3")
    before = _outbox_count(db_session)
    client.post("/sessions/lost-ticket",
                json={"reading_id": reading.id, "penalty_amount": 30000},
                headers=staff_headers)
    assert _outbox_count(db_session) > before


# --- Thiết bị biên báo được heartbeat bằng edge key ---

def test_heartbeat_accepts_edge_key(client, admin_headers):
    """Edge worker chỉ có X-Edge-Key, không có JWT nhân viên. Trước đây endpoint
    này bắt buộc JWT nên không thiết bị biên nào báo được, màn health luôn offline."""
    from app.config import settings

    dev = client.post("/devices", json={"kind": "camera", "name": "cam-in"}, headers=admin_headers).json()
    r = client.post(f"/devices/{dev['id']}/heartbeat", headers={"X-Edge-Key": settings.edge_api_key})
    assert r.status_code == 200
    assert r.json()["last_heartbeat"] is not None


def test_heartbeat_rejects_wrong_edge_key(client, admin_headers):
    dev = client.post("/devices", json={"kind": "camera", "name": "cam-out"}, headers=admin_headers).json()
    assert client.post(f"/devices/{dev['id']}/heartbeat", headers={"X-Edge-Key": "sai-key"}).status_code == 401


def test_heartbeat_rejects_no_credentials(client, admin_headers):
    dev = client.post("/devices", json={"kind": "camera", "name": "cam-x"}, headers=admin_headers).json()
    assert client.post(f"/devices/{dev['id']}/heartbeat").status_code == 401


# --- Bảng giá vẫn hoạt động bình thường sau khi gộp hàm tạo phiên ---

def test_normal_entry_exit_still_charges_fee(client, db_session, staff_headers, make_reading):
    db_session.add(PriceRule(vehicle_group="unknown", mode="flat", unit_price=6000, active=True))
    db_session.commit()
    r_in = make_reading(plate="51F00099", direction="in", capture_id="cap-fee-1")
    client.post("/sessions/entry", json={"reading_id": r_in.id}, headers=staff_headers)
    r_out = make_reading(plate="51F00099", direction="out", capture_id="cap-fee-2")
    body = client.post("/sessions/exit", json={"reading_id": r_out.id}, headers=staff_headers).json()
    assert body["outcome"] == "completed"
    assert body["session"]["fee_amount"] == 6000
