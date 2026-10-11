"""Agent 4：风险分析 Agent（Risk Agent）。

核心 Agent。采用「规则引擎 + RAG 知识增强 + LLM 语义推理」三层检测模型，
判断条款风险并给出等级、依据、修改建议。
"""
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.prompts import RISK_ANALYSIS_PROMPT
from app.tools import detect_risk_tool, rule_engine
from app.agents.legal_agent import LegalAgent
from app.graph.store import graph_store
from app.utils.logger import logger


class RiskAgent(BaseAgent):
    name = "RiskAgent"

    def __init__(self) -> None:
        super().__init__()
        self.legal_agent = LegalAgent()

    def run(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析合同条款风险。

        Args:
            input_data: {
                "clauses": List[{"clause_name","clause_type","content"}],
                "amount": Optional[float],
                "contract_type": Optional[str]
            }
        Returns:
            List[risk dict]
        """
        clauses = input_data.get("clauses", [])
        amount = input_data.get("amount")
        contract_type = input_data.get("contract_type")

        risks = []

        # ---- 合同级规则：大额合同等，整个合同只触发一次 ----
        contract_level_hits = rule_engine.detect_contract_level(amount)
        for hit in contract_level_hits:
            risks.append({
                "clause_name": "合同整体",
                "risk_type": hit.get("risk_type"),
                "risk_category": hit.get("category"),
                "risk_level": hit.get("level"),
                "risk_score": self._level_to_score(hit.get("level")),
                "description": hit.get("description"),
                "suggestion": hit.get("suggestion"),
                "evidence": [],
                "original_text": "",
                "source": "rule_engine",
            })

        # ---- 条款级分析 ----
        for clause in clauses:
            content = clause.get("content", "") or ""
            clause_name = clause.get("clause_name", "") or "条款"

            # 跳过空条款
            if not content.strip():
                continue

            # ---- 第一层：规则引擎检测（条款级关键词规则） ----
            rule_hits = detect_risk_tool(content, amount)

            # ---- 第二层：RAG 法律知识增强 ----
            legal_results = self.legal_agent.run({"clause": content})
            legal_context = self._format_legal_context(legal_results)

            # ---- 第三层：LLM 语义推理 ----
            prompt = RISK_ANALYSIS_PROMPT.format(
                clause=content, legal_context=legal_context
            )
            llm_result = self._call_llm_json(prompt)

            # ---- 融合结果 ----
            if rule_hits:
                # 规则命中优先，作为确定风险
                for hit in rule_hits:
                    risks.append({
                        "clause_name": clause_name,
                        "risk_type": hit.get("risk_type"),
                        "risk_category": hit.get("category"),
                        "risk_level": hit.get("level"),
                        "risk_score": self._level_to_score(hit.get("level")),
                        "description": hit.get("description"),
                        "suggestion": hit.get("suggestion"),
                        "evidence": self._extract_evidence(legal_results),
                        "original_text": content,
                        "source": "rule_engine",
                    })
            elif llm_result and llm_result.get("has_risk"):
                # LLM 判断有风险
                risks.append({
                    "clause_name": clause_name,
                    "risk_type": llm_result.get("risk_type"),
                    "risk_category": llm_result.get("risk_category"),
                    "risk_level": llm_result.get("risk_level", "LOW"),
                    "risk_score": self._level_to_score(llm_result.get("risk_level")),
                    "description": llm_result.get("description"),
                    "suggestion": llm_result.get("suggestion"),
                    "evidence": self._extract_evidence(legal_results),
                    "original_text": content,
                    "source": "llm",
                })

        # ---- 知识图谱写入：记录「条款-产生-风险-依据-法规」关系 ----
        self._persist_risk_relations(risks, contract_type)

        return risks

    def _persist_risk_relations(
        self, risks: List[Dict[str, Any]], contract_type: Optional[str]
    ) -> None:
        """将识别出的风险关系写入知识图谱（Neo4j 或内存降级）。"""
        try:
            for risk in risks:
                clause_name = risk.get("clause_name", "") or "未命名条款"
                risk_type = risk.get("risk_type", "") or "未知风险"
                # 取证据中的第一条法律来源作为 SUPPORTED_BY 关系
                law = None
                evidence = risk.get("evidence") or []
                if evidence:
                    law = evidence[0].get("source")
                graph_store.add_risk_relation(
                    clause=clause_name,
                    risk_type=risk_type,
                    law=law,
                    contract_type=contract_type,
                )
            logger.info(f"已写入 {len(risks)} 条风险关系到知识图谱")
        except Exception as e:  # pragma: no cover - 图谱写入失败不应中断审查
            logger.warning(f"知识图谱写入失败（不影响审查结果）：{e}")

    # ---------- 辅助方法 ----------
    @staticmethod
    def _format_legal_context(legal_results: List[Dict]) -> str:
        """格式化法律检索结果为上下文文本。"""
        if not legal_results:
            return "（未检索到相关依据）"
        parts = []
        for i, r in enumerate(legal_results, 1):
            source = r.get("metadata", {}).get("source", "未知来源")
            parts.append(f"[{i}] {r.get('text', '')}（来源：{source}）")
        return "\n".join(parts)

    @staticmethod
    def _extract_evidence(legal_results: List[Dict]) -> List[Dict]:
        """提取法律依据作为证据。"""
        evidence = []
        for r in legal_results:
            evidence.append({
                "source": r.get("metadata", {}).get("source", "未知来源"),
                "text": r.get("text", ""),
                "score": r.get("score", 0),
            })
        return evidence

    @staticmethod
    def _level_to_score(level: Optional[str]) -> int:
        """风险等级转评分（用于风险评分模型）。"""
        mapping = {"LOW": 15, "MEDIUM": 35, "HIGH": 75, "CRITICAL": 100}
        return mapping.get(level, 15)
