"""Seed danh mục vehicle_group cho deployment hiện có (idempotent)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.services.vehicle_groups import seed_default_vehicle_groups  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        n = seed_default_vehicle_groups(db)
        print(f"Seed vehicle_group: thêm {n} nhóm")
    finally:
        db.close()


if __name__ == "__main__":
    main()
