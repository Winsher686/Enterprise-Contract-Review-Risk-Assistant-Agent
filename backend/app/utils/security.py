"""安全工具：JWT 生成与校验（简化实现，生产建议用 python-jose）。"""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from app.core.config import settings


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(user_id: str, role: str, expires_hours: int = 24) -> str:
    """生成 JWT Token（简化实现，无第三方依赖）。"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": int(time.time()) + expires_hours * 3600,
    }
    header_b64 = _b64_encode(json.dumps(header).encode())
    payload_b64 = _b64_encode(json.dumps(payload).encode())
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256
    ).digest()
    sig_b64 = _b64_encode(signature)
    return f"{message}.{sig_b64}"


def verify_token(token: str) -> Optional[dict]:
    """校验 JWT Token，返回 payload 或 None。"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64_decode(sig_b64), expected_sig):
            return None
        payload = json.loads(_b64_decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
