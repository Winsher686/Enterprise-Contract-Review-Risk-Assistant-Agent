"""Celery 应用配置（Docker 完整架构模式使用）。

本地降级模式不使用 Celery，改用线程池（见 app/tasks/__init__.py）。
"""
from app.core.config import settings


def _make_celery():
    try:
        from celery import Celery

        app = Celery(
            "contract_review",
            broker=settings.redis_url,
            backend=settings.redis_url,
        )
        app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="Asia/Shanghai",
            enable_utc=True,
        )
        return app
    except ImportError:
        return None


celery_app = _make_celery()


if celery_app is not None:
    @celery_app.task(name="review_contract_task")
    def review_contract_task(task_id: str):
        """Celery 任务：执行合同审查。"""
        from app.tasks import _run_review
        _run_review(task_id)
