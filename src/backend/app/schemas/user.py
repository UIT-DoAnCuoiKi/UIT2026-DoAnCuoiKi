from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # staff | admin


class UserUpdate(BaseModel):
    active: bool | None = None
    role: str | None = None
    password: str | None = None


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    active: bool

    model_config = {"from_attributes": True}
