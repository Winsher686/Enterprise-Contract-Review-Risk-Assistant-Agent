"""规则引擎单元测试。

重点验证：
1. 条款级关键词规则命中
2. 合同级金额规则不重复触发（去重逻辑）
3. 空条款/无金额等情况
"""
from app.tools.rule_engine import RuleEngine, rule_engine, DEFAULT_RULES


class TestRuleEngine:
    """规则引擎基础行为。"""

    def test_detect_infinite_liability(self):
        """无限责任关键词应命中。"""
        hits = rule_engine.detect("乙方承担全部损失")
        types = [h["risk_type"] for h in hits]
        assert "违约责任风险" in types
        hit = next(h for h in hits if h["rule_name"] == "无限责任检测")
        assert hit["level"] == "HIGH"

    def test_detect_exemption(self):
        """单方免责关键词应命中。"""
        hits = rule_engine.detect("甲方无需承担任何责任")
        assert any(h["rule_name"] == "免责条款检测" for h in hits)

    def test_detect_payment_risk(self):
        """付款条件缺失应命中。"""
        hits = rule_engine.detect("甲方应在收到货物后付款")
        assert any(h["rule_name"] == "付款条件缺失检测" for h in hits)

    def test_no_risk_for_plain_clause(self):
        """普通条款不应命中任何规则。"""
        hits = rule_engine.detect("甲乙双方本着平等互利原则达成协议")
        assert hits == []

    def test_same_rule_hits_only_once(self):
        """同一条款含多个关键词，同一规则只命中一次。"""
        # 包含两个无限责任关键词，但只能命中一次
        hits = rule_engine.detect("乙方承担全部损失，承担全部责任")
        infinite = [h for h in hits if h["rule_name"] == "无限责任检测"]
        assert len(infinite) == 1

    def test_detect_skips_amount_rule(self):
        """detect() 不应触发合同级金额规则（即使传入 amount）。"""
        hits = rule_engine.detect("普通条款内容", amount=100000000)
        assert all("amount_threshold" not in h for h in hits)
        assert all(h["rule_name"] != "大额合同检测" for h in hits)


class TestContractLevelRule:
    """合同级规则（金额）测试。"""

    def test_large_amount_triggers(self):
        """金额超阈值应触发大额合同规则。"""
        hits = rule_engine.detect_contract_level(amount=6000000)
        assert len(hits) == 1
        assert hits[0]["rule_name"] == "大额合同检测"
        assert hits[0]["level"] == "HIGH"

    def test_small_amount_no_trigger(self):
        """金额低于阈值不应触发。"""
        hits = rule_engine.detect_contract_level(amount=100000)
        assert hits == []

    def test_none_amount_no_trigger(self):
        """金额为 None 不应触发。"""
        assert rule_engine.detect_contract_level(None) == []
        assert rule_engine.detect_contract_level() == []

    def test_boundary_amount(self):
        """金额等于阈值（500万）应触发（>= 判断）。"""
        hits = rule_engine.detect_contract_level(amount=5000000)
        assert len(hits) == 1


class TestCustomRules:
    """自定义规则注入。"""

    def test_custom_rules_override(self):
        """构造时传入自定义规则应生效。"""
        custom = [{
            "name": "测试规则",
            "category": "test",
            "risk_type": "测试风险",
            "keywords": ["测试关键词"],
            "level": "LOW",
            "description": "测试",
            "suggestion": "测试",
        }]
        engine = RuleEngine(rules=custom)
        hits = engine.detect("包含测试关键词的内容")
        assert len(hits) == 1
        assert hits[0]["risk_type"] == "测试风险"


def test_default_rules_count():
    """默认规则数量应稳定（防止误删规则）。"""
    assert len(DEFAULT_RULES) >= 6
    # 至少包含一个合同级（金额）规则
    assert any("amount_threshold" in r for r in DEFAULT_RULES)
