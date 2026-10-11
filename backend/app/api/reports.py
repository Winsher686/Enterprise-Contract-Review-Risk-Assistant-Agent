"""报告管理 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.report_service import report_service
from app.services.risk_service import risk_service

router = APIRouter(prefix="/reports", tags=["报告管理"])


@router.get("/{contract_id}")
def get_report(contract_id: str, db: Session = Depends(get_db)):
    """获取合同的最新审查报告。"""
    report = report_service.get_report_by_contract(db, contract_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return report.to_dict()


@router.post("/{contract_id}/review")
def review_report(contract_id: str, db: Session = Depends(get_db)):
    """人工审核：将报告状态改为 approved。"""
    report = report_service.get_report_by_contract(db, contract_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    report_service.update_status(db, report.id, "approved")
    return {"status": "approved"}
