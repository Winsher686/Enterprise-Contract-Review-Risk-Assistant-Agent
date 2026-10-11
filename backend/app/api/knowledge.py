"""知识库管理 API。"""
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.rag.vector_store import vector_store
from app.rag.hybrid_search import hybrid_retriever
from app.rag.service import rag_service

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class KnowledgeItem(BaseModel):
    text: str
    source: str = "manual"
    category: str = "company_rule"


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/add")
def add_knowledge(items: List[KnowledgeItem]):
    """添加知识条目到知识库。"""
    texts = [i.text for i in items]
    metadatas = [{"source": i.source, "category": i.category} for i in items]
    ids = vector_store.add(texts, metadatas)
    # 重建 BM25 索引（用与向量库一致的 id，确保混合检索去重正确）
    all_items = vector_store._memory_store
    all_texts = [item["text"] for item in all_items]
    all_metas = [item["metadata"] for item in all_items]
    all_ids = [item["id"] for item in all_items]
    hybrid_retriever.index(all_texts, all_metas, ids=all_ids)
    return {"added": len(ids), "ids": ids}


@router.post("/search")
def search_knowledge(req: SearchRequest):
    """检索知识库。"""
    results = rag_service.search_legal_basis(req.query, top_k=req.top_k)
    return results


@router.get("/stats")
def knowledge_stats():
    """知识库统计。"""
    return {"total_chunks": vector_store.count()}
