"""风险记录服务。"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.risk import RiskRecord


class RiskService:
    """风险记录管理服务。"""

    def save_risks(
        self, db: Session, contract_id: str, task_id: str, risks: List[dict]
    ) -> List[RiskRecord]:
        """保存风险列表。"""
        saved = []
        for r in risks:
            record = RiskRecord(
                contract_id=contract_id,
                task_id=task_id,
                clause_name=r.get("clause_name"),
                risk_type=r.get("risk_type"),
                risk_category=r.get("risk_category"),
                risk_level=r.get("risk_level"),
                risk_score=r.get("risk_score"),
                confidence=r.get("confidence"),
                description=r.get("description"),
                evidence=r.get("evidence"),
                suggestion=r.get("suggestion"),
                original_text=r.get("original_text"),
                review_status="pending",
            )
            db.add(record)
            saved.append(record)
        db.commit()
        return saved

    def list_risks(
        self, db: Session, task_id: Optional[str] = None,
        contract_id: Optional[str] = None,
    ) -> List[RiskRecord]:
        query = db.query(RiskRecord)
        if task_id:
            query = query.filter(RiskRecord.task_id == task_id)
        if contract_id:
            query = query.filter(RiskRecord.contract_id == contract_id)
        return query.order_by(RiskRecord.risk_score.desc()).all()

    def update_review_status(
        self, db: Session, risk_id: str, review_status: str
    ) -> Optional[RiskRecord]:
        """人工审核：更新风险确认状态。"""
        record = db.query(RiskRecord).filter(RiskRecord.id == risk_id).first()
        if record:
            record.review_status = review_status
            db.commit()
        return record


risk_service = RiskService()
