"""合同审查 API（核心接口）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.review import ReviewCreate
from app.services.contract_service import contract_service
from app.services.review_service import review_service
from app.services.risk_service import risk_service
from app.services.report_service import report_service
from app.tasks import run_review_async

router = APIRouter(prefix="/reviews", tags=["合同审查"])


@router.post("/create")
def create_review(req: ReviewCreate, db: Session = Depends(get_db)):
    """创建审查任务。"""
    # 校验合同存在
    contract = contract_service.get_contract(db, req.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    task = review_service.create_task(
        db, req.contract_id, task_type=req.review_type
    )

    # 异步执行
    run_review_async(task.id)

    return {
        "task_id": task.id,
        "contract_id": req.contract_id,
        "status": "pending",
    }


@router.get("/{task_id}/status")
def get_review_status(task_id: str, db: Session = Depends(get_db)):
    """查询审查状态。"""
    task = review_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "error_message": task.error_message,
    }


@router.get("/{task_id}/risks")
def get_review_risks(task_id: str, db: Session = Depends(get_db)):
    """获取审查风险结果。"""
    risks = risk_service.list_risks(db, task_id=task_id)
    return [r.to_dict() for r in risks]


@router.get("/{task_id}/report")
def get_review_report(task_id: str, db: Session = Depends(get_db)):
    """获取审查报告。"""
    report = report_service.get_report_by_task(db, task_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return report.to_dict()
