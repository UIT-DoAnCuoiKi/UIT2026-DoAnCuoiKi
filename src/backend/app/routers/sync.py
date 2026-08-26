from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_edge_key, require_role
from app.models import FeatureToggle, ParkingSession, PriceRule, User
from app.schemas.sync import SyncPushIn, SyncPushOut
from app.security.plate import plate_hash
from app.services.sync import upsert_session_from_sync

router = APIRouter(tags=["sync"])


@router.post("/sync/push", response_model=SyncPushOut, dependencies=[Depends(require_edge_key)])
def push(body: SyncPushIn, db: Session = Depends(get_db)) -> SyncPushOut:
    count = 0
    for item in body.items:
        if item.entity_type == "session":
            upsert_session_from_sync(db, item.payload)
            count += 1
    return SyncPushOut(upserted=count)


@router.get("/sync/config", dependencies=[Depends(require_edge_key)])
def config(db: Session = Depends(get_db)) -> dict:
    rules = db.scalars(select(PriceRule).order_by(PriceRule.id)).all()
    toggle = db.scalars(select(FeatureToggle).order_by(FeatureToggle.id)).first()
    return {
        "price_rules": [
            {"vehicle_group": r.vehicle_group, "mode": r.mode, "unit_price": r.unit_price,
             "block_minutes": r.block_minutes, "active": r.active}
            for r in rules
        ],
        "feature_toggles": {
            "read_plate": toggle.read_plate if toggle else True,
            "plate_color": toggle.plate_color if toggle else True,
            "vehicle_class": toggle.vehicle_class if toggle else True,
        },
    }


central_admin = require_role("manager", "root")


@router.get("/central/sessions")
def central_sessions(
    lot_id: int | None = Query(None),
    plate: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(central_admin),
) -> list[dict]:
    stmt = select(ParkingSession)
    if lot_id is not None:
        stmt = stmt.where(ParkingSession.lot_id == lot_id)
    if plate:
        stmt = stmt.where(ParkingSession.plate_hash == plate_hash(plate))
    rows = db.scalars(stmt.order_by(ParkingSession.id.desc()).limit(limit)).all()
    return [
        {"uuid": s.uuid, "lot_id": s.lot_id, "status": s.status,
         "vehicle_group": s.vehicle_group, "fee_amount": s.fee_amount,
         "entry_time": s.entry_time.isoformat() if s.entry_time else None,
         "exit_time": s.exit_time.isoformat() if s.exit_time else None}
        for s in rows
    ]
