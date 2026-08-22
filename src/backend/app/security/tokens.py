from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_ALGO = "HS256"


def create_access_token(sub: str, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])
