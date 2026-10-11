"""异步任务模块。

合同审查是耗时任务，采用异步执行。
本地降级模式下用线程池模拟 Celery；Docker 模式下可切换 Celery。
"""
from app.services.contract_service import contract_service
from app.services.review_service import review_service
from app.services.risk_service import risk_service
from app.services.report_service import report_service
from app.agents.orchestrator import contract_review_agent
from app.models.review import AgentExecutionLog
from app.database.session import SessionLocal
from app.utils.logger import logger


def _run_review(task_id: str) -> None:
    """执行合同审查任务（核心逻辑）。"""
    db = SessionLocal()
    try:
        # 获取任务
        task = review_service.get_task(db, task_id)
        if not task:
            logger.error(f"任务不存在：{task_id}")
            return

        contract_id = task.contract_id
        contract = contract_service.get_contract(db, contract_id)
        if not contract:
            review_service.update_status(
                db, task_id, "failed", error_message="合同不存在"
            )
            return

        contract_file = contract_service.get_file(db, contract_id)
        if not contract_file:
            review_service.update_status(
                db, task_id, "failed", error_message="合同文件不存在"
            )
            return

        # 更新状态为运行中
        review_service.update_status(db, task_id, "running", progress=5,
                                     current_step="ParserAgent")

        # 设置进度回调
        def progress_callback(step: str, progress: int) -> None:
            status = "completed" if step == "completed" else "running"
            review_service.update_status(
                db, task_id, status, progress=progress, current_step=step
            )

        contract_review_agent.set_progress_callback(progress_callback)

        # 执行审查
        report = contract_review_agent.run({
            "file_path": contract_file.file_path,
            "file_type": contract_file.file_type,
            "contract_id": contract_id,
            "amount": contract.amount,
        })

        # 保存条款
        clauses = report.get("_meta", {}).get("clauses", [])
        contract_service.save_clauses(db, contract_id, clauses)

        # 保存风险记录
        risks = report.get("risks", [])
        risk_service.save_risks(db, contract_id, task_id, risks)

        # 保存 Agent 执行日志
        execution_logs = report.get("_meta", {}).get("execution_logs", [])
        for log in execution_logs:
            db.add(AgentExecutionLog(
                task_id=task_id,
                agent_name=log.get("agent_name"),
                action=log.get("action"),
                input_data=log.get("input"),
                output_data=log.get("output"),
                status="success",
            ))
        db.commit()

        # 保存报告
        report_service.save_report(db, task_id, contract_id, report)

        # 更新合同状态
        contract_service.update_status(db, contract_id, "completed")

        # 更新任务状态
        review_service.update_status(db, task_id, "completed", progress=100,
                                     current_step="completed")
        logger.info(f"审查任务完成：{task_id}，发现 {len(risks)} 个风险")

    except Exception as e:
        logger.exception(f"审查任务失败：{task_id}")
        review_service.update_status(
            db, task_id, "failed", error_message=str(e)
        )
        if task_id:
            pass
    finally:
        db.close()


def run_review_async(task_id: str) -> None:
    """异步执行审查任务（降级模式：线程池；Docker：Celery）。"""
    from app.core.config import settings

    if settings.USE_DOCKER:
        # Docker 模式：使用 Celery
        try:
            from app.tasks.celery_app import review_contract_task
            review_contract_task.delay(task_id)
            return
        except ImportError:
            logger.warning("Celery 未安装，降级为线程池执行")

    # 线程池执行
    import threading

    t = threading.Thread(target=_run_review, args=(task_id,), daemon=True)
    t.start()
    logger.info(f"已提交异步审查任务：{task_id}（线程池模式）")
