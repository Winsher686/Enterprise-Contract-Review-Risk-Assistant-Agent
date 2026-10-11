"""认证 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.user_service import user_service
from app.utils.security import create_token
from app.utils.response import ok

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = user_service.authenticate(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user.id, user.role)
    return TokenResponse(
        token=token,
        user=UserResponse(id=user.id, username=user.username, role=user.role, email=user.email),
    )
