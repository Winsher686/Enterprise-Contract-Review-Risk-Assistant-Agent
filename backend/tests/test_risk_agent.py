"""RiskAgent 单元测试。

验证三层检测模型（规则引擎 + RAG + LLM）的核心融合逻辑：
1. 合同级金额规则只触发一次
2. 条款级规则命中生成风险
3. LLM 语义风险识别
4. 风险评分映射
"""
from app.agents.risk_agent import RiskAgent


class TestRiskAgent:
    def test_contract_level_amount_risk_once(self):
        """大额合同风险整个合同只触发一次。"""
        agent = RiskAgent()
        clauses = [
            {"clause_name": "付款方式", "clause_type": "payment", "content": "甲方应付款"},
            {"clause_name": "违约责任", "clause_type": "liability", "content": "乙方违约"},
        ]
        risks = agent.run({"clauses": clauses, "amount": 8000000})
        # 金额规则只在"合同整体"出现一次
        amount_risks = [r for r in risks if r["clause_name"] == "合同整体"]
        assert len(amount_risks) == 1
        assert amount_risks[0]["risk_type"] == "付款风险"

    def test_no_amount_no_contract_level_risk(self):
        """无金额时不产生合同级风险。"""
        agent = RiskAgent()
        clauses = [{"clause_name": "x", "clause_type": "other", "content": "普通内容"}]
        risks = agent.run({"clauses": clauses})
        assert all(r["clause_name"] != "合同整体" for r in risks)

    def test_rule_hit_generates_risk(self):
        """规则命中（免责条款）应生成 HIGH 风险。"""
        agent = RiskAgent()
        clauses = [
            {"clause_name": "违约责任", "clause_type": "liability",
             "content": "乙方无需承担任何责任。"}
        ]
        risks = agent.run({"clauses": clauses})
        liability = [r for r in risks if r["risk_type"] == "违约责任风险"]
        assert len(liability) >= 1
        assert liability[0]["risk_level"] == "HIGH"

    def test_empty_clause_skipped(self):
        """空条款应被跳过。"""
        agent = RiskAgent()
        clauses = [{"clause_name": "空", "clause_type": "other", "content": ""}]
        risks = agent.run({"clauses": clauses})
        assert risks == []

    def test_risk_structure_complete(self):
        """风险结果应包含完整字段。"""
        agent = RiskAgent()
        clauses = [
            {"clause_name": "违约责任", "clause_type": "liability",
             "content": "乙方承担全部损失。"}
        ]
        risks = agent.run({"clauses": clauses})
        assert risks, "应至少有一个风险"
        r = risks[0]
        for key in ["clause_name", "risk_type", "risk_category", "risk_level",
                    "risk_score", "description", "suggestion", "source"]:
            assert key in r, f"缺少字段 {key}"

    def test_level_to_score(self):
        """风险等级到评分映射。"""
        assert RiskAgent._level_to_score("LOW") == 15
        assert RiskAgent._level_to_score("MEDIUM") == 35
        assert RiskAgent._level_to_score("HIGH") == 75
        assert RiskAgent._level_to_score("CRITICAL") == 100
        assert RiskAgent._level_to_score(None) == 15  # 默认 LOW
        assert RiskAgent._level_to_score("UNKNOWN") == 15

    def test_risk_persisted_to_graph(self):
        """识别出的风险应写入知识图谱（内存降级模式）。"""
        from app.graph.store import graph_store
        before = len(graph_store._memory_nodes["Risk"])
        agent = RiskAgent()
        clauses = [
            {"clause_name": "违约责任", "clause_type": "liability",
             "content": "乙方承担全部损失。"}
        ]
        agent.run({"clauses": clauses, "contract_type": "采购合同"})
        after = len(graph_store._memory_nodes["Risk"])
        assert after > before, "风险应写入知识图谱"
