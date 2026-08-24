from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import Floor, ParkingLot, User, Zone
from app.schemas.space import (
    FloorIn, FloorOut, FloorUpdate, LotIn, LotOut, LotUpdate, ZoneIn, ZoneOut, ZoneUpdate,
)
from app.services.occupancy import occupancy_report

router = APIRouter(tags=["spaces"])
admin_only = require_role("admin")


@router.get("/lots", response_model=list[LotOut])
def list_lots(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(ParkingLot).order_by(ParkingLot.id)).all())


@router.post("/lots", response_model=LotOut, status_code=status.HTTP_201_CREATED)
def create_lot(body: LotIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lot = ParkingLot(**body.model_dump())
    db.add(lot); db.commit(); db.refresh(lot)
    return lot


@router.patch("/lots/{lot_id}", response_model=LotOut)
def update_lot(lot_id: int, body: LotUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lot = db.get(ParkingLot, lot_id)
    if lot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bãi")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lot, field, value)
    db.commit(); db.refresh(lot)
    return lot


@router.get("/floors", response_model=list[FloorOut])
def list_floors(lot_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Floor).order_by(Floor.id)
    if lot_id is not None:
        stmt = stmt.where(Floor.lot_id == lot_id)
    return list(db.scalars(stmt).all())


@router.post("/floors", response_model=FloorOut, status_code=status.HTTP_201_CREATED)
def create_floor(body: FloorIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.get(ParkingLot, body.lot_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bãi")
    floor = Floor(**body.model_dump())
    db.add(floor); db.commit(); db.refresh(floor)
    return floor


@router.patch("/floors/{floor_id}", response_model=FloorOut)
def update_floor(floor_id: int, body: FloorUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    floor = db.get(Floor, floor_id)
    if floor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy tầng")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(floor, field, value)
    db.commit(); db.refresh(floor)
    return floor


@router.get("/zones", response_model=list[ZoneOut])
def list_zones(lot_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Zone).order_by(Zone.id)
    if lot_id is not None:
        stmt = stmt.where(Zone.lot_id == lot_id)
    return list(db.scalars(stmt).all())


@router.post("/zones", response_model=ZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(body: ZoneIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.get(ParkingLot, body.lot_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy bãi")
    zone = Zone(**body.model_dump())
    db.add(zone); db.commit(); db.refresh(zone)
    return zone


@router.patch("/zones/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, body: ZoneUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy khu")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(zone, field, value)
    db.commit(); db.refresh(zone)
    return zone


@router.get("/occupancy")
def get_occupancy(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"lots": occupancy_report(db)}
