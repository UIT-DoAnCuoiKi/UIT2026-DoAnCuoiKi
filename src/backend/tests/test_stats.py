from datetime import datetime

from app.models import ParkingSession
from app.security import crypto, plate


def _completed(db, fee, entry, exit_):
    s = ParkingSession(plate_hash=plate.plate_hash("51F-123.45"), plate_ciphertext=crypto.encrypt_text("51F-123.45"),
                       vehicle_group="o_to_con", status="completed", entry_time=entry, exit_time=exit_, fee_amount=fee)
    db.add(s); db.commit(); return s


def test_stats_revenue_and_counts(client, db_session, staff_headers):
    _completed(db_session, 5000, datetime(2026, 8, 22, 8), datetime(2026, 8, 22, 9))
    _completed(db_session, 3000, datetime(2026, 8, 22, 10), datetime(2026, 8, 22, 11))
    db_session.add(ParkingSession(plate_hash="h", plate_ciphertext="", vehicle_group="o_to_con", status="in_lot"))
    db_session.commit()

    r = client.get("/stats", params={"from": "2026-08-22T00:00:00", "to": "2026-08-22T23:59:59"}, headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["in_lot"] == 1
    assert body["exits"] == 2
    assert body["revenue"] == 8000


def test_stats_export_admin_only(client, db_session, make_user):
    make_user(username="stf", password="pw", role="staff")
    make_user(username="adm", password="pw", role="admin")
    st = client.post("/auth/login", json={"username": "stf", "password": "pw"}).json()["access_token"]
    ad = client.post("/auth/login", json={"username": "adm", "password": "pw"}).json()["access_token"]

    assert client.get("/stats/export", headers={"Authorization": f"Bearer {st}"}).status_code == 403
    r = client.get("/stats/export", headers={"Authorization": f"Bearer {ad}"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "date,entries,exits,revenue" in r.text
