from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_edge_key
from app.models import PlateReading, User
from app.schemas.capture import CaptureResponse, PipelinePayload
from app.security import crypto
from app.services.capture_ingest import build_capture_response, ingest_reading
from app.services.inference import InferenceEngine, get_inference_engine

router = APIRouter(tags=["captures"])


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
    data = PipelinePayload.model_validate_json(payload)
    raw = image.file.read()
    reading, plate_text, duplicate = ingest_reading(
        db, capture_id=capture_id, direction=direction, lane=lane, payload=data, image_bytes=raw,
    )
    return build_capture_response(reading, plate_text, duplicate)


@router.post("/captures/infer", response_model=CaptureResponse)
def infer_capture(
    capture_id: str = Form(...),
    direction: str = Form(...),
    lane: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
    user: User = Depends(get_current_user),
) -> CaptureResponse:
    if direction not in ("in", "out"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "direction phải là in hoặc out")
    raw = image.file.read()
    payload = engine.infer(raw)
    reading, plate_text, duplicate = ingest_reading(
        db, capture_id=capture_id, direction=direction, lane=lane, payload=payload, image_bytes=raw,
    )
    return build_capture_response(reading, plate_text, duplicate)


@router.get("/captures/latest", response_model=CaptureResponse | None)
def latest_capture(lane: str | None = None, db: Session = Depends(get_db)) -> CaptureResponse | None:
    stmt = select(PlateReading).order_by(PlateReading.id.desc())
    if lane:
        stmt = stmt.where(PlateReading.lane == lane)
    reading = db.scalars(stmt.limit(1)).first()
    if reading is None:
        return None
    text = crypto.decrypt_text(reading.plate_text_ciphertext) if reading.plate_text_ciphertext else None
    return build_capture_response(reading, text, duplicate=False)
