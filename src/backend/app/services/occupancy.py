from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ParkingLot, ParkingSession, Zone


def lot_occupancy(db: Session, lot_id: int) -> int:
    return int(db.scalar(
        select(func.count()).select_from(ParkingSession).where(
            ParkingSession.status == "in_lot", ParkingSession.lot_id == lot_id,
        )
    ) or 0)


def zone_occupancy(db: Session, zone_id: int) -> int:
    return int(db.scalar(
        select(func.count()).select_from(ParkingSession).where(
            ParkingSession.status == "in_lot", ParkingSession.zone_id == zone_id,
        )
    ) or 0)


def lot_is_full(db: Session, lot_id: int) -> bool:
    lot = db.get(ParkingLot, lot_id)
    if lot is None or lot.capacity <= 0:
        return False
    return lot_occupancy(db, lot_id) >= lot.capacity


def resolve_default_lot(db: Session) -> int | None:
    """Bãi để gán cho phiên khi màn cổng không gửi zone_id.

    Màn cổng hiện không có ô chọn khu (đúng phạm vi MVP 1 làn), nên nếu không
    suy ra bãi ở đây thì phiên sẽ có lot_id rỗng: vừa không kiểm được sức chứa,
    vừa biến mất khỏi báo cáo occupancy vốn lọc theo lot_id.

    Chỉ suy ra khi có đúng một bãi đang hoạt động. Nhiều bãi thì trả None để
    bắt buộc gửi zone_id, không đoán bừa xe thuộc bãi nào.
    """
    lots = list(db.scalars(select(ParkingLot).where(ParkingLot.active.is_(True)).limit(2)).all())
    return lots[0].id if len(lots) == 1 else None


def _available(capacity: int, occupancy: int) -> int | None:
    return max(capacity - occupancy, 0) if capacity > 0 else None


def occupancy_report(db: Session) -> list[dict]:
    report: list[dict] = []
    for lot in db.scalars(select(ParkingLot).order_by(ParkingLot.id)).all():
        occ = lot_occupancy(db, lot.id)
        zones = []
        for z in db.scalars(select(Zone).where(Zone.lot_id == lot.id).order_by(Zone.id)).all():
            zocc = zone_occupancy(db, z.id)
            zones.append({
                "zone_id": z.id, "floor_id": z.floor_id, "name": z.name,
                "capacity": z.capacity, "occupancy": zocc, "available": _available(z.capacity, zocc),
            })
        report.append({
            "lot_id": lot.id, "name": lot.name, "capacity": lot.capacity,
            "occupancy": occ, "available": _available(lot.capacity, occ),
            "full": lot.capacity > 0 and occ >= lot.capacity, "zones": zones,
        })
    return report
