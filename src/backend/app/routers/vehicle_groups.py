from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import admin_only, get_current_user
from app.models import MonthlyPass, ParkingSession, PriceRule, User, VehicleGroup
from app.schemas.vehicle_group import VehicleGroupIn, VehicleGroupOut, VehicleGroupUpdate

router = APIRouter(prefix="/vehicle-groups", tags=["vehicle-groups"])


@router.get("", response_model=list[VehicleGroupOut])
def list_vehicle_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(VehicleGroup).order_by(VehicleGroup.sort_order, VehicleGroup.id)).all())


@router.post("", response_model=VehicleGroupOut, status_code=status.HTTP_201_CREATED)
def create_vehicle_group(body: VehicleGroupIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.scalars(select(VehicleGroup).where(VehicleGroup.code == body.code)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "code đã tồn tại")
    group = VehicleGroup(**body.model_dump())
    db.add(group); db.commit(); db.refresh(group)
    return group


@router.patch("/{group_id}", response_model=VehicleGroupOut)
def update_vehicle_group(group_id: int, body: VehicleGroupUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    group = db.get(VehicleGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy nhóm")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(group, field, value)
    db.commit(); db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_group(group_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    group = db.get(VehicleGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy nhóm")
    referenced = (
        db.scalars(select(ParkingSession.id).where(ParkingSession.vehicle_group == group.code).limit(1)).first()
        or db.scalars(select(PriceRule.id).where(PriceRule.vehicle_group == group.code).limit(1)).first()
        or db.scalars(select(MonthlyPass.id).where(MonthlyPass.vehicle_group == group.code).limit(1)).first()
    )
    if referenced is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "nhóm đang được sử dụng")
    db.delete(group); db.commit()
