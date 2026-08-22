from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.security.passwords import verify_password
from app.security.tokens import create_access_token
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalars(select(User).where(User.username == body.username)).first()
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sai tài khoản hoặc mật khẩu")
    token = create_access_token(str(user.id), user.username, user.role)
    write_audit(db, user_id=user.id, action="login")
    db.commit()
    return TokenResponse(access_token=token, role=user.role)
