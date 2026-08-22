import hashlib
from pathlib import Path

from app.security import crypto
from app.services.image_store import store_encrypted_image


def test_store_encrypts_and_hashes(db_session, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "image_storage_dir", str(tmp_path))

    raw = b"\xff\xd8\xff fake jpeg bytes"
    asset = store_encrypted_image(db_session, raw, direction="in")
    db_session.commit()

    assert asset.id is not None
    assert asset.encrypted is True
    assert asset.direction == "in"
    assert asset.sha256 == hashlib.sha256(raw).hexdigest()

    stored = Path(asset.path).read_bytes()
    assert stored != raw
    assert crypto.decrypt_bytes(stored) == raw
