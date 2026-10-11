"""Agent 1：合同解析 Agent（Parser Agent）。

职责：理解合同结构，调用 Parser Tool 解析文件，提取合同基本信息。
"""
from typing import Any, Dict

from app.agents.base import BaseAgent
from app.prompts import CONTRACT_PARSE_PROMPT
from app.tools import parse_contract_tool


class ParserAgent(BaseAgent):
    name = "ParserAgent"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析合同。

        Args:
            input_data: {"file_path": str, "file_type": Optional[str]}
        Returns:
            {"text": str, "contract_info": dict}
        """
        file_path = input_data.get("file_path")
        file_type = input_data.get("file_type")

        # 1. 调用 Parser Tool 解析文件
        text = parse_contract_tool(file_path, file_type)

        # 2. 调用 LLM 提取结构化信息
        prompt = CONTRACT_PARSE_PROMPT.format(contract_text=text[:6000])
        contract_info = self._call_llm_json(prompt)

        return {
            "text": text,
            "contract_info": contract_info or {},
        }
