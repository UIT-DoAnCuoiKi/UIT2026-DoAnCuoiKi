import hashlib
import os
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ImageAsset
from app.security import crypto


def store_encrypted_image(db: Session, raw: bytes, direction: str | None) -> ImageAsset:
    os.makedirs(settings.image_storage_dir, exist_ok=True)
    path = os.path.join(settings.image_storage_dir, f"{uuid.uuid4().hex}.enc")
    with open(path, "wb") as f:
        f.write(crypto.encrypt_bytes(raw))
    asset = ImageAsset(
        path=path,
        encrypted=True,
        sha256=hashlib.sha256(raw).hexdigest(),
        direction=direction,
        retention_delete_after=None,  # đặt khi xe ra; job xóa Phase 5 tính theo exit_time
    )
    db.add(asset)
    db.flush()
    return asset
