from sqlalchemy import select

from app.models import AuditLog
from app.services.image_store import store_encrypted_image


def test_view_image_decrypts_and_audits(client, db_session, staff_headers, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    asset = store_encrypted_image(db_session, b"\xff\xd8\xff raw", "in")
    db_session.commit()

    r = client.get(f"/images/{asset.id}", headers=staff_headers)
    assert r.status_code == 200
    assert r.content == b"\xff\xd8\xff raw"

    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "view_image")).all()
    assert len(logs) == 1


def test_view_image_requires_auth(client, db_session, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))
    asset = store_encrypted_image(db_session, b"x", "in")
    db_session.commit()
    assert client.get(f"/images/{asset.id}").status_code in (401, 403)
