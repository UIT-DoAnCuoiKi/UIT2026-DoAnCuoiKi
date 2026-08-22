from datetime import datetime, timezone


def now_utc() -> datetime:
    """UTC naive: nhất quán giữa SQLite (không lưu tz) và Postgres, tránh
    DeprecationWarning của datetime.utcnow() trên Python 3.12 trở lên."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive(dt: datetime | None) -> datetime | None:
    """Bỏ tzinfo về naive UTC. Cột DateTime(timezone=True) trả datetime aware
    trên Postgres nhưng naive trên SQLite; coerce trước khi trừ hoặc so sánh với
    now_utc() (naive) để không lỗi 'can't subtract offset-naive and offset-aware'."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
