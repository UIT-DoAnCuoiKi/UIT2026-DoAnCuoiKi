from pydantic import BaseModel


class VehicleGroupIn(BaseModel):
    code: str
    display_name: str
    sort_order: int = 0
    active: bool = True


class VehicleGroupUpdate(BaseModel):
    display_name: str | None = None
    sort_order: int | None = None
    active: bool | None = None


class VehicleGroupOut(BaseModel):
    id: int
    code: str
    display_name: str
    active: bool
    sort_order: int
    model_config = {"from_attributes": True}
