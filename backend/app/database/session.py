"""数据库引擎与会话管理。

USE_DOCKER=true  -> PostgreSQL
USE_DOCKER=false -> SQLite（本地降级）
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# SQLite 需要额外参数
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖：获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """初始化数据库表（开发用，生产建议用 alembic 迁移）。"""
    # 延迟导入，确保所有 model 已注册到 Base
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
