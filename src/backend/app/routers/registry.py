from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import MonthlyPass, PlateBlacklist, PlateWhitelist, User, VehicleOwner
from app.schemas.registry import (
    MonthlyPassIn, MonthlyPassOut, OwnerIn, OwnerOut, PlateListIn, PlateListOut,
)
from app.security import crypto
from app.security.plate import plate_hash

router = APIRouter(tags=["registry"])
admin_only = require_role("admin")


def _plate_fields(plate_text: str) -> dict:
    return {"plate_hash": plate_hash(plate_text), "plate_ciphertext": crypto.encrypt_text(plate_text)}


@router.post("/owners", response_model=OwnerOut, status_code=status.HTTP_201_CREATED)
def create_owner(body: OwnerIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    owner = VehicleOwner(name=body.name, phone=body.phone, **_plate_fields(body.plate_text))
    db.add(owner); db.commit(); db.refresh(owner)
    return OwnerOut(id=owner.id, name=owner.name, phone=owner.phone, plate_text=body.plate_text)


@router.get("/owners", response_model=list[OwnerOut])
def list_owners(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(VehicleOwner).order_by(VehicleOwner.id)).all()
    return [OwnerOut(id=o.id, name=o.name, phone=o.phone,
                     plate_text=crypto.decrypt_text(o.plate_ciphertext)) for o in rows]


@router.post("/monthly-passes", response_model=MonthlyPassOut, status_code=status.HTTP_201_CREATED)
def create_pass(body: MonthlyPassIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    mp = MonthlyPass(
        owner_id=body.owner_id, vehicle_group=body.vehicle_group,
        start_date=body.start_date, end_date=body.end_date, active=body.active,
        **_plate_fields(body.plate_text),
    )
    db.add(mp); db.commit(); db.refresh(mp)
    return MonthlyPassOut(id=mp.id, plate_text=body.plate_text, vehicle_group=mp.vehicle_group,
                          start_date=mp.start_date, end_date=mp.end_date, owner_id=mp.owner_id, active=mp.active)


@router.get("/monthly-passes", response_model=list[MonthlyPassOut])
def list_passes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(MonthlyPass).order_by(MonthlyPass.id)).all()
    return [MonthlyPassOut(id=p.id, plate_text=crypto.decrypt_text(p.plate_ciphertext),
                           vehicle_group=p.vehicle_group, start_date=p.start_date, end_date=p.end_date,
                           owner_id=p.owner_id, active=p.active) for p in rows]


def _list_out(rows) -> list[PlateListOut]:
    return [PlateListOut(id=r.id, plate_text=crypto.decrypt_text(r.plate_ciphertext),
                         reason=r.reason, active=r.active) for r in rows]


@router.post("/whitelist", response_model=PlateListOut, status_code=status.HTTP_201_CREATED)
def add_whitelist(body: PlateListIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    row = PlateWhitelist(reason=body.reason, active=body.active, **_plate_fields(body.plate_text))
    db.add(row); db.commit(); db.refresh(row)
    return PlateListOut(id=row.id, plate_text=body.plate_text, reason=row.reason, active=row.active)


@router.get("/whitelist", response_model=list[PlateListOut])
def list_whitelist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _list_out(db.scalars(select(PlateWhitelist).order_by(PlateWhitelist.id)).all())


@router.post("/blacklist", response_model=PlateListOut, status_code=status.HTTP_201_CREATED)
def add_blacklist(body: PlateListIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    row = PlateBlacklist(reason=body.reason, active=body.active, **_plate_fields(body.plate_text))
    db.add(row); db.commit(); db.refresh(row)
    return PlateListOut(id=row.id, plate_text=body.plate_text, reason=row.reason, active=row.active)


@router.get("/blacklist", response_model=list[PlateListOut])
def list_blacklist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _list_out(db.scalars(select(PlateBlacklist).order_by(PlateBlacklist.id)).all())
