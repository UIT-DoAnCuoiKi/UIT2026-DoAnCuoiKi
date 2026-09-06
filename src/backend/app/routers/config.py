from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import admin_only, get_current_user
from app.models import FeatureToggle, Lane, LaneCamera, PriceRule, User, VehicleGroup
from app.schemas.config import (
    LaneCameraIn, LaneCameraOut, LaneCameraUpdate, LaneIn, LaneOut, LaneUpdate,
    PriceRuleIn, PriceRuleOut, PriceRuleUpdate, ToggleOut, ToggleUpdate,
)

router = APIRouter(tags=["config"])


@router.get("/price-rules", response_model=list[PriceRuleOut])
def list_price_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(PriceRule).order_by(PriceRule.id)).all())


@router.post("/price-rules", response_model=PriceRuleOut, status_code=status.HTTP_201_CREATED)
def create_price_rule(body: PriceRuleIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if body.mode not in ("flat", "block"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode phải là flat hoặc block")
    if body.mode == "block" and not body.block_minutes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode block cần block_minutes > 0")
    if not db.scalars(select(VehicleGroup).where(VehicleGroup.code == body.vehicle_group)).first():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "vehicle_group không tồn tại")
    rule = PriceRule(**body.model_dump(), updated_by=admin.id)
    db.add(rule); db.commit(); db.refresh(rule)
    return rule


@router.patch("/price-rules/{rule_id}", response_model=PriceRuleOut)
def update_price_rule(rule_id: int, body: PriceRuleUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    rule = db.get(PriceRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bảng giá")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    if rule.mode == "block" and not rule.block_minutes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode block cần block_minutes > 0")
    rule.updated_by = admin.id
    db.commit(); db.refresh(rule)
    return rule


def _lane_out(db: Session, lane: Lane) -> LaneOut:
    cameras = list(db.scalars(select(LaneCamera).where(LaneCamera.lane_id == lane.id).order_by(LaneCamera.id)).all())
    return LaneOut(
        id=lane.id, name=lane.name, rtsp_url=lane.rtsp_url, active=lane.active,
        recognition_mode=lane.recognition_mode,
        cameras=[LaneCameraOut.model_validate(c) for c in cameras],
    )


@router.get("/lanes", response_model=list[LaneOut])
def list_lanes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lanes = list(db.scalars(select(Lane).order_by(Lane.id)).all())
    return [_lane_out(db, lane) for lane in lanes]


@router.post("/lanes", response_model=LaneOut, status_code=status.HTTP_201_CREATED)
def create_lane(body: LaneIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lane = Lane(**body.model_dump())
    db.add(lane); db.commit(); db.refresh(lane)
    return _lane_out(db, lane)


@router.patch("/lanes/{lane_id}", response_model=LaneOut)
def update_lane(lane_id: int, body: LaneUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lane = db.get(Lane, lane_id)
    if lane is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy lane")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lane, field, value)
    db.commit(); db.refresh(lane)
    return _lane_out(db, lane)


@router.get("/lanes/{lane_id}/cameras", response_model=list[LaneCameraOut])
def list_lane_cameras(lane_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.get(Lane, lane_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy lane")
    return list(db.scalars(select(LaneCamera).where(LaneCamera.lane_id == lane_id).order_by(LaneCamera.id)).all())


@router.post("/lanes/{lane_id}/cameras", response_model=LaneCameraOut, status_code=status.HTTP_201_CREATED)
def create_lane_camera(lane_id: int, body: LaneCameraIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.get(Lane, lane_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy lane")
    if body.source_kind not in ("browser", "rtsp"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "source_kind phải là browser hoặc rtsp")
    if body.source_kind == "rtsp" and not body.rtsp_url:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "source_kind rtsp cần rtsp_url")
    cam = LaneCamera(lane_id=lane_id, **body.model_dump())
    db.add(cam); db.commit(); db.refresh(cam)
    return cam


@router.patch("/lane-cameras/{camera_id}", response_model=LaneCameraOut)
def update_lane_camera(camera_id: int, body: LaneCameraUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    cam = db.get(LaneCamera, camera_id)
    if cam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy camera")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cam, field, value)
    db.commit(); db.refresh(cam)
    return cam


@router.delete("/lane-cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lane_camera(camera_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    cam = db.get(LaneCamera, camera_id)
    if cam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy camera")
    db.delete(cam); db.commit()


def _get_or_create_toggle(db: Session) -> FeatureToggle:
    toggle = db.scalars(select(FeatureToggle).order_by(FeatureToggle.id)).first()
    if toggle is None:
        toggle = FeatureToggle()
        db.add(toggle); db.commit(); db.refresh(toggle)
    return toggle


@router.get("/feature-toggles", response_model=ToggleOut)
def get_toggles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_or_create_toggle(db)


@router.patch("/feature-toggles", response_model=ToggleOut)
def update_toggles(body: ToggleUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    toggle = _get_or_create_toggle(db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(toggle, field, value)
    db.commit(); db.refresh(toggle)
    return toggle
