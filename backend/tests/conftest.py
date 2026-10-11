"""pytest 全局 fixture。

提供：
- 隔离的测试数据库（内存 SQLite，每个测试独立，不污染开发数据库）
- FastAPI TestClient
- 示例合同文本
- 已登录的 token

关键点：测试在 Mock LLM 模式下运行（不依赖真实 API Key），
并使用内存 SQLite 数据库，保证测试可重复、无副作用。
"""
import os
import sys

# 确保 backend 目录在 sys.path 中（可 import app.*）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# 强制使用测试数据库（内存 SQLite），避免污染开发库
os.environ["USE_DOCKER"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import Base  # noqa: E402
from app import models  # noqa: E402,F401  确保所有模型已注册


def _make_test_db():
    """创建一个全新的内存 SQLite 数据库及 sessionmaker。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    # 内存 SQLite + StaticPool，保证同一连接复用（后台线程共享）
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    return test_engine, TestSessionLocal


@pytest.fixture()
def db_engine():
    """每个测试独立的数据库（function 级，避免测试间状态污染）。"""
    test_engine, TestSessionLocal = _make_test_db()
    yield test_engine, TestSessionLocal
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def db(db_engine):
    """测试数据库会话。"""
    _, TestSessionLocal = db_engine
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(db_engine, monkeypatch):
    """FastAPI TestClient，依赖被替换为测试数据库会话。

    通过 monkeypatch 覆盖：
    1. get_db 依赖 -> 测试库会话（API 请求路径）
    2. session_module.SessionLocal -> 测试库 sessionmaker
    3. app.tasks.SessionLocal -> 测试库 sessionmaker（后台审查线程路径）

    从而保证审查任务（线程池执行）也写入测试库，而非真实开发库。
    """
    from app.main import app
    from app.database import session as session_module
    import app.tasks as tasks_module

    _, TestSessionLocal = db_engine

    def _override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[session_module.get_db] = _override_get_db
    # 关键：替换 SessionLocal 引用，让后台线程也用测试库
    monkeypatch.setattr(session_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    # 关键：审查任务改为同步执行，消除后台线程与主线程共享
    # StaticPool 单连接的并发竞态（SQLite 多线程不安全）。
    # 同步执行后，测试轮询的状态在同一个线程内即可完成。
    def _sync_run_review(task_id: str) -> None:
        tasks_module._run_review(task_id)

    # 审查 API 通过 app.api.reviews 调用 run_review_async，需同时覆盖该引用
    from app.api import reviews as reviews_module
    monkeypatch.setattr(reviews_module, "run_review_async", _sync_run_review)
    monkeypatch.setattr(tasks_module, "run_review_async", _sync_run_review)

    # 确保默认管理员存在
    from app.services.user_service import user_service
    _db = TestSessionLocal()
    try:
        user_service.ensure_default_admin(_db)
    finally:
        _db.close()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_token(client):
    """返回一个已登录的 token。"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, f"登录失败：{resp.text}"
    return resp.json()["token"]


@pytest.fixture()
def sample_contract_text():
    """示例合同文本（含多个可触发风险的条款）。"""
    return """采购合同

合同编号：CG-2026-001

甲方：示例有限公司
乙方：示例科技有限公司

第一条 合同目的
甲乙双方本着平等互利的原则，就货物采购事宜达成如下协议。

第二条 付款方式
甲方应在收到货物后支付合同款项，未约定验收标准和付款期限。

第三条 违约责任
乙方逾期交付，无需承担任何责任。乙方承担全部损失。

第四条 知识产权
开发成果归甲方所有，技术成果的知识产权归属由双方另行协商。

第五条 保密条款
双方应对合作内容保密。

第六条 合同期限
本合同到期后自动续约一年。
"""


@pytest.fixture()
def sample_clauses():
    """示例条款列表（模拟 parser 输出结构）。"""
    return [
        {"clause_name": "合同目的", "clause_type": "purpose", "content": "甲乙双方本着平等互利的原则，就货物采购事宜达成如下协议。"},
        {"clause_name": "付款方式", "clause_type": "payment", "content": "甲方应在收到货物后支付合同款项。"},
        {"clause_name": "违约责任", "clause_type": "liability", "content": "乙方逾期交付，无需承担任何责任。乙方承担全部损失。"},
        {"clause_name": "保密条款", "clause_type": "confidential", "content": "双方应对合作内容保密。"},
    ]
