from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_edge_key
from app.models import PlateReading
from app.schemas.capture import CaptureResponse, PipelinePayload
from app.security import crypto
from app.security.plate import plate_hash
from app.services.capture import compute_review_state, select_representative
from app.services.gate_hub import gate_hub
from app.services.image_store import store_encrypted_image
from app.services.vehicle_groups import group_for

router = APIRouter(tags=["captures"])


def _response(reading: PlateReading, plate_text: str | None, vehicle_group: str | None, duplicate: bool) -> CaptureResponse:
    return CaptureResponse(
        reading_id=reading.id,
        capture_id=reading.capture_id,
        direction=reading.direction,
        review_state=reading.review_state,
        plate_text=plate_text,
        plate_valid=reading.plate_valid,
        vehicle_type=reading.vehicle_type,
        vehicle_group=vehicle_group,
        color=reading.color,
        image_asset_id=reading.image_asset_id,
        duplicate=duplicate,
    )


@router.post("/captures", response_model=CaptureResponse, dependencies=[Depends(require_edge_key)])
def ingest_capture(
    capture_id: str = Form(...),
    direction: str = Form(...),
    payload: str = Form(...),
    lane: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CaptureResponse:
    if direction not in ("in", "out"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "direction phải là in hoặc out")

    existing = db.scalars(select(PlateReading).where(PlateReading.capture_id == capture_id)).first()
    if existing is not None:
        text = crypto.decrypt_text(existing.plate_text_ciphertext) if existing.plate_text_ciphertext else None
        return _response(existing, text, group_for(existing.vehicle_type), duplicate=True)

    data = PipelinePayload.model_validate_json(payload)
    raw = image.file.read()
    asset = store_encrypted_image(db, raw, direction)

    rep = select_representative(data.plates)
    plate_text = rep.plate_text if rep else None
    reading = PlateReading(
        capture_id=capture_id,
        direction=direction,
        lane=lane,
        plate_text_ciphertext=crypto.encrypt_text(plate_text) if plate_text else None,
        plate_hash=plate_hash(plate_text) if plate_text else None,
        plate_valid=rep.plate_valid if rep else None,
        det_conf=rep.det_conf if rep else None,
        ocr_conf=rep.ocr_conf if rep else None,
        layout=rep.layout if rep else None,
        color=rep.color if rep else None,
        color_conf=rep.color_conf if rep else None,
        vehicle_type=data.vehicle_type,
        vehicle_style=data.vehicle_style,
        vehicle_style_conf=data.vehicle_style_conf,
        raw_pipeline_json=data.model_dump(),
        image_asset_id=asset.id,
        review_state=compute_review_state(rep),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    gate_hub.publish({
        "reading_id": reading.id,
        "capture_id": reading.capture_id,
        "direction": reading.direction,
        "lane": reading.lane,
        "review_state": reading.review_state,
        "plate_text": plate_text,
        "vehicle_group": group_for(data.vehicle_type),
    })
    return _response(reading, plate_text, group_for(data.vehicle_type), duplicate=False)


@router.get("/captures/latest")
def latest_capture(lane: str | None = None, db: Session = Depends(get_db)) -> dict:
    stmt = select(PlateReading).order_by(PlateReading.id.desc())
    if lane:
        stmt = stmt.where(PlateReading.lane == lane)
    reading = db.scalars(stmt.limit(1)).first()
    if reading is None:
        return {}
    text = crypto.decrypt_text(reading.plate_text_ciphertext) if reading.plate_text_ciphertext else None
    return {
        "reading_id": reading.id,
        "capture_id": reading.capture_id,
        "direction": reading.direction,
        "lane": reading.lane,
        "review_state": reading.review_state,
        "plate_text": text,
        "vehicle_group": group_for(reading.vehicle_type),
    }
