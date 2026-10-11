"""报告相关 Schema。"""
from typing import Optional, Any

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: str
    task_id: str
    contract_id: str
    summary: Optional[str] = None
    risk_count: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    overall_level: Optional[str] = None
    content: Optional[Any] = None
    report_url: Optional[str] = None
    status: str = "draft"
