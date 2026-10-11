"""Prompt 集中管理。

将 Prompt 从代码中抽离，方便调整、A/B 测试和版本管理。
所有 Prompt 均为字符串模板，使用 .format() 填充变量。
"""

# ============ 合同解析 Prompt ============
CONTRACT_PARSE_PROMPT = """你是一名资深合同解析专家。请分析以下合同文本，提取结构化信息。

【合同文本】
{contract_text}

请提取以下信息并以 JSON 格式返回（只返回 JSON，不要其他文字）：
{{
  "contract_type": "合同类型（采购/销售/技术/劳动/保密/其他）",
  "party_a": "甲方名称",
  "party_b": "乙方名称",
  "amount": "合同金额（数字，若无则 null）",
  "sign_date": "签署日期",
  "summary": "合同主要内容一句话概括"
}}
"""

# ============ 条款抽取 Prompt ============
CLAUSE_EXTRACT_PROMPT = """你是一名合同条款分析专家。请将以下合同文本拆分为关键条款。

【合同文本】
{contract_text}

【条款分类参考】
合同主体、合同期限、付款方式、交付条款、验收条款、违约责任、争议解决、解除条款、保密条款、知识产权

请输出 JSON 数组，每个元素包含：
{{
  "clause_name": "条款名称",
  "clause_type": "条款类型(party/term/payment/delivery/acceptance/liability/dispute/termination/confidential/ip/other)",
  "content": "条款原文内容"
}}
只返回 JSON 数组，不要其他文字。
"""

# ============ 风险分析 Prompt ============
RISK_ANALYSIS_PROMPT = """你是一名企业法务专家，负责审查合同条款风险。

【合同条款】
{clause}

【企业制度/法律依据】
{legal_context}

请基于以上资料（不得脱离资料推测）分析该条款风险，输出 JSON：
{{
  "has_risk": true,
  "risk_type": "风险类型（违约责任风险/付款风险/知识产权风险/数据安全风险/解除条款风险/争议解决风险/主体资格风险/无风险）",
  "risk_category": "liability/payment/ip/data_security/termination/dispute/qualification/none",
  "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
  "description": "风险原因说明",
  "suggestion": "具体修改建议"
}}
只返回 JSON，不要其他文字。
"""

# ============ 法律检索 Query 生成 Prompt ============
LEGAL_QUERY_PROMPT = """你是一名法律检索专家。针对以下合同条款，生成检索关键词，用于查找相关法律依据和企业制度。

【合同条款】
{clause}

请输出 JSON：
{{
  "risk_type": "可能的风险类型",
  "keywords": ["关键词1", "关键词2", "关键词3"]
}}
只返回 JSON，不要其他文字。
"""

# ============ 报告生成 Prompt ============
REPORT_SUMMARY_PROMPT = """你是一名企业法务主管。请根据以下合同审查结果，生成一份专业、简洁的审查报告摘要。

【合同信息】
{contract_info}

【风险列表】
{risk_list}

请输出 JSON：
{{
  "summary": "总体审查结论（100字以内）",
  "overall_level": "综合风险等级（LOW/MEDIUM/HIGH/CRITICAL）",
  "key_concerns": ["需要重点关注的事项1", "事项2"]
}}
只返回 JSON，不要其他文字。
"""

# ============ 智能问答 Prompt ============
QA_PROMPT = """你是一名企业法务助手。请基于以下合同信息和审查结果回答用户问题。

【合同信息】
{contract_info}

【审查结果】
{review_result}

【用户问题】
{question}

要求：
1. 不得编造法律依据，所有风险必须引用已有审查结果中的来源
2. 给出明确、可执行的建议
3. 回答简洁专业
"""
