"""统一 API 响应封装。"""
from typing import Any, Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一响应结构。"""
    code: int = 0
    message: str = "success"
    data: Any = None


def ok(data: Any = None, message: str = "success") -> ApiResponse:
    return ApiResponse(code=0, message=message, data=data)


def fail(message: str, code: int = -1, data: Any = None) -> ApiResponse:
    return ApiResponse(code=code, message=message, data=data)
