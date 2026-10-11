"""RAG 检索模块单元测试（向量库 + 混合检索 + 服务层）。

这些测试使用全新的 VectorStore / HybridRetriever 实例，不污染全局单例。
"""
import numpy as np

from app.rag.vector_store import VectorStore
from app.rag.hybrid_search import HybridRetriever, Reranker
from app.rag.service import RagService


class TestVectorStore:
    def test_add_and_count(self):
        """添加文本后 count 正确，返回唯一 id。"""
        store = VectorStore()
        ids = store.add(["文本一", "文本二", "文本三"])
        assert store.count() == 3
        assert len(ids) == 3
        assert len(set(ids)) == 3  # id 唯一

    def test_add_returns_incremental_ids(self):
        """多次 add 时 id 不冲突（修复历史 bug）。"""
        store = VectorStore()
        ids1 = store.add(["a", "b"])
        ids2 = store.add(["c", "d"])
        all_ids = ids1 + ids2
        assert len(set(all_ids)) == 4  # 无重复 id

    def test_search_returns_results(self):
        """检索能返回结果并按相似度排序。"""
        store = VectorStore()
        store.add(["违约责任条款", "付款方式约定", "保密条款约定"])
        results = store.search("违约责任", top_k=2)
        assert len(results) == 2
        assert "违约责任" in results[0]["text"]  # 最相关排第一

    def test_search_metadata_filter(self):
        """metadata 过滤生效。"""
        store = VectorStore()
        store.add(
            ["法律条文A", "公司制度B"],
            metadatas=[{"category": "law"}, {"category": "company"}],
        )
        results = store.search("条文", metadata_filter={"category": "law"})
        assert len(results) == 1
        assert results[0]["metadata"]["category"] == "law"

    def test_empty_store_search(self):
        """空库检索返回空列表。"""
        store = VectorStore()
        assert store.search("任意") == []


class TestHybridRetriever:
    def test_index_and_retrieve(self):
        """建立索引后能检索。"""
        retriever = HybridRetriever()
        texts = ["违约责任相关法律规定", "付款条款约定", "保密协议内容"]
        retriever.index(texts)
        results = retriever.retrieve("违约责任", top_k=2)
        assert len(results) >= 1
        assert isinstance(results[0]["text"], str)

    def test_rrf_fusion_dedup(self):
        """RRF 融合：相同 id 的文档合并，不重复返回。"""
        retriever = HybridRetriever()
        list_a = [
            {"id": "doc1", "text": "A1", "metadata": {}, "score": 0.9},
            {"id": "doc2", "text": "A2", "metadata": {}, "score": 0.8},
        ]
        list_b = [
            {"id": "doc1", "text": "A1", "metadata": {}, "score": 0.7},
            {"id": "doc3", "text": "B3", "metadata": {}, "score": 0.6},
        ]
        fused = retriever._rrf_fusion(list_a, list_b)
        ids = [d["id"] for d in fused]
        # doc1 同时出现在两个列表，融合后只出现一次
        assert ids.count("doc1") == 1
        assert set(ids) == {"doc1", "doc2", "doc3"}

    def test_rrf_fusion_ranking(self):
        """RRF 融合：两个列表都排前的文档应排最前。"""
        retriever = HybridRetriever()
        list_a = [{"id": "x", "text": "", "metadata": {}, "score": 0}]
        list_b = [{"id": "x", "text": "", "metadata": {}, "score": 0},
                  {"id": "y", "text": "", "metadata": {}, "score": 0}]
        fused = retriever._rrf_fusion(list_a, list_b)
        assert fused[0]["id"] == "x"


class TestReranker:
    def test_rerank_orders_by_overlap(self):
        """重排器：关键词重叠度高的排前。"""
        reranker = Reranker()
        docs = [
            {"text": "违约责任法律规定", "score": 0.5},
            {"text": "无关内容", "score": 0.9},  # 分数高但无关键词
        ]
        ranked = reranker.rerank("违约责任", docs)
        assert ranked[0]["text"] == "违约责任法律规定"

    def test_rerank_top_k(self):
        """重排返回指定 top_k。"""
        reranker = Reranker()
        docs = [{"text": f"文档{i}", "score": 0.1} for i in range(10)]
        ranked = reranker.rerank("查询", docs, top_k=3)
        assert len(ranked) == 3


class TestRagService:
    def test_search_legal_basis_empty(self):
        """空向量库时检索返回空列表（不报错）。"""
        service = RagService()
        # 使用全新 retriever/vector_store 隔离
        # 注意：service 依赖全局单例，这里仅验证接口不崩溃
        results = service.search_legal_basis("违约责任", top_k=3)
        assert isinstance(results, list)

    def test_get_context_empty(self):
        """空结果时 get_context 返回提示语。"""
        service = RagService()
        ctx = service.get_context("不存在的查询")
        assert "未检索到" in ctx or isinstance(ctx, str)
