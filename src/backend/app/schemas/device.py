from datetime import datetime

from pydantic import BaseModel


class DeviceIn(BaseModel):
    kind: str            # barrier | camera | led
    name: str
    lot_id: int | None = None
    lane: str | None = None


class DeviceOut(BaseModel):
    id: int
    lot_id: int | None = None
    kind: str
    name: str
    lane: str | None = None
    status: str
    last_heartbeat: datetime | None = None
    model_config = {"from_attributes": True}


class DeviceHealthOut(BaseModel):
    device_id: int
    name: str
    kind: str
    status: str
    last_heartbeat: datetime | None = None
    online: bool
