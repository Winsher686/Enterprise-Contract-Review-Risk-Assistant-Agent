"""FastAPI 应用入口。"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api import api_router
from app.database.session import init_db
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动初始化 + 优雅关闭。"""
    # ---- 启动初始化 ----
    logger.info(f"应用启动：{settings.APP_NAME}")
    logger.info(f"运行模式：{'Docker 完整架构' if settings.USE_DOCKER else '本地降级模式'}")
    logger.info(f"LLM 模式：{'Mock' if settings.use_mock_llm else '真实 API'}")

    # 初始化数据库
    init_db()

    # 创建默认管理员
    from app.database.session import SessionLocal
    from app.services.user_service import user_service
    db = SessionLocal()
    try:
        user_service.ensure_default_admin(db)
    finally:
        db.close()

    # 加载示例知识库
    try:
        from app.core.knowledge_loader import load_default_knowledge
        load_default_knowledge()
    except Exception as e:
        logger.warning(f"加载示例知识库失败：{e}")

    logger.info("应用初始化完成")

    yield

    # ---- 优雅关闭 ----
    try:
        from app.graph.store import graph_store
        graph_store.close()
        logger.info("知识图谱连接已关闭")
    except Exception as e:  # pragma: no cover
        logger.warning(f"关闭知识图谱连接失败：{e}")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="企业合同智能审查与风险辅助 Agent 系统",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix=settings.API_PREFIX)

# 前端静态文件目录（相对 backend 目录，即项目根目录下的 frontend）
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "frontend")

if os.path.isdir(_FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")

    @app.get("/ui", include_in_schema=False)
    def web_ui() -> FileResponse:
        """前端 Web 界面入口。"""
        return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

    @app.get("/index.html", include_in_schema=False)
    def web_ui_index() -> FileResponse:
        return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "ui": "/ui",
        "api_prefix": settings.API_PREFIX,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
