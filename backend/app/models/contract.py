"""合同相关模型：合同主表、文件表、条款表。"""
from sqlalchemy import Column, String, Integer, Text, Float

from app.database.session import Base
from app.utils.file import gen_uuid, now_iso


class Contract(Base):
    """合同主表。"""
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(256), nullable=False)
    contract_type = Column(String(64), nullable=True)  # 采购/销售/技术/劳动...
    party_a = Column(String(128), nullable=True)  # 甲方
    party_b = Column(String(128), nullable=True)  # 乙方
    amount = Column(Float, nullable=True)  # 合同金额
    sign_date = Column(String(32), nullable=True)
    status = Column(String(32), default="uploaded")  # uploaded/parsed/reviewing/completed/failed
    creator_id = Column(String(36), nullable=True)
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "contract_type": self.contract_type,
            "party_a": self.party_a,
            "party_b": self.party_b,
            "amount": self.amount,
            "sign_date": self.sign_date,
            "status": self.status,
            "creator_id": self.creator_id,
            "created_at": self.created_at,
        }


class ContractFile(Base):
    """合同文件表。"""
    __tablename__ = "contract_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    contract_id = Column(String(36), nullable=False, index=True)
    file_name = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(32), nullable=True)  # pdf/docx/txt
    file_size = Column(Integer, nullable=True)
    # uploaded -> parsing -> completed -> failed
    parse_status = Column(String(32), default="uploaded")
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "parse_status": self.parse_status,
        }


class ContractClause(Base):
    """合同条款表（解析后的结构化条款）。"""
    __tablename__ = "contract_clauses"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    contract_id = Column(String(36), nullable=False, index=True)
    clause_name = Column(String(128), nullable=True)  # 违约责任/付款方式...
    clause_type = Column(String(64), nullable=True)  # liability/payment/ip...
    content = Column(Text, nullable=True)
    page_num = Column(Integer, nullable=True)
    order_num = Column(Integer, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "clause_name": self.clause_name,
            "clause_type": self.clause_type,
            "content": self.content,
            "page_num": self.page_num,
            "order_num": self.order_num,
        }
