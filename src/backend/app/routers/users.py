from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_role
from app.models import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.security.passwords import hash_password
from app.services.audit import write_audit

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_role("admin")
_ROLES = ("staff", "admin")


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> User:
    if body.role not in _ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "role không hợp lệ")
    if db.scalars(select(User).where(User.username == body.username)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "username đã tồn tại")
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role, active=True)
    db.add(user)
    db.flush()
    write_audit(db, user_id=admin.id, action="create_user", entity_type="user", entity_id=str(user.id))
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "không tìm thấy user")
    changed: list[str] = []
    if body.active is not None:
        user.active = body.active
        changed.append("active")
    if body.role is not None:
        if body.role not in _ROLES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "role không hợp lệ")
        user.role = body.role
        changed.append("role")
    if body.password is not None:
        user.password_hash = hash_password(body.password)
        changed.append("password")
    write_audit(db, user_id=admin.id, action="update_user", entity_type="user", entity_id=str(user.id), detail=",".join(changed))
    db.commit()
    db.refresh(user)
    return user
