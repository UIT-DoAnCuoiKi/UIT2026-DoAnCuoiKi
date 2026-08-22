from collections.abc import Callable

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.security.tokens import decode_token

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token không hợp lệ")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "tài khoản không hợp lệ")
    return user


def require_role(*roles: str) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "không đủ quyền")
        return user
    return checker


def require_edge_key(x_edge_key: str = Header(..., alias="X-Edge-Key")) -> None:
    if x_edge_key != settings.edge_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "edge key không hợp lệ")
