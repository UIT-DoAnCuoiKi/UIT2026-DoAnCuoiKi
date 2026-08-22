from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import FeatureToggle, Lane, PriceRule, User
from app.schemas.config import (
    LaneIn, LaneOut, LaneUpdate, PriceRuleIn, PriceRuleOut, PriceRuleUpdate, ToggleOut, ToggleUpdate,
)

router = APIRouter(tags=["config"])
admin_only = require_role("admin")


@router.get("/price-rules", response_model=list[PriceRuleOut])
def list_price_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(PriceRule).order_by(PriceRule.id)).all())


@router.post("/price-rules", response_model=PriceRuleOut, status_code=status.HTTP_201_CREATED)
def create_price_rule(body: PriceRuleIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if body.mode not in ("flat", "block"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode phải là flat hoặc block")
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
    rule.updated_by = admin.id
    db.commit(); db.refresh(rule)
    return rule


@router.get("/lanes", response_model=list[LaneOut])
def list_lanes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Lane).order_by(Lane.id)).all())


@router.post("/lanes", response_model=LaneOut, status_code=status.HTTP_201_CREATED)
def create_lane(body: LaneIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lane = Lane(**body.model_dump())
    db.add(lane); db.commit(); db.refresh(lane)
    return lane


@router.patch("/lanes/{lane_id}", response_model=LaneOut)
def update_lane(lane_id: int, body: LaneUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    lane = db.get(Lane, lane_id)
    if lane is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy lane")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lane, field, value)
    db.commit(); db.refresh(lane)
    return lane


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
