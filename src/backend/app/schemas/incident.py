from datetime import datetime

from pydantic import BaseModel


class IncidentIn(BaseModel):
    kind: str                       # collision | lost_vehicle | damage | other
    description: str | None = None
    lot_id: int | None = None
    session_id: int | None = None
    image_asset_id: int | None = None


class IncidentOut(BaseModel):
    id: int
    kind: str
    description: str | None = None
    lot_id: int | None = None
    session_id: int | None = None
    image_asset_id: int | None = None
    user_id: int | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
