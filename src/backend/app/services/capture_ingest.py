from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlateReading
from app.schemas.capture import CaptureResponse, PipelinePayload
from app.security import crypto
from app.security.plate import plate_hash
from app.services.capture import compute_review_state, select_representative
from app.services.gate_hub import gate_hub
from app.services.image_store import store_encrypted_image
from app.services.vehicle_groups import group_for


def build_capture_response(reading: PlateReading, plate_text: str | None, duplicate: bool) -> CaptureResponse:
    return CaptureResponse(
        reading_id=reading.id,
        capture_id=reading.capture_id,
        direction=reading.direction,
        lane=reading.lane,
        review_state=reading.review_state,
        plate_text=plate_text,
        plate_valid=reading.plate_valid,
        vehicle_type=reading.vehicle_type,
        vehicle_group=group_for(reading.vehicle_type),
        color=reading.color,
        image_asset_id=reading.image_asset_id,
        duplicate=duplicate,
    )


def ingest_reading(
    db: Session, *, capture_id: str, direction: str, lane: str | None,
    payload: PipelinePayload, image_bytes: bytes,
) -> tuple[PlateReading, str | None, bool]:
    existing = db.scalars(select(PlateReading).where(PlateReading.capture_id == capture_id)).first()
    if existing is not None:
        text = crypto.decrypt_text(existing.plate_text_ciphertext) if existing.plate_text_ciphertext else None
        return existing, text, True

    asset = store_encrypted_image(db, image_bytes, direction)
    rep = select_representative(payload.plates)
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
        vehicle_type=payload.vehicle_type,
        vehicle_style=payload.vehicle_style,
        vehicle_style_conf=payload.vehicle_style_conf,
        raw_pipeline_json=payload.model_dump(),
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
        "vehicle_group": group_for(payload.vehicle_type),
        "vehicle_type": reading.vehicle_type,
        "color": reading.color,
        "plate_valid": reading.plate_valid,
        "image_asset_id": reading.image_asset_id,
        "duplicate": False,
    })
    return reading, plate_text, False
