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
_bearer_optional = HTTPBearer(auto_error=False)


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token không hợp lệ")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "tài khoản không hợp lệ")
    return user


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    return _user_from_token(creds.credentials, db)


def require_role(*roles: str) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "không đủ quyền")
        return user
    return checker


# Mọi thao tác chỉ dành cho quản lý trở lên đều dùng đúng cặp role này (config,
# giá, tài khoản, thiết bị, doanh thu, đồng bộ trung tâm...). Trước đây mỗi
# router tự khai `admin_only = require_role("manager", "root")` riêng, lặp lại
# nguyên văn ở 7 nơi; đổi role admin sau này (vd thêm "supervisor") phải sửa cả
# 7 chỗ và rất dễ bỏ sót một chỗ.
admin_only = require_role("manager", "root")


def require_edge_key(x_edge_key: str = Header(..., alias="X-Edge-Key")) -> None:
    if x_edge_key != settings.edge_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "edge key không hợp lệ")


def user_or_edge_key(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer_optional),
    x_edge_key: str | None = Header(None, alias="X-Edge-Key"),
    db: Session = Depends(get_db),
) -> User | None:
    """Chấp nhận JWT nhân viên HOẶC X-Edge-Key, trả None nếu là thiết bị biên.

    Dùng cho heartbeat: thiết bị biên chỉ có edge key (không có tài khoản nhân
    viên), mà nếu nó không báo được heartbeat thì màn hình health luôn hiện
    offline dù thiết bị đang chạy tốt.
    """
    if x_edge_key is not None:
        if x_edge_key != settings.edge_api_key:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "edge key không hợp lệ")
        return None
    if creds is not None:
        return _user_from_token(creds.credentials, db)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "cần token nhân viên hoặc X-Edge-Key")
