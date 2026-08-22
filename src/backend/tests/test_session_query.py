from app.models import ParkingSession
from app.security import crypto, plate


def _session(db, plate_text, status="in_lot"):
    s = ParkingSession(plate_hash=plate.plate_hash(plate_text), plate_ciphertext=crypto.encrypt_text(plate_text),
                       vehicle_group="o_to_con", status=status)
    db.add(s); db.commit(); db.refresh(s); return s


def test_list_filters_by_plate(client, db_session, staff_headers):
    _session(db_session, "51F-123.45")
    _session(db_session, "30A-678.90")
    r = client.get("/sessions", params={"plate": "51f 123 45"}, headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["plate_text"] == "51F-123.45"


def test_list_filters_by_status_and_paginates(client, db_session, staff_headers):
    for i in range(3):
        _session(db_session, f"51F-000.0{i}", status="completed")
    _session(db_session, "88H-111.11", status="in_lot")
    r = client.get("/sessions", params={"status": "completed", "limit": 2, "offset": 0}, headers=staff_headers)
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_detail_returns_readings(client, db_session, staff_headers):
    s = _session(db_session, "51F-123.45")
    r = client.get(f"/sessions/{s.id}", headers=staff_headers)
    assert r.status_code == 200
    assert r.json()["plate_text"] == "51F-123.45"


def test_query_requires_auth(client):
    assert client.get("/sessions").status_code in (401, 403)
