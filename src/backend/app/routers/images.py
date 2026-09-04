from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import ImageAsset, User
from app.security import crypto
from app.services.audit import write_audit

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    asset = db.get(ImageAsset, image_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy ảnh")
    with open(asset.path, "rb") as f:
        raw = crypto.decrypt_bytes(f.read()) if asset.encrypted else f.read()
    write_audit(db, user_id=user.id, action="view_image", entity_type="image", entity_id=str(image_id))
    db.commit()
    return Response(content=raw, media_type="image/jpeg")
