"""示例知识库加载器。

内置一些示例法律/企业制度知识，用于演示 RAG 检索能力。
生产环境应通过知识库管理 API 或导入脚本加载真实资料。
"""
from typing import List, Dict

from app.rag.vector_store import vector_store
from app.rag.hybrid_search import hybrid_retriever
from app.utils.logger import logger

# 内置示例知识（企业合同管理制度 + 常见法律要点）
DEFAULT_KNOWLEDGE: List[Dict] = [
    {
        "text": "企业合同管理制度第8条：合同中的违约责任条款应当明确约定双方的违约责任范围，"
                "不得出现单方免责或无限责任等显失公平的约定。",
        "source": "企业合同管理制度",
        "category": "company_rule",
    },
    {
        "text": "企业合同管理制度第5条：合同金额超过500万元的采购合同，必须经过法务部门审核并"
                "报公司管理层审批。",
        "source": "企业合同管理制度",
        "category": "company_rule",
    },
    {
        "text": "采购合同付款管理制度：付款条款应当明确约定付款比例、付款时间节点、验收标准及"
                "验收期限，避免因付款条件不明确产生争议。",
        "source": "采购付款管理制度",
        "category": "company_rule",
    },
    {
        "text": "民法典第五百八十五条：当事人可以约定一方违约时应当根据违约情况向对方支付一定"
                "数额的违约金。约定的违约金过分高于造成的损失的，人民法院可以适当减少。",
        "source": "中华人民共和国民法典",
        "category": "law",
    },
    {
        "text": "民法典合同编：当事人应当遵循公平原则确定各方的权利和义务。采用格式条款订立合同"
                "的，提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务。",
        "source": "中华人民共和国民法典",
        "category": "law",
    },
    {
        "text": "劳动合同法第二十四条：竞业限制的人员限于用人单位的高级管理人员、高级技术人员"
                "和其他负有保密义务的人员。竞业限制期限不得超过二年。",
        "source": "中华人民共和国劳动合同法",
        "category": "law",
    },
    {
        "text": "知识产权保护规范：技术开发合同应当明确约定技术成果的归属、使用范围及授权方式，"
                "避免因知识产权归属不清晰产生纠纷。",
        "source": "知识产权保护规范",
        "category": "company_rule",
    },
    {
        "text": "数据安全管理制度：涉及数据处理的技术服务合同应当约定数据安全责任、隐私保护义务"
                "及数据泄露的赔偿责任。",
        "source": "数据安全管理制度",
        "category": "company_rule",
    },
]


def load_default_knowledge() -> None:
    """加载默认示例知识库（幂等，避免重复加载）。"""
    if vector_store.count() > 0:
        logger.info(f"知识库已有 {vector_store.count()} 条数据，跳过默认加载")
        return

    texts = [k["text"] for k in DEFAULT_KNOWLEDGE]
    metadatas = [{"source": k["source"], "category": k["category"]} for k in DEFAULT_KNOWLEDGE]
    ids = vector_store.add(texts, metadatas)
    # 用与 vector_store 一致的 id 建立 BM25 索引，确保混合检索去重正确
    hybrid_retriever.index(texts, metadatas, ids=ids)
    logger.info(f"已加载默认知识库：{len(texts)} 条")
