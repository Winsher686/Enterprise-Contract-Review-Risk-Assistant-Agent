"""LLM 客户端单元测试（Mock 模式行为）。

测试 _extract_section、_mock_embed、_mock_risk_analysis 等纯逻辑，
不依赖真实 API。
"""
from app.core.llm import LLMClient


class TestMockEmbed:
    def test_embed_returns_normalized_vector(self):
        """Mock 向量应为归一化的 128 维向量。"""
        client = LLMClient()
        client.use_mock = True
        vec = client._mock_embed("违约责任")
        assert len(vec) == 128
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-6

    def test_similar_text_similar_vector(self):
        """相似文本向量应相似（点积 > 不相关文本）。"""
        client = LLMClient()
        client.use_mock = True
        v1 = client._mock_embed("违约责任")
        v2 = client._mock_embed("违约责任条款")
        v3 = client._mock_embed("完全无关的内容")
        sim_same = sum(a * b for a, b in zip(v1, v2))
        sim_diff = sum(a * b for a, b in zip(v1, v3))
        assert sim_same > sim_diff


class TestExtractSection:
    def test_extract_between_markers(self):
        """提取两个【】标记之间的内容。"""
        client = LLMClient()
        prompt = "前言【合同条款】真实条款内容【企业制度】依据内容"
        assert client._extract_section(prompt, "【合同条款】") == "真实条款内容"

    def test_extract_to_end_when_no_next_marker(self):
        """无后续标记时提取到结尾。"""
        client = LLMClient()
        prompt = "【合同文本】这是合同全部内容"
        assert client._extract_section(prompt, "【合同文本】") == "这是合同全部内容"

    def test_extract_returns_whole_prompt_when_marker_missing(self):
        """标记不存在时返回原 prompt。"""
        client = LLMClient()
        prompt = "没有标记的内容"
        assert client._extract_section(prompt, "【不存在】") == prompt


class TestMockRiskAnalysis:
    def test_liability_risk(self):
        """「无需承担」应判定为违约责任风险 HIGH。"""
        client = LLMClient()
        import json
        result = json.loads(client._mock_risk_analysis("【合同条款】乙方无需承担任何责任"))
        assert result["has_risk"] is True
        assert result["risk_level"] == "HIGH"

    def test_payment_risk(self):
        """「收到货物后付款」应判定为付款风险。"""
        client = LLMClient()
        import json
        result = json.loads(client._mock_risk_analysis("【合同条款】甲方收到货物后付款"))
        assert result["risk_category"] == "payment"

    def test_no_risk(self):
        """普通条款应判定为无风险。"""
        client = LLMClient()
        import json
        result = json.loads(client._mock_risk_analysis("【合同条款】双方友好协商合作"))
        assert result["has_risk"] is False


class TestExtractJson:
    def test_direct_json(self):
        client = LLMClient()
        assert client._extract_json('{"a": 1}') == {"a": 1}

    def test_json_in_code_block(self):
        client = LLMClient()
        text = '```json\n{"b": 2}\n```'
        assert client._extract_json(text) == {"b": 2}

    def test_json_embedded_in_text(self):
        client = LLMClient()
        text = '结果是：{"c": 3} 完毕'
        assert client._extract_json(text) == {"c": 3}

    def test_invalid_json_returns_empty(self):
        client = LLMClient()
        assert client._extract_json("这不是 JSON") == {}
        assert client._extract_json("") == {}
