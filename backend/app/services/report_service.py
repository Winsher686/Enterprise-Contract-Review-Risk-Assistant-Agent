"""报告生成服务。"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.report import Report
from app.utils.logger import logger


class ReportService:
    """报告管理服务。"""

    def save_report(
        self, db: Session, task_id: str, contract_id: str, report_content: dict
    ) -> Report:
        """保存审查报告。"""
        stats = report_content.get("risk_statistics", {})
        report = Report(
            task_id=task_id,
            contract_id=contract_id,
            summary=report_content.get("summary", ""),
            risk_count=stats.get("total", 0),
            high_risk_count=stats.get("high", 0),
            medium_risk_count=stats.get("medium", 0),
            low_risk_count=stats.get("low", 0),
            overall_level=report_content.get("overall_level", "LOW"),
            content=report_content,
            status="draft",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def get_report_by_task(
        self, db: Session, task_id: str
    ) -> Optional[Report]:
        return db.query(Report).filter(Report.task_id == task_id).first()

    def get_report_by_contract(
        self, db: Session, contract_id: str
    ) -> Optional[Report]:
        return (
            db.query(Report)
            .filter(Report.contract_id == contract_id)
            .order_by(Report.created_at.desc())
            .first()
        )

    def update_status(self, db: Session, report_id: str, status: str) -> None:
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = status
            db.commit()


report_service = ReportService()
