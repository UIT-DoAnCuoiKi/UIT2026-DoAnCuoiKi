from pydantic import BaseModel


class PriceRuleIn(BaseModel):
    vehicle_group: str
    mode: str  # flat | block
    unit_price: int
    block_minutes: int | None = None
    active: bool = True


class PriceRuleUpdate(BaseModel):
    mode: str | None = None
    unit_price: int | None = None
    block_minutes: int | None = None
    active: bool | None = None


class PriceRuleOut(BaseModel):
    id: int
    vehicle_group: str
    mode: str
    unit_price: int
    block_minutes: int | None = None
    active: bool
    model_config = {"from_attributes": True}


class LaneIn(BaseModel):
    name: str
    rtsp_url: str | None = None
    active: bool = True


class LaneUpdate(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    active: bool | None = None


class LaneOut(BaseModel):
    id: int
    name: str
    rtsp_url: str | None = None
    active: bool
    model_config = {"from_attributes": True}


class ToggleUpdate(BaseModel):
    read_plate: bool | None = None
    plate_color: bool | None = None
    vehicle_class: bool | None = None


class ToggleOut(BaseModel):
    read_plate: bool
    plate_color: bool
    vehicle_class: bool
