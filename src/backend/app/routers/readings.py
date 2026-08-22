from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import PlateReading, User
from app.schemas.session import PlatePatch
from app.security import crypto
from app.security.plate import plate_hash
from app.services.audit import write_audit

router = APIRouter(prefix="/readings", tags=["readings"])


@router.patch("/{reading_id}/plate")
def patch_plate(reading_id: int, body: PlatePatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    reading = db.get(PlateReading, reading_id)
    if reading is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy reading")
    reading.plate_text_ciphertext = crypto.encrypt_text(body.plate_text)
    reading.plate_hash = plate_hash(body.plate_text)
    reading.review_state = "manual"
    write_audit(db, user_id=user.id, action="edit_plate", entity_type="reading", entity_id=str(reading.id))
    db.commit()
    return {"reading_id": reading.id, "plate_text": body.plate_text, "review_state": "manual"}
