from app.db import SessionLocal
from app.services.retention import purge_expired


def main() -> None:
    db = SessionLocal()
    try:
        n = purge_expired(db)
        print(f"purged {n} sessions")
    finally:
        db.close()


if __name__ == "__main__":
    main()
