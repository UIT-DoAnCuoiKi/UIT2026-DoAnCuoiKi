from sqlalchemy import select

from app.models import AuditLog
from app.services.audit import write_audit


def test_write_audit_inserts_row(db_session):
    write_audit(db_session, user_id=None, action="login")
    db_session.commit()
    rows = db_session.scalars(select(AuditLog)).all()
    assert len(rows) == 1
    assert rows[0].action == "login"


def test_write_audit_records_entity(db_session):
    write_audit(db_session, user_id=1, action="edit_plate", entity_type="reading", entity_id="7", detail="fix")
    db_session.commit()
    row = db_session.scalars(select(AuditLog)).one()
    assert row.entity_type == "reading"
    assert row.entity_id == "7"
    assert row.detail == "fix"
