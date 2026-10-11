"""LLM 客户端封装。

支持两种模式：
- Mock 模式：未配置 API Key 时，用内置规则/启发式返回结果，保证流程可跑通
- 真实模式：配置 API Key 后，调用 OpenAI 协议接口

Agent 层通过统一接口 LLMClient 调用，无需关心底层实现。
"""
import json
import re
from typing import Any, Optional

from app.core.config import settings
from app.utils.logger import logger


class LLMClient:
    """统一 LLM 调用接口。"""

    def __init__(self) -> None:
        self.use_mock = settings.use_mock_llm
        self._client = None
        if not self.use_mock:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=settings.LLM_API_KEY,
                    base_url=settings.LLM_BASE_URL,
                )
                logger.info(
                    f"LLM 客户端初始化：真实模式 model={settings.LLM_MODEL}"
                )
            except Exception as e:  # pragma: no cover
                logger.error(f"OpenAI 客户端初始化失败，降级为 Mock：{e}")
                self.use_mock = True
        else:
            logger.info("LLM 客户端初始化：Mock 模式（未配置 API Key）")

    def chat(self, prompt: str, system: Optional[str] = None) -> str:
        """对话接口，返回文本。"""
        if self.use_mock:
            return self._mock_chat(prompt)
        return self._real_chat(prompt, system)

    def _real_chat(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        return resp.choices[0].message.content or ""

    def chat_json(self, prompt: str, system: Optional[str] = None) -> Any:
        """对话接口，返回解析后的 JSON。"""
        text = self.chat(prompt, system)
        return self._extract_json(text)

    def embed(self, text: str) -> list:
        """文本向量化。Mock 模式下返回伪向量（基于字符哈希）。"""
        if self.use_mock:
            return self._mock_embed(text)
        resp = self._client.embeddings.create(
            model=settings.LLM_EMBEDDING_MODEL, input=text
        )
        return resp.data[0].embedding

    @staticmethod
    def _extract_json(text: str) -> Any:
        """从 LLM 输出中稳健提取 JSON。"""
        if not text:
            return {}
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 尝试提取 ```json ... ``` 代码块
        m = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # 提取第一个 { } 或 [ ] 块
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        logger.warning(f"无法解析 LLM 输出为 JSON：{text[:200]}")
        return {}

    # ---------- Mock 实现 ----------
    def _mock_embed(self, text: str) -> list:
        """伪向量：128 维，基于字符 hash，保证相似文本向量相似。"""
        dim = 128
        vec = [0.0] * dim
        # 简单 bag-of-words 哈希
        for ch in text:
            idx = ord(ch) % dim
            vec[idx] += 1.0
        # 归一化
        norm = (sum(v * v for v in vec)) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def _mock_chat(self, prompt: str) -> str:
        """Mock 回复：根据 prompt 内容启发式返回。"""
        if "合同类型" in prompt and "contract_type" in prompt:
            return self._mock_parse(prompt)
        if "条款" in prompt and "clause_type" in prompt and "clause_name" in prompt:
            return self._mock_clause_extract(prompt)
        if "has_risk" in prompt and "risk_level" in prompt:
            return self._mock_risk_analysis(prompt)
        if "keywords" in prompt and "risk_type" in prompt:
            return self._mock_legal_query(prompt)
        if "overall_level" in prompt and "summary" in prompt:
            return self._mock_report_summary(prompt)
        # 默认返回
        return '{"result": "mock response"}'

    @staticmethod
    def _extract_section(prompt: str, marker: str) -> str:
        """从 prompt 中提取【marker】标记后的真实内容段落。

        提取 marker 后到下一个【...】标记之间的文本，用于 Mock 模式
        基于真实合同内容做启发式分析（而非对整个 prompt 做关键词匹配）。
        """
        idx = prompt.find(marker)
        if idx == -1:
            return prompt
        start = idx + len(marker)
        rest = prompt[start:]
        # 截取到下一个【】标记
        end = rest.find("【")
        if end == -1:
            return rest.strip()
        return rest[:end].strip()

    def _mock_parse(self, prompt: str) -> str:
        text = self._extract_section(prompt, "【合同文本】")
        contract_type = "采购合同"
        for kw, t in [("采购", "采购合同"), ("销售", "销售合同"),
                      ("技术", "技术合同"), ("劳动", "劳动合同"),
                      ("保密", "保密协议")]:
            if kw in text:
                contract_type = t
                break
        # 从文本中尝试提取金额
        amount = 5000000
        m = re.search(r"([\d,，.]+)\s*万", text)
        if m:
            try:
                amount = float(m.group(1).replace(",", "").replace("，", "")) * 10000
            except ValueError:
                pass
        # 尝试提取签署日期
        sign_date = ""
        m = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月", text)
        if m:
            sign_date = f"{m.group(1)}-{m.group(2).zfill(2)}-01"
        result = {
            "contract_type": contract_type,
            "party_a": "甲方",
            "party_b": "乙方",
            "amount": amount,
            "sign_date": sign_date or "2026-01-01",
            "summary": f"这是一份{contract_type}",
        }
        return json.dumps(result, ensure_ascii=False)

    def _mock_clause_extract(self, prompt: str) -> str:
        """基于真实合同文本按条款切分（而非写死的通用条款）。"""
        text = self._extract_section(prompt, "【合同文本】")
        # 复用规则切分逻辑，按「第X条」等标记切分
        from app.rag.chunker import split_clauses

        raw_clauses = split_clauses(text)
        # 条款类型 -> 中文名映射
        type_map = {
            "party": "合同主体", "term": "合同期限", "payment": "付款方式",
            "delivery": "交付条款", "acceptance": "验收条款",
            "liability": "违约责任", "dispute": "争议解决",
            "termination": "解除条款", "confidential": "保密条款",
            "ip": "知识产权",
        }
        clauses = []
        for c in raw_clauses:
            title = c.get("title", "") or "其他条款"
            content = c.get("content", "")
            # 根据标题关键词推断条款类型
            clause_type = "other"
            clause_name = title
            for t, cn in type_map.items():
                if cn in title:
                    clause_type = t
                    clause_name = cn
                    break
            clauses.append({
                "clause_name": clause_name,
                "clause_type": clause_type,
                "content": content,
            })
        return json.dumps(clauses, ensure_ascii=False)

    def _mock_risk_analysis(self, prompt: str) -> str:
        """基于真实条款内容判断风险（提取【合同条款】部分，而非整个 prompt）。"""
        clause = self._extract_section(prompt, "【合同条款】")
        if "无需承担" in clause or "全部责任" in clause or "全部损失" in clause \
                or "无限责任" in clause or "概不负责" in clause:
            result = {
                "has_risk": True,
                "risk_type": "违约责任风险",
                "risk_category": "liability",
                "risk_level": "HIGH",
                "description": "条款未限定责任范围，存在责任过宽或单方免责风险。",
                "suggestion": "建议限定责任范围，明确双方责任边界和赔偿上限。",
            }
        elif "收到货物后付款" in clause or "验收后付款" in clause \
                or ("付款" in clause and "验收" not in clause):
            result = {
                "has_risk": True,
                "risk_type": "付款风险",
                "risk_category": "payment",
                "risk_level": "MEDIUM",
                "description": "付款条件不明确，未约定验收标准和期限。",
                "suggestion": "建议增加验收标准、验收期限及付款触发条件。",
            }
        elif "保密" in clause:
            result = {
                "has_risk": True,
                "risk_type": "保密风险",
                "risk_category": "confidential",
                "risk_level": "LOW",
                "description": "保密范围未明确界定。",
                "suggestion": "建议明确保密信息的范围和保密期限。",
            }
        elif "自动续约" in clause or "自动顺延" in clause:
            result = {
                "has_risk": True,
                "risk_type": "合同期限风险",
                "risk_category": "term",
                "risk_level": "MEDIUM",
                "description": "存在自动续约条款，可能产生持续义务。",
                "suggestion": "建议明确续约条件及解约通知期限。",
            }
        elif "归" in clause and ("成果" in clause or "知识产权" in clause):
            result = {
                "has_risk": True,
                "risk_type": "知识产权风险",
                "risk_category": "ip",
                "risk_level": "MEDIUM",
                "description": "知识产权归属约定不清晰。",
                "suggestion": "建议明确知识产权的归属、使用范围及授权方式。",
            }
        else:
            result = {
                "has_risk": False,
                "risk_type": "无风险",
                "risk_category": "none",
                "risk_level": "LOW",
                "description": "未发现明显风险。",
                "suggestion": "",
            }
        return json.dumps(result, ensure_ascii=False)

    def _mock_legal_query(self, prompt: str) -> str:
        result = {
            "risk_type": "违约责任风险",
            "keywords": ["违约责任", "责任范围", "免责条款"],
        }
        return json.dumps(result, ensure_ascii=False)

    def _mock_report_summary(self, prompt: str) -> str:
        result = {
            "summary": "该合同存在若干需关注的风险点，建议法务人员重点审核违约责任和付款条款。",
            "overall_level": "HIGH",
            "key_concerns": ["违约责任条款责任范围过宽", "付款条件不明确"],
        }
        return json.dumps(result, ensure_ascii=False)


# 全局单例
llm_client = LLMClient()
