from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_utc, to_naive
from app.models import Device


def _is_online(dev: Device, stale_seconds: int) -> bool:
    if dev.last_heartbeat is None:
        return False
    delta = to_naive(now_utc()) - to_naive(dev.last_heartbeat)
    return delta <= timedelta(seconds=stale_seconds)


def record_heartbeat(db: Session, device: Device) -> Device:
    device.last_heartbeat = now_utc()
    device.status = "online"
    db.commit(); db.refresh(device)
    return device


def device_health(db: Session, stale_seconds: int = 60) -> list[dict]:
    rows = []
    for dev in db.scalars(select(Device).order_by(Device.id)).all():
        rows.append({
            "device_id": dev.id, "name": dev.name, "kind": dev.kind,
            "status": dev.status, "last_heartbeat": dev.last_heartbeat,
            "online": _is_online(dev, stale_seconds),
        })
    return rows
