"""混合检索模块。

实现 Vector Search + BM25 关键词检索 + RRF 融合 + Reranker 排序，
对应规划文档阶段五的 RAG 检索链路设计。
"""
from typing import List, Dict, Any, Optional

from app.core.llm import llm_client
from app.rag.vector_store import vector_store
from app.utils.logger import logger


class HybridRetriever:
    """混合检索器。"""

    def __init__(self) -> None:
        self._bm25_corpus: List[Dict[str, Any]] = []
        self._bm25 = None

    def index(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """建立 BM25 索引（关键词检索）。

        ids 需与 vector_store 保持一致，确保 RRF 融合时能正确去重。
        """
        metadatas = metadatas or [{}] * len(texts)
        ids = ids or [str(i) for i in range(len(texts))]
        tokenized = [list(t) for t in texts]  # 字符级切分，避免分词依赖
        try:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi(tokenized)
            self._bm25_corpus = [
                {"id": _id, "text": t, "metadata": m, "tokens": tk}
                for _id, t, m, tk in zip(ids, texts, metadatas, tokenized)
            ]
            logger.info(f"BM25 索引建立完成，共 {len(texts)} 条")
        except ImportError:
            # 没有 rank_bm25 时降级为简单关键词匹配
            self._bm25 = None
            self._bm25_corpus = [
                {"id": _id, "text": t, "metadata": m, "tokens": list(t)}
                for _id, t, m in zip(ids, texts, metadatas)
            ]

    def _bm25_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """BM25 关键词检索。"""
        if not self._bm25_corpus:
            return []
        tokens = list(query)
        if self._bm25:
            scores = self._bm25.get_scores(tokens)
            ranked = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:top_k]
            results = []
            for i in ranked:
                item = self._bm25_corpus[i]
                results.append({
                    "id": item["id"],
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "score": float(scores[i]),
                })
            return results
        # 降级：简单字符重叠度
        results = []
        for i, item in enumerate(self._bm25_corpus):
            overlap = len(set(tokens) & set(item["tokens"]))
            results.append({
                "id": item["id"],
                "text": item["text"],
                "metadata": item["metadata"],
                "score": float(overlap),
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """混合检索主流程：向量 + BM25 -> RRF 融合 -> 返回 Top K。"""
        # 1. 向量检索（粗召回 Top20）
        vector_results = vector_store.search(
            query, top_k=20, metadata_filter=metadata_filter
        )
        # 2. BM25 关键词检索
        bm25_results = self._bm25_search(query, top_k=20)

        # 3. RRF 融合
        fused = self._rrf_fusion(vector_results, bm25_results)

        # 4. 返回 Top K
        return fused[:top_k]

    @staticmethod
    def _rrf_fusion(
        list_a: List[Dict], list_b: List[Dict], k: int = 60
    ) -> List[Dict]:
        """RRF (Reciprocal Rank Fusion) 融合两个排序列表。"""
        scores: Dict[str, float] = {}
        docs: Dict[str, Dict] = {}

        for rank, doc in enumerate(list_a):
            key = doc["id"]
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            docs[key] = doc
        for rank, doc in enumerate(list_b):
            key = doc["id"]
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            if key not in docs:
                docs[key] = doc

        fused = []
        for key, score in scores.items():
            doc = dict(docs[key])
            doc["score"] = score
            fused.append(doc)
        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused


class Reranker:
    """重排序器。

    Mock 模式：基于关键词重叠度的启发式重排。
    真实模式：可接入 CrossEncoder 模型（预留接口）。
    """

    def __init__(self) -> None:
        pass

    def rerank(
        self, query: str, docs: List[Dict[str, Any]], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """重排序，返回 Top K。"""
        query_tokens = set(list(query))
        for doc in docs:
            text_tokens = set(list(doc.get("text", "")))
            overlap = len(query_tokens & text_tokens)
            # 结合原始分数 + 重叠度
            doc["rerank_score"] = doc.get("score", 0) + overlap * 0.1
        ranked = sorted(docs, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return ranked[:top_k]


# 全局单例
hybrid_retriever = HybridRetriever()
reranker = Reranker()
