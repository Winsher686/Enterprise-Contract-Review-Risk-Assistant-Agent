"""合同相关 Schema。"""
from typing import Optional, List

from pydantic import BaseModel


class ContractCreate(BaseModel):
    name: str
    contract_type: Optional[str] = None
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    amount: Optional[float] = None


class ContractResponse(BaseModel):
    id: str
    name: str
    contract_type: Optional[str] = None
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    amount: Optional[float] = None
    status: str
    created_at: Optional[str] = None


class ClauseResponse(BaseModel):
    id: str
    clause_name: Optional[str] = None
    clause_type: Optional[str] = None
    content: Optional[str] = None
    order_num: Optional[int] = None
