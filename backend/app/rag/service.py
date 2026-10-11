"""RAG 服务层：封装检索能力，供 Agent Tool 调用。

提供 search_legal_basis 等方法，Agent 不直接访问向量库。
"""
from typing import List, Dict, Any, Optional

from app.rag.hybrid_search import hybrid_retriever, reranker
from app.rag.vector_store import vector_store
from app.utils.logger import logger


class RagService:
    """RAG 检索服务。"""

    def search_legal_basis(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """检索法律依据/企业制度/历史案例。

        Args:
            query: 检索查询（如「违约责任风险」）
            top_k: 返回数量
            metadata_filter: 元数据过滤（如 clause_type）
        """
        # 混合检索粗召回
        retrieved = hybrid_retriever.retrieve(
            query, top_k=top_k * 4, metadata_filter=metadata_filter
        )
        # Reranker 精排序
        ranked = reranker.rerank(query, retrieved, top_k=top_k)
        return [
            {
                "text": d.get("text", ""),
                "score": round(d.get("rerank_score", d.get("score", 0)), 4),
                "metadata": d.get("metadata", {}),
            }
            for d in ranked
        ]

    def get_context(self, query: str, top_k: int = 3) -> str:
        """获取检索上下文（拼接成文本，供 LLM 分析）。"""
        results = self.search_legal_basis(query, top_k=top_k)
        if not results:
            return "（未检索到相关依据）"
        parts = []
        for i, r in enumerate(results, 1):
            source = r.get("metadata", {}).get("source", "未知来源")
            parts.append(f"[{i}] {r['text']}（来源：{source}）")
        return "\n".join(parts)


# 全局单例
rag_service = RagService()
