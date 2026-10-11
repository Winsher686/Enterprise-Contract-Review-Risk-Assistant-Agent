"""风险规则引擎（Rule Engine）。

对应规划文档阶段七「三层检测模型」的第一层：规则检测。
用于发现具有明确条件、可被关键词/规则判断的风险。
"""
from typing import List, Dict, Any, Optional

# 内置风险规则
DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "name": "无限责任检测",
        "category": "liability",
        "risk_type": "违约责任风险",
        "keywords": ["无限责任", "承担全部损失", "承担全部责任", "所有责任", "全部赔偿"],
        "level": "HIGH",
        "description": "条款存在责任范围过宽/无限责任风险。",
        "suggestion": "建议限定责任范围，明确责任上限及赔偿范围。",
    },
    {
        "name": "免责条款检测",
        "category": "liability",
        "risk_type": "违约责任风险",
        "keywords": ["无需承担", "不承担任何责任", "免除一切责任", "概不负责"],
        "level": "HIGH",
        "description": "条款存在单方免责/责任缺失风险。",
        "suggestion": "建议明确双方违约责任，避免单方免责。",
    },
    {
        "name": "付款条件缺失检测",
        "category": "payment",
        "risk_type": "付款风险",
        "keywords": ["收到货物后付款", "验收后付款", "见票付款"],
        "level": "MEDIUM",
        "description": "付款条件不明确，未约定验收标准和期限。",
        "suggestion": "建议明确验收标准、验收期限及付款触发条件。",
    },
    {
        "name": "自动续约检测",
        "category": "term",
        "risk_type": "合同期限风险",
        "keywords": ["自动续约", "自动顺延", "到期自动续"],
        "level": "MEDIUM",
        "description": "存在自动续约条款，可能产生持续义务。",
        "suggestion": "建议明确续约条件及解约通知期限。",
    },
    {
        "name": "知识产权归属缺失检测",
        "category": "ip",
        "risk_type": "知识产权风险",
        "keywords": ["开发成果归", "技术成果", "知识产权归属"],
        "level": "MEDIUM",
        "description": "知识产权归属约定不清晰。",
        "suggestion": "建议明确知识产权的归属、使用范围及授权方式。",
    },
    {
        "name": "大额合同检测",
        "category": "payment",
        "risk_type": "付款风险",
        "keywords": [],  # 特殊规则，基于金额判断
        "level": "HIGH",
        "description": "合同金额较大，需重点关注审批流程。",
        "suggestion": "建议确认是否已满足企业内部大额合同审批要求。",
        "amount_threshold": 5000000,
    },
]


class RuleEngine:
    """风险规则引擎。"""

    def __init__(self, rules: Optional[List[Dict]] = None) -> None:
        self.rules = rules or DEFAULT_RULES

    def _build_hit(self, rule: Dict, **extra) -> Dict[str, Any]:
        """构造规则命中结果。"""
        hit = {
            "risk_type": rule["risk_type"],
            "category": rule["category"],
            "level": rule["level"],
            "description": rule["description"],
            "suggestion": rule["suggestion"],
            "rule_name": rule["name"],
            "source": "rule_engine",
        }
        hit.update(extra)
        return hit

    def detect(
        self, clause_text: str, amount: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """检测条款是否命中「条款级」规则（关键词规则）。

        注意：金额规则属于「合同级」规则，不应在此方法中触发，
        否则会针对每个条款重复命中。请使用 detect_contract_level 单独处理。
        """
        hits = []
        for rule in self.rules:
            # 跳过金额（合同级）规则
            if "amount_threshold" in rule:
                continue
            for kw in rule["keywords"]:
                if kw in clause_text:
                    hits.append(self._build_hit(rule, matched_keyword=kw))
                    break  # 同一规则只命中一次
        return hits

    def detect_contract_level(self, amount: Optional[float] = None) -> List[Dict[str, Any]]:
        """检测「合同级」规则（如大额合同），整个合同只触发一次。"""
        hits = []
        if amount is None:
            return hits
        for rule in self.rules:
            if "amount_threshold" in rule:
                if amount >= rule["amount_threshold"]:
                    hits.append(self._build_hit(rule))
        return hits


# 全局单例
rule_engine = RuleEngine()
