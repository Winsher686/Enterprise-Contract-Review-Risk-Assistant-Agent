"""认证相关 Schema。"""
from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    email: Optional[str] = None


class TokenResponse(BaseModel):
    token: str
    user: UserResponse
