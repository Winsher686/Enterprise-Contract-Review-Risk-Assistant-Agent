"""Agent 5：报告生成 Agent（Report Agent）。

职责：整合风险、依据、建议，生成合同审查报告。
"""
from typing import Any, Dict, List

from app.agents.base import BaseAgent
from app.prompts import REPORT_SUMMARY_PROMPT


class ReportAgent(BaseAgent):
    name = "ReportAgent"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成审查报告。

        Args:
            input_data: {
                "contract_info": dict,
                "risks": List[risk dict]
            }
        Returns:
            报告内容 dict
        """
        contract_info = input_data.get("contract_info", {})
        risks = input_data.get("risks", [])

        # 统计风险等级
        high = sum(1 for r in risks if r.get("risk_level") in ("HIGH", "CRITICAL"))
        medium = sum(1 for r in risks if r.get("risk_level") == "MEDIUM")
        low = sum(1 for r in risks if r.get("risk_level") == "LOW")

        # LLM 生成摘要
        risk_list_str = self._format_risk_list(risks)
        contract_info_str = str(contract_info)
        prompt = REPORT_SUMMARY_PROMPT.format(
            contract_info=contract_info_str, risk_list=risk_list_str
        )
        summary_result = self._call_llm_json(prompt)

        overall_level = self._calc_overall_level(risks)
        if summary_result and summary_result.get("overall_level"):
            overall_level = summary_result.get("overall_level")

        # 组装完整报告
        report = {
            "contract_info": contract_info,
            "summary": (summary_result or {}).get("summary", ""),
            "overall_level": overall_level,
            "key_concerns": (summary_result or {}).get("key_concerns", []),
            "risk_statistics": {
                "total": len(risks),
                "high": high,
                "medium": medium,
                "low": low,
            },
            "risks": risks,
            "suggestions": self._collect_suggestions(risks),
        }
        return report

    # ---------- 辅助方法 ----------
    @staticmethod
    def _format_risk_list(risks: List[Dict]) -> str:
        if not risks:
            return "（未发现风险）"
        parts = []
        for i, r in enumerate(risks, 1):
            parts.append(
                f"{i}. [{r.get('risk_level')}] {r.get('risk_type')} - "
                f"{r.get('description', '')}（条款：{r.get('clause_name', '')}）"
            )
        return "\n".join(parts)

    @staticmethod
    def _calc_overall_level(risks: List[Dict]) -> str:
        """计算综合风险等级。"""
        if not risks:
            return "LOW"
        levels = [r.get("risk_level", "LOW") for r in risks]
        if "CRITICAL" in levels:
            return "CRITICAL"
        if "HIGH" in levels:
            return "HIGH"
        if "MEDIUM" in levels:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _collect_suggestions(risks: List[Dict]) -> List[str]:
        """汇总所有修改建议。"""
        suggestions = []
        for r in risks:
            s = r.get("suggestion")
            if s:
                suggestions.append({
                    "clause_name": r.get("clause_name"),
                    "risk_type": r.get("risk_type"),
                    "suggestion": s,
                })
        return suggestions
