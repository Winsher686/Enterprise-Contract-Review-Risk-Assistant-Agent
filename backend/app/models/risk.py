"""风险记录模型。"""
from sqlalchemy import Column, String, Integer, Text, Float, JSON

from app.database.session import Base
from app.utils.file import gen_uuid, now_iso


class RiskRecord(Base):
    """风险记录表（AI 发现的合同问题）。"""
    __tablename__ = "risk_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    contract_id = Column(String(36), nullable=False, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    clause_id = Column(String(36), nullable=True)
    clause_name = Column(String(128), nullable=True)  # 对应条款名
    risk_type = Column(String(64), nullable=False)  # 违约责任风险/付款风险...
    risk_category = Column(String(64), nullable=True)  # liability/payment/ip...
    # LOW / MEDIUM / HIGH / CRITICAL
    risk_level = Column(String(16), nullable=False)
    risk_score = Column(Integer, nullable=True)  # 0-125
    confidence = Column(Float, nullable=True)  # 0-1
    description = Column(Text, nullable=True)  # 风险原因
    evidence = Column(JSON, nullable=True)  # 法律依据列表
    suggestion = Column(Text, nullable=True)  # 修改建议
    original_text = Column(Text, nullable=True)  # 原条款
    # pending -> confirmed -> rejected（人工审核状态）
    review_status = Column(String(32), default="pending")
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "task_id": self.task_id,
            "clause_id": self.clause_id,
            "clause_name": self.clause_name,
            "risk_type": self.risk_type,
            "risk_category": self.risk_category,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "description": self.description,
            "evidence": self.evidence,
            "suggestion": self.suggestion,
            "original_text": self.original_text,
            "review_status": self.review_status,
        }
