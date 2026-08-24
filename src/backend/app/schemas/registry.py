from datetime import date

from pydantic import BaseModel


class OwnerIn(BaseModel):
    name: str
    phone: str | None = None
    plate_text: str


class OwnerOut(BaseModel):
    id: int
    name: str
    phone: str | None = None
    plate_text: str


class MonthlyPassIn(BaseModel):
    plate_text: str
    vehicle_group: str
    start_date: date
    end_date: date
    owner_id: int | None = None
    active: bool = True


class MonthlyPassOut(BaseModel):
    id: int
    plate_text: str
    vehicle_group: str
    start_date: date
    end_date: date
    owner_id: int | None = None
    active: bool


class PlateListIn(BaseModel):
    plate_text: str
    reason: str | None = None
    active: bool = True


class PlateListOut(BaseModel):
    id: int
    plate_text: str
    reason: str | None = None
    active: bool
