"""通用工具函数：文件保存、UUID 生成等。"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings


def gen_uuid() -> str:
    """生成 UUID 字符串。"""
    return str(uuid.uuid4())


def now_iso() -> str:
    """当前时间 ISO 字符串（UTC，无时区后缀，兼容现有存储）。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")


def get_storage_dir(sub: str = "") -> Path:
    """获取文件存储目录（合同 / 报告等）。"""
    base = Path(settings.STORAGE_DIR).resolve()
    target = base / sub if sub else base
    target.mkdir(parents=True, exist_ok=True)
    return target


def save_upload_file(file_bytes: bytes, filename: str, sub: str = "contracts") -> str:
    """保存上传文件，返回相对路径。

    使用 uuid 前缀避免文件名冲突。
    """
    safe_name = os.path.basename(filename)
    stored = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    target_dir = get_storage_dir(sub)
    filepath = target_dir / stored
    filepath.write_bytes(file_bytes)
    return str(filepath)
