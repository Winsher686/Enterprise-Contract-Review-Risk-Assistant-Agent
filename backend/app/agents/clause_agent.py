"""Agent 2：条款分析 Agent（Clause Agent）。

职责：分析合同条款，调用 Clause Extraction Tool 识别关键条款。
"""
from typing import Any, Dict, List

from app.agents.base import BaseAgent
from app.prompts import CLAUSE_EXTRACT_PROMPT
from app.tools import extract_clause_tool


class ClauseAgent(BaseAgent):
    name = "ClauseAgent"

    def run(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """抽取合同条款。

        Args:
            input_data: {"text": str}
        Returns:
            List[{"clause_name", "clause_type", "content"}]
        """
        text = input_data.get("text", "")

        # 1. 先用规则切分（确定性）
        raw_clauses = extract_clause_tool(text)

        # 2. 调用 LLM 对条款进行语义分类
        prompt = CLAUSE_EXTRACT_PROMPT.format(contract_text=text[:6000])
        llm_clauses = self._call_llm_json(prompt)

        # 3. 合并：优先用 LLM 结果，若失败则用规则切分结果
        if isinstance(llm_clauses, list) and llm_clauses:
            return llm_clauses

        # 降级：用规则切分结果
        result = []
        for i, c in enumerate(raw_clauses):
            result.append({
                "clause_name": c.get("title", "条款"),
                "clause_type": "other",
                "content": c.get("content", ""),
                "order_num": i,
            })
        return result
