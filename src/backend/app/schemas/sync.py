from pydantic import BaseModel


class SyncItem(BaseModel):
    entity_type: str
    payload: dict


class SyncPushIn(BaseModel):
    items: list[SyncItem]


class SyncPushOut(BaseModel):
    upserted: int
