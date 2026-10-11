"""审查报告模型。"""
from sqlalchemy import Column, String, Integer, Text, JSON

from app.database.session import Base
from app.utils.file import gen_uuid, now_iso


class Report(Base):
    """审查报告表。"""
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    task_id = Column(String(36), nullable=False, index=True)
    contract_id = Column(String(36), nullable=False, index=True)
    summary = Column(Text, nullable=True)  # 总体摘要
    risk_count = Column(Integer, default=0)
    high_risk_count = Column(Integer, default=0)
    medium_risk_count = Column(Integer, default=0)
    low_risk_count = Column(Integer, default=0)
    overall_level = Column(String(16), nullable=True)  # 综合风险等级
    content = Column(JSON, nullable=True)  # 完整报告内容
    report_url = Column(String(512), nullable=True)  # 报告文件路径
    # draft -> reviewing -> approved -> archived
    status = Column(String(32), default="draft")
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "contract_id": self.contract_id,
            "summary": self.summary,
            "risk_count": self.risk_count,
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "low_risk_count": self.low_risk_count,
            "overall_level": self.overall_level,
            # 统一风险统计结构（供 demo.py / 前端使用）
            "risk_statistics": {
                "total": self.risk_count,
                "high": self.high_risk_count,
                "medium": self.medium_risk_count,
                "low": self.low_risk_count,
            },
            "content": self.content,
            "report_url": self.report_url,
            "status": self.status,
        }
