from sqlalchemy import select

from app.models import AuditLog, ParkingSession, PlateReading, PriceRule
from app.security import crypto, plate


def _seed_price(db):
    db.add(PriceRule(vehicle_group="xe_may", mode="flat", unit_price=3000, active=True))
    db.commit()


def test_manual_entry_then_exit(client, db_session, staff_headers):
    _seed_price(db_session)
    r = client.post("/sessions/manual", json={"action": "entry", "plate_text": "59X1-234.56", "vehicle_group": "xe_may"}, headers=staff_headers)
    assert r.status_code == 200
    sid = r.json()["id"]
    assert r.json()["status"] == "in_lot"
    assert r.json()["match_flag"] == "manual"

    r2 = client.post("/sessions/manual", json={"action": "exit", "session_id": sid}, headers=staff_headers)
    assert r2.json()["status"] == "completed"
    assert r2.json()["fee_amount"] == 3000


def test_patch_plate_updates_and_audits(client, db_session, staff_headers):
    reading = PlateReading(capture_id="patch1", direction="in", plate_text_ciphertext=crypto.encrypt_text("51F-000.00"),
                           plate_hash=plate.plate_hash("51F-000.00"), review_state="needs_review", vehicle_type="car")
    db_session.add(reading); db_session.commit(); db_session.refresh(reading)

    r = client.patch(f"/readings/{reading.id}/plate", json={"plate_text": "51F-123.45"}, headers=staff_headers)
    assert r.status_code == 200
    db_session.refresh(reading)
    assert reading.plate_hash == plate.plate_hash("51F12345")
    assert reading.review_state == "manual"
    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "edit_plate")).all()
    assert len(logs) == 1


def test_dispute_then_resolve(client, db_session, staff_headers):
    session = ParkingSession(plate_hash="h", plate_ciphertext=crypto.encrypt_text("51F-123.45"),
                             vehicle_group="o_to_con", status="in_lot")
    db_session.add(session); db_session.commit(); db_session.refresh(session)

    assert client.post(f"/sessions/{session.id}/dispute", headers=staff_headers).json()["status"] == "disputed"

    r = client.post(f"/sessions/{session.id}/resolve", json={"fee_amount": 8000}, headers=staff_headers)
    assert r.json()["status"] == "completed"
    assert r.json()["fee_amount"] == 8000
