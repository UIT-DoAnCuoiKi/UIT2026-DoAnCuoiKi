from pydantic import BaseModel


class PriceRuleIn(BaseModel):
    vehicle_group: str
    mode: str  # flat | block
    unit_price: int
    block_minutes: int | None = None
    grace_minutes: int = 0
    daily_cap: int | None = None
    active: bool = True


class PriceRuleUpdate(BaseModel):
    mode: str | None = None
    unit_price: int | None = None
    block_minutes: int | None = None
    grace_minutes: int | None = None
    daily_cap: int | None = None
    active: bool | None = None


class PriceRuleOut(BaseModel):
    id: int
    vehicle_group: str
    mode: str
    unit_price: int
    block_minutes: int | None = None
    grace_minutes: int = 0
    daily_cap: int | None = None
    active: bool
    model_config = {"from_attributes": True}


class LaneIn(BaseModel):
    name: str
    rtsp_url: str | None = None
    active: bool = True
    recognition_mode: str = "primary"  # primary | best_of


class LaneUpdate(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    active: bool | None = None
    recognition_mode: str | None = None


class LaneCameraIn(BaseModel):
    role: str  # front | rear | overview
    source_kind: str  # browser | rtsp
    device_id: str | None = None
    rtsp_url: str | None = None
    is_primary: bool = False
    active: bool = True


class LaneCameraUpdate(BaseModel):
    role: str | None = None
    source_kind: str | None = None
    device_id: str | None = None
    rtsp_url: str | None = None
    is_primary: bool | None = None
    active: bool | None = None


class LaneCameraOut(BaseModel):
    id: int
    lane_id: int
    role: str
    source_kind: str
    device_id: str | None = None
    rtsp_url: str | None = None
    is_primary: bool
    active: bool
    model_config = {"from_attributes": True}


class LaneOut(BaseModel):
    id: int
    name: str
    rtsp_url: str | None = None
    active: bool
    recognition_mode: str = "primary"
    cameras: list[LaneCameraOut] = []
    model_config = {"from_attributes": True}


class ToggleUpdate(BaseModel):
    read_plate: bool | None = None
    plate_color: bool | None = None
    vehicle_class: bool | None = None
    dev_mode: bool | None = None


class ToggleOut(BaseModel):
    read_plate: bool
    plate_color: bool
    vehicle_class: bool
    dev_mode: bool
