def test_entry_enqueues_outbox(client, staff_headers, make_reading, db_session):
    from app.models import Outbox
    reading = make_reading(plate="51F70001", direction="in")
    client.post("/sessions/entry", json={"reading_id": reading.id}, headers=staff_headers)
    assert db_session.query(Outbox).filter(Outbox.entity_type == "session").count() >= 1
