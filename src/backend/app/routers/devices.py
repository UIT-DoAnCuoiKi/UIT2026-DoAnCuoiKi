from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import BarrierEvent, Device, User
from app.schemas.barrier import BarrierEventOut, BarrierOpenIn
from app.schemas.device import DeviceHealthOut, DeviceIn, DeviceOut
from app.services.audit import write_audit
from app.services.device import device_health, record_heartbeat

router = APIRouter(tags=["devices"])
admin_only = require_role("admin")


@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(body: DeviceIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    device = Device(**body.model_dump())
    db.add(device); db.commit(); db.refresh(device)
    return device


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Device).order_by(Device.id)).all())


@router.post("/devices/{device_id}/heartbeat", response_model=DeviceOut)
def heartbeat(device_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy thiết bị")
    return record_heartbeat(db, device)


@router.get("/devices/health", response_model=list[DeviceHealthOut])
def health(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return device_health(db)


@router.post("/barrier/open", response_model=BarrierEventOut, status_code=status.HTTP_201_CREATED)
def open_barrier(body: BarrierOpenIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.mode not in ("auto", "manual", "emergency"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode không hợp lệ")
    if body.mode in ("manual", "emergency") and not body.reason:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mở tay và khẩn cấp cần lý do")

    event = BarrierEvent(
        device_id=body.device_id, session_id=body.session_id,
        action="open", mode=body.mode, reason=body.reason, user_id=user.id,
    )
    db.add(event)
    if body.mode in ("manual", "emergency"):
        write_audit(
            db, user_id=user.id, action="barrier_open", entity_type="barrier",
            entity_id=str(body.device_id) if body.device_id else None,
            detail=f"mode={body.mode} reason={body.reason}",
        )
    db.commit(); db.refresh(event)
    return event


@router.get("/barrier/events", response_model=list[BarrierEventOut])
def list_barrier_events(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(
        select(BarrierEvent).order_by(BarrierEvent.id.desc()).limit(limit)
    ).all())
