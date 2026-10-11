"""Agent 基类。

所有 Agent 继承此基类，统一接口：run(input) -> output。
"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.core.llm import llm_client
from app.utils.logger import logger


class BaseAgent(ABC):
    """Agent 基类。"""

    name: str = "BaseAgent"

    def __init__(self) -> None:
        self.logger = logger

    @abstractmethod
    def run(self, input_data: Any) -> Any:
        """执行 Agent 任务。"""
        raise NotImplementedError

    def log_execution(self, action: str, input_data: Any, output_data: Any) -> Dict:
        """记录执行日志（供持久化到 agent_execution_logs）。"""
        return {
            "agent_name": self.name,
            "action": action,
            "input": input_data,
            "output": output_data,
        }

    def _call_llm(self, prompt: str, system: Optional[str] = None) -> str:
        """调用 LLM。"""
        return llm_client.chat(prompt, system)

    def _call_llm_json(self, prompt: str, system: Optional[str] = None) -> Any:
        """调用 LLM 并解析 JSON。"""
        return llm_client.chat_json(prompt, system)
