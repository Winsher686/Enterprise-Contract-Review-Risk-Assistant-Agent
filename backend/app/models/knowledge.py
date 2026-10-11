"""法规知识库模型：文档表 + 知识切片表。"""
from sqlalchemy import Column, String, Text, JSON

from app.database.session import Base
from app.utils.file import gen_uuid, now_iso


class LegalDocument(Base):
    """法规知识文档表。"""
    __tablename__ = "legal_documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(256), nullable=False)  # 民法典/合同管理制度...
    category = Column(String(64), nullable=True)  # law/company_rule/case
    version = Column(String(32), nullable=True)
    source = Column(String(256), nullable=True)
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "source": self.source,
        }


class KnowledgeChunk(Base):
    """知识切片表（连接文档与向量库）。"""
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    content = Column(Text, nullable=False)
    # 注意：`metadata` 是 SQLAlchemy 保留属性名，此处用列名映射避免冲突
    chunk_metadata = Column("metadata", JSON, nullable=True)
    embedding_id = Column(String(128), nullable=True)  # 向量库中的 ID

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "metadata": self.chunk_metadata,
            "embedding_id": self.embedding_id,
        }
