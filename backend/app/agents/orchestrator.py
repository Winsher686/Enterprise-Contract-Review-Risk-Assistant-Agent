"""Agent Orchestrator（智能编排核心）。

负责：任务拆解、Agent 调度、状态管理、结果汇总。
采用固定 Workflow + LLM 决策的混合模式，保证企业场景的稳定性。
"""
import time
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.agents.parser_agent import ParserAgent
from app.agents.clause_agent import ClauseAgent
from app.agents.risk_agent import RiskAgent
from app.agents.legal_agent import LegalAgent
from app.agents.report_agent import ReportAgent
from app.utils.logger import logger


class ContractReviewAgent(BaseAgent):
    """合同审查编排 Agent（Orchestrator）。"""

    name = "ContractReviewAgent"

    def __init__(self) -> None:
        super().__init__()
        self.parser_agent = ParserAgent()
        self.clause_agent = ClauseAgent()
        self.risk_agent = RiskAgent()
        self.legal_agent = LegalAgent()
        self.report_agent = ReportAgent()

        # 执行日志（供持久化到 agent_execution_logs）
        self.execution_logs: List[Dict] = []

        # 进度回调
        self._progress_callback: Optional[callable] = None

    def set_progress_callback(self, callback: callable) -> None:
        """设置进度回调，用于更新任务状态。"""
        self._progress_callback = callback

    def _update_progress(self, step: str, progress: int) -> None:
        """更新进度。"""
        if self._progress_callback:
            try:
                self._progress_callback(step, progress)
            except Exception as e:  # pragma: no cover
                logger.warning(f"进度回调失败：{e}")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整审查流程。

        Args:
            input_data: {"file_path": str, "file_type": Optional[str],
                         "contract_id": Optional[str], "amount": Optional[float]}
        Returns:
            完整报告 dict
        """
        file_path = input_data.get("file_path")
        file_type = input_data.get("file_type")
        amount = input_data.get("amount")
        self.execution_logs = []

        # ---- Step 1: 解析合同 ----
        self._update_progress("ParserAgent", 10)
        t0 = time.time()
        parse_result = self.parser_agent.run({
            "file_path": file_path, "file_type": file_type
        })
        self._log("ParserAgent", "parse_contract",
                  {"file_path": file_path}, parse_result.get("contract_info"))
        contract_text = parse_result.get("text", "")
        contract_info = parse_result.get("contract_info", {})
        if amount is None:
            amount = contract_info.get("amount")

        # ---- Step 2: 识别条款 ----
        self._update_progress("ClauseAgent", 30)
        clauses = self.clause_agent.run({"text": contract_text})
        self._log("ClauseAgent", "extract_clause",
                  {"text_len": len(contract_text)}, {"clause_count": len(clauses)})

        # ---- Step 3: 风险分析 ----
        self._update_progress("RiskAgent", 50)
        risks = self.risk_agent.run({
            "clauses": clauses,
            "amount": amount,
            "contract_type": contract_info.get("contract_type"),
        })
        self._log("RiskAgent", "analyze_risk",
                  {"clause_count": len(clauses)}, {"risk_count": len(risks)})

        # ---- Step 4: 生成报告 ----
        self._update_progress("ReportAgent", 85)
        report = self.report_agent.run({
            "contract_info": contract_info, "risks": risks
        })
        self._log("ReportAgent", "generate_report",
                  {"risk_count": len(risks)}, {"overall_level": report.get("overall_level")})

        self._update_progress("completed", 100)

        # 附加中间产物
        report["_meta"] = {
            "clauses": clauses,
            "execution_logs": self.execution_logs,
            "duration": round(time.time() - t0, 2),
        }
        return report

    def _log(self, agent_name: str, action: str, input_data: Any, output_data: Any) -> None:
        """记录执行日志。"""
        self.execution_logs.append({
            "agent_name": agent_name,
            "action": action,
            "input": input_data,
            "output": output_data,
        })


# 全局单例
contract_review_agent = ContractReviewAgent()
