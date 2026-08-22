from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.security.passwords import hash_password


def seed_admin(db: Session) -> bool:
    if not settings.admin_password:
        return False
    if db.scalars(select(User).where(User.username == settings.admin_username)).first():
        return False
    db.add(User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        role="admin",
        active=True,
    ))
    db.commit()
    return True


def main() -> None:
    db = SessionLocal()
    try:
        created = seed_admin(db)
        print("đã tạo admin" if created else "bỏ qua seed admin")
    finally:
        db.close()


if __name__ == "__main__":
    main()
