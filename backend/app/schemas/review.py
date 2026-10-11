"""审查相关 Schema。"""
from typing import Optional, List, Any

from pydantic import BaseModel


class ReviewCreate(BaseModel):
    contract_id: str
    review_type: str = "full"


class ReviewResponse(BaseModel):
    task_id: str
    contract_id: str
    status: str
    progress: int = 0


class ReviewStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    current_step: Optional[str] = None
    error_message: Optional[str] = None


class RiskResponse(BaseModel):
    id: str
    clause_name: Optional[str] = None
    risk_type: str
    risk_category: Optional[str] = None
    risk_level: str
    risk_score: Optional[int] = None
    confidence: Optional[float] = None
    description: Optional[str] = None
    evidence: Optional[List[Any]] = None
    suggestion: Optional[str] = None
    original_text: Optional[str] = None
    review_status: str = "pending"
