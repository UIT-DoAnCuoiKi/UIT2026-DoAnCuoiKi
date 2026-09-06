from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_edge_key
from app.models import Lane, PlateReading, User
from app.schemas.capture import CaptureResponse, PipelinePayload
from app.security import crypto
from app.services.capture import select_representative
from app.services.capture_ingest import build_capture_response, ingest_reading
from app.services.inference import InferenceEngine, get_inference_engine

router = APIRouter(tags=["captures"])


def _zip_extra_images(extra_images: list[UploadFile], extra_roles: list[str]) -> list[tuple[bytes, str]]:
    """Ảnh camera phụ (vd cam sau xe) — chỉ lưu làm bằng chứng, không nhận dạng
    lại. `extra_images`/`extra_roles` là 2 danh sách multipart song song; lệch
    độ dài là lỗi client (thiếu vai trò cho 1 ảnh nào đó), không nên đoán."""
    if not extra_images:
        return []
    if len(extra_images) != len(extra_roles):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "số ảnh phụ (extra_images) và số vai trò (extra_roles) phải bằng nhau",
        )
    return [(f.file.read(), role) for f, role in zip(extra_images, extra_roles)]


def _ocr_conf(payload: PipelinePayload) -> float:
    rep = select_representative(payload.plates)
    return rep.ocr_conf if rep and rep.ocr_conf is not None else -1.0


def _apply_recognition_mode(
    engine: InferenceEngine, lane: str | None, db: Session,
    raw: bytes, primary_role: str, extras: list[tuple[bytes, str]],
) -> tuple[PipelinePayload, bytes, str, list[tuple[bytes, str]]]:
    """Chạy nhận dạng theo cấu hình của làn.

    Mặc định (`primary`, hoặc không có ảnh phụ): chỉ nhận dạng ảnh chính, ảnh phụ
    chỉ lưu làm bằng chứng — đúng hành vi cũ, 1 lần suy luận.

    `best_of`: nhận dạng CẢ ảnh chính lẫn ảnh phụ đầu tiên (vd ô tô có biển cả
    trước lẫn sau), lấy ảnh cho ocr_conf cao hơn làm ảnh "chính" thật sự — vì
    một camera có thể bị khuất/lóa mà camera còn lại vẫn đọc được. Trả về đã
    hoán vị đúng: image_bytes/role của ảnh thắng cuộc, phần còn lại dồn vào extras.
    """
    payload = engine.infer(raw)
    if not lane or not extras:
        return payload, raw, primary_role, extras

    lane_row = db.scalars(select(Lane).where(Lane.name == lane)).first()
    if lane_row is None or lane_row.recognition_mode != "best_of":
        return payload, raw, primary_role, extras

    extra_bytes, extra_role = extras[0]
    extra_payload = engine.infer(extra_bytes)
    if _ocr_conf(extra_payload) <= _ocr_conf(payload):
        return payload, raw, primary_role, extras

    # Ảnh phụ đọc tốt hơn: hoán vị vai trò, ảnh chính cũ lùi xuống làm ảnh phụ.
    new_extras = [(raw, primary_role), *extras[1:]]
    return extra_payload, extra_bytes, extra_role, new_extras


@router.post("/captures", response_model=CaptureResponse, dependencies=[Depends(require_edge_key)])
def ingest_capture(
    capture_id: str = Form(...),
    direction: str = Form(...),
    payload: str = Form(...),
    lane: str | None = Form(None),
    image: UploadFile = File(...),
    primary_role: str = Form("front"),
    extra_images: list[UploadFile] = File(default=[]),
    extra_roles: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
) -> CaptureResponse:
    if direction not in ("in", "out"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "direction phải là in hoặc out")
    data = PipelinePayload.model_validate_json(payload)
    raw = image.file.read()
    reading, plate_text, duplicate = ingest_reading(
        db, capture_id=capture_id, direction=direction, lane=lane, payload=data, image_bytes=raw,
        primary_role=primary_role, extra_images=_zip_extra_images(extra_images, extra_roles),
    )
    return build_capture_response(db, reading, plate_text, duplicate)


@router.post("/captures/infer", response_model=CaptureResponse)
def infer_capture(
    capture_id: str = Form(...),
    direction: str = Form(...),
    lane: str | None = Form(None),
    image: UploadFile = File(...),
    primary_role: str = Form("front"),
    extra_images: list[UploadFile] = File(default=[]),
    extra_roles: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
    user: User = Depends(get_current_user),
) -> CaptureResponse:
    if direction not in ("in", "out"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "direction phải là in hoặc out")
    raw = image.file.read()
    extras = _zip_extra_images(extra_images, extra_roles)
    payload, raw, primary_role, extras = _apply_recognition_mode(engine, lane, db, raw, primary_role, extras)
    reading, plate_text, duplicate = ingest_reading(
        db, capture_id=capture_id, direction=direction, lane=lane, payload=payload, image_bytes=raw,
        primary_role=primary_role, extra_images=extras,
    )
    return build_capture_response(db, reading, plate_text, duplicate)


@router.get("/captures/latest", response_model=CaptureResponse | None)
def latest_capture(lane: str | None = None, db: Session = Depends(get_db)) -> CaptureResponse | None:
    stmt = select(PlateReading).order_by(PlateReading.id.desc())
    if lane:
        stmt = stmt.where(PlateReading.lane == lane)
    reading = db.scalars(stmt.limit(1)).first()
    if reading is None:
        return None
    text = crypto.decrypt_text(reading.plate_text_ciphertext) if reading.plate_text_ciphertext else None
    return build_capture_response(db, reading, text, duplicate=False)
