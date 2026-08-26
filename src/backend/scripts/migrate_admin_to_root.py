from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User


def migrate_admin_to_root(db: Session) -> int:
    users = list(db.scalars(select(User).where(User.role == "admin")).all())
    for u in users:
        u.role = "root"
    db.commit()
    return len(users)


def main() -> None:
    db = SessionLocal()
    try:
        n = migrate_admin_to_root(db)
        print(f"đã đổi {n} tài khoản admin sang root")
    finally:
        db.close()


if __name__ == "__main__":
    main()
