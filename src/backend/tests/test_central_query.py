EDGE = {"X-Edge-Key": "edge-dev-key"}


def _push(client, uuid, lot_id, plate_hash):
    item = {"entity_type": "session", "payload": {
        "uuid": uuid, "lot_id": lot_id, "zone_id": None, "plate_hash": plate_hash,
        "plate_ciphertext": "x", "vehicle_group": "o_to_con", "vehicle_type": "car",
        "status": "completed", "fee_amount": 1000, "match_flag": "exact",
        "entry_time": "2026-08-23T08:00:00", "exit_time": "2026-08-23T09:00:00",
    }}
    client.post("/sync/push", json={"items": [item]}, headers=EDGE)


def test_central_filters_by_lot(client, admin_headers):
    from app.security.plate import plate_hash
    _push(client, "c-1", 1, plate_hash("51A00001"))
    _push(client, "c-2", 2, plate_hash("51A00002"))
    rows = client.get("/central/sessions?lot_id=1", headers=admin_headers).json()
    assert all(r["lot_id"] == 1 for r in rows)
    assert any(r["uuid"] == "c-1" for r in rows)


def test_central_filters_by_plate_across_lots(client, admin_headers):
    from app.security.plate import plate_hash
    ph = plate_hash("51A55555")
    _push(client, "c-3", 1, ph)
    _push(client, "c-4", 2, ph)
    rows = client.get("/central/sessions?plate=51A55555", headers=admin_headers).json()
    uuids = {r["uuid"] for r in rows}
    assert {"c-3", "c-4"}.issubset(uuids)


def test_central_requires_admin(client, staff_headers):
    assert client.get("/central/sessions", headers=staff_headers).status_code == 403
