"""向量存储封装。

双模式实现：
- USE_DOCKER=true  -> Milvus（真实向量库，需 pymilvus + Milvus 服务）
- USE_DOCKER=false -> 内存向量存储（基于 numpy 余弦相似度，零依赖降级）

两种模式暴露完全一致的 add / search / count 接口，上层无需感知差异。
Milvus 连接失败时自动降级为内存模式，保证核心流程不中断。
"""
from typing import List, Dict, Any, Optional

import numpy as np

from app.core.config import settings
from app.core.llm import llm_client
from app.utils.logger import logger

# 向量维度：与 Mock embed 保持一致的默认值；真实 embedding 模型可能不同，
# 首次建集合时以首条向量维度为准动态创建。
_DEFAULT_DIM = 128


class VectorStore:
    """统一向量存储接口。

    Milvus 模式下的集合名来自 settings.MILVUS_COLLECTION。
    """

    def __init__(self) -> None:
        self._use_milvus = settings.USE_DOCKER
        self._memory_store: List[Dict[str, Any]] = []
        self._milvus_collection = None
        self._milvus_dim: Optional[int] = None
        self._milvus_available = False

        if self._use_milvus:
            self._init_milvus()
        else:
            logger.info("向量存储：内存模式（降级）")

    # ---------------- Milvus 初始化 ----------------
    def _init_milvus(self) -> None:
        """尝试连接 Milvus；失败则降级为内存模式。"""
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )

            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
            self._collection_name = settings.MILVUS_COLLECTION

            if utility.has_collection(self._collection_name):
                self._milvus_collection = Collection(self._collection_name)
                self._milvus_collection.load()
                # 从已存在集合推断向量维度
                for f in self._milvus_collection.schema.fields:
                    if f.dtype == DataType.FLOAT_VECTOR:
                        self._milvus_dim = f.params.get("dim")
                        break
            else:
                # 首次：用默认维度建集合（嵌入维度一致时无需改动）
                fields = [
                    FieldSchema(
                        name="id",
                        dtype=DataType.VARCHAR,
                        is_primary=True,
                        max_length=128,
                    ),
                    FieldSchema(
                        name="text",
                        dtype=DataType.VARCHAR,
                        max_length=4096,
                    ),
                    FieldSchema(
                        name="source",
                        dtype=DataType.VARCHAR,
                        max_length=256,
                    ),
                    FieldSchema(
                        name="category",
                        dtype=DataType.VARCHAR,
                        max_length=128,
                    ),
                    FieldSchema(
                        name="vector",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=_DEFAULT_DIM,
                    ),
                ]
                schema = CollectionSchema(
                    fields, description="合同审查法律知识库向量集合"
                )
                self._milvus_collection = Collection(
                    self._collection_name, schema=schema
                )
                self._milvus_dim = _DEFAULT_DIM

                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "IP",
                    "params": {"nlist": 128},
                }
                self._milvus_collection.create_index(
                    field_name="vector", index_params=index_params
                )
                self._milvus_collection.load()

            self._milvus_available = True
            logger.info(
                f"向量存储：Milvus 模式（host={settings.MILVUS_HOST}:"
                f"{settings.MILVUS_PORT}, collection={self._collection_name}, "
                f"dim={self._milvus_dim}）"
            )
        except Exception as e:  # pragma: no cover - 依赖外部服务
            self._milvus_available = False
            logger.warning(f"Milvus 连接失败，降级为内存模式：{e}")

    @property
    def _effective_mode(self) -> str:
        return "milvus" if self._milvus_available else "memory"

    # ---------------- 对外接口 ----------------
    def add(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> List[str]:
        """批量添加文本，返回 ID 列表。"""
        metadatas = metadatas or [{}] * len(texts)
        vectors = [llm_client.embed(t) for t in texts]

        if self._milvus_available:
            try:
                return self._add_milvus(texts, metadatas, vectors)
            except Exception as e:  # pragma: no cover
                logger.warning(f"Milvus 写入失败，降级内存：{e}")
                self._milvus_available = False

        return self._add_memory(texts, metadatas, vectors)

    def _add_memory(self, texts, metadatas, vectors) -> List[str]:
        ids = []
        base = len(self._memory_store)
        for i, (t, v, m) in enumerate(zip(texts, vectors, metadatas)):
            _id = f"chunk_{base}_{i}"
            self._memory_store.append({
                "id": _id,
                "text": t,
                "vector": np.array(v, dtype=np.float32),
                "metadata": m,
            })
            ids.append(_id)
        return ids

    def _add_milvus(self, texts, metadatas, vectors) -> List[str]:
        import uuid

        rows = []
        ids = []
        for i, (t, v, m) in enumerate(zip(texts, vectors, metadatas)):
            _id = f"chunk_{uuid.uuid4().hex}"
            rows.append([
                _id,
                t,
                m.get("source", ""),
                m.get("category", ""),
                [float(x) for x in v],
            ])
            ids.append(_id)
        self._milvus_collection.insert(rows)
        self._milvus_collection.flush()
        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """向量检索，返回 [{id, text, metadata, score}]。"""
        if self._milvus_available:
            try:
                return self._search_milvus(query, top_k, metadata_filter)
            except Exception as e:  # pragma: no cover
                logger.warning(f"Milvus 检索失败，降级内存：{e}")
                self._milvus_available = False

        return self._search_memory(query, top_k, metadata_filter)

    def _search_memory(self, query, top_k, metadata_filter) -> List[Dict[str, Any]]:
        query_vec = np.array(llm_client.embed(query), dtype=np.float32)
        results = []
        for item in self._memory_store:
            if metadata_filter:
                skip = False
                for k, v in metadata_filter.items():
                    if item["metadata"].get(k) != v:
                        skip = True
                        break
                if skip:
                    continue
            score = float(np.dot(query_vec, item["vector"]))
            results.append({
                "id": item["id"],
                "text": item["text"],
                "metadata": item["metadata"],
                "score": score,
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _search_milvus(self, query, top_k, metadata_filter) -> List[Dict[str, Any]]:
        query_vec = [float(x) for x in llm_client.embed(query)]
        search_params = {"metric_type": "IP", "params": {"nprobe": 16}}
        output_fields = ["id", "text", "source", "category"]

        expr = None
        if metadata_filter:
            conditions = []
            if "source" in metadata_filter:
                conditions.append(f'source == "{metadata_filter["source"]}"')
            if "category" in metadata_filter:
                conditions.append(f'category == "{metadata_filter["category"]}"')
            expr = " and ".join(conditions) if conditions else None

        res = self._milvus_collection.search(
            data=[query_vec],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=output_fields,
        )
        results = []
        for hit in res[0]:
            entity = hit.entity
            results.append({
                "id": entity.get("id"),
                "text": entity.get("text", ""),
                "metadata": {
                    "source": entity.get("source", ""),
                    "category": entity.get("category", ""),
                },
                "score": float(hit.distance),
            })
        return results

    def count(self) -> int:
        if self._milvus_available:
            try:
                return self._milvus_collection.num_entities
            except Exception as e:  # pragma: no cover
                logger.warning(f"Milvus 计数失败，降级内存：{e}")
                self._milvus_available = False
        return len(self._memory_store)


# 全局单例
vector_store = VectorStore()
