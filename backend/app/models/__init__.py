"""数据模型汇总导出。

集中导入所有 ORM 模型，确保 Base.metadata 完整注册。
"""
from app.models.user import User
from app.models.contract import Contract, ContractFile, ContractClause
from app.models.review import ReviewTask, AgentExecutionLog
from app.models.risk import RiskRecord
from app.models.report import Report
from app.models.knowledge import LegalDocument, KnowledgeChunk

__all__ = [
    "User",
    "Contract",
    "ContractFile",
    "ContractClause",
    "ReviewTask",
    "AgentExecutionLog",
    "RiskRecord",
    "Report",
    "LegalDocument",
    "KnowledgeChunk",
]
