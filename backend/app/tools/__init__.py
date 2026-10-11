"""Tool 工具层。

Agent 不能直接访问数据库/向量库，必须通过 Tool 调用。
本模块定义 Agent 可用的工具函数。
"""
from typing import List, Dict, Any, Optional

from app.rag.parser import parse_document
from app.rag.chunker import split_clauses
from app.rag.service import rag_service
from app.tools.rule_engine import rule_engine
from app.utils.logger import logger


# ============ Tool 1: 合同解析工具 ============
def parse_contract_tool(file_path: str, file_type: Optional[str] = None) -> str:
    """解析合同文件，返回纯文本。"""
    logger.info(f"parse_contract_tool 调用：{file_path}")
    return parse_document(file_path, file_type)


# ============ Tool 2: 条款抽取工具 ============
def extract_clause_tool(contract_text: str) -> List[Dict[str, Any]]:
    """抽取合同条款，返回条款列表。"""
    clauses = split_clauses(contract_text)
    return clauses


# ============ Tool 3: 法律检索工具 ============
def search_legal_tool(
    query: str, top_k: int = 5, metadata_filter: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """检索法律依据/企业制度/历史案例。"""
    logger.info(f"search_legal_tool 调用：{query}")
    return rag_service.search_legal_basis(query, top_k, metadata_filter)


# ============ Tool 4: 风险检测工具（规则引擎） ============
def detect_risk_tool(
    clause_text: str, amount: Optional[float] = None
) -> List[Dict[str, Any]]:
    """基于规则引擎检测风险。"""
    return rule_engine.detect(clause_text, amount)


# 工具注册表（供 Agent 描述/展示使用）
AVAILABLE_TOOLS = {
    "parse_contract": "解析合同文件为文本",
    "extract_clause": "抽取合同条款",
    "search_legal": "检索法律依据与企业制度",
    "detect_risk": "规则引擎风险检测",
}
