from pydantic import BaseModel


class LotIn(BaseModel):
    name: str
    address: str | None = None
    capacity: int = 0
    active: bool = True


class LotUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    capacity: int | None = None
    active: bool | None = None


class LotOut(BaseModel):
    id: int
    name: str
    address: str | None = None
    capacity: int
    active: bool
    model_config = {"from_attributes": True}


class FloorIn(BaseModel):
    lot_id: int
    name: str
    capacity: int = 0
    active: bool = True


class FloorUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    active: bool | None = None


class FloorOut(BaseModel):
    id: int
    lot_id: int
    name: str
    capacity: int
    active: bool
    model_config = {"from_attributes": True}


class ZoneIn(BaseModel):
    lot_id: int
    floor_id: int | None = None
    name: str
    capacity: int = 0
    active: bool = True


class ZoneUpdate(BaseModel):
    name: str | None = None
    floor_id: int | None = None
    capacity: int | None = None
    active: bool | None = None


class ZoneOut(BaseModel):
    id: int
    lot_id: int
    floor_id: int | None = None
    name: str
    capacity: int
    active: bool
    model_config = {"from_attributes": True}
