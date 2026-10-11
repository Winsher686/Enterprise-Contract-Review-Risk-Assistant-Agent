"""Agent 3：法律检索 Agent（Legal Agent）。

职责：调用 RAG Tool，查询法律法规、企业制度、历史案例，为风险判断提供依据。
"""
from typing import Any, Dict, List

from app.agents.base import BaseAgent
from app.prompts import LEGAL_QUERY_PROMPT
from app.tools import search_legal_tool


class LegalAgent(BaseAgent):
    name = "LegalAgent"

    def run(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检索法律依据。

        Args:
            input_data: {"clause": str}
        Returns:
            List[{"text", "score", "metadata"}]
        """
        clause = input_data.get("clause", "")

        # 1. 生成检索关键词（LLM）
        prompt = LEGAL_QUERY_PROMPT.format(clause=clause)
        query_info = self._call_llm_json(prompt)

        # 2. 构造检索查询
        keywords = query_info.get("keywords", []) if query_info else []
        query = " ".join(keywords) if keywords else clause

        # 3. 调用 RAG Tool 检索
        results = search_legal_tool(query, top_k=3)

        return results
