"""合同业务服务。"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.contract import Contract, ContractFile, ContractClause
from app.utils.file import save_upload_file
from app.utils.logger import logger


class ContractService:
    """合同管理服务。"""

    def create_contract(
        self,
        db: Session,
        name: str,
        contract_type: Optional[str] = None,
        party_a: Optional[str] = None,
        party_b: Optional[str] = None,
        amount: Optional[float] = None,
        creator_id: Optional[str] = None,
    ) -> Contract:
        contract = Contract(
            name=name,
            contract_type=contract_type,
            party_a=party_a,
            party_b=party_b,
            amount=amount,
            creator_id=creator_id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    def save_file(
        self,
        db: Session,
        contract_id: str,
        file_bytes: bytes,
        filename: str,
        file_type: str,
    ) -> ContractFile:
        file_path = save_upload_file(file_bytes, filename, "contracts")
        contract_file = ContractFile(
            contract_id=contract_id,
            file_name=filename,
            file_path=file_path,
            file_type=file_type,
            file_size=len(file_bytes),
        )
        db.add(contract_file)
        db.commit()
        db.refresh(contract_file)
        return contract_file

    def get_contract(self, db: Session, contract_id: str) -> Optional[Contract]:
        return db.query(Contract).filter(Contract.id == contract_id).first()

    def list_contracts(self, db: Session) -> List[Contract]:
        return db.query(Contract).order_by(Contract.created_at.desc()).all()

    def get_file(self, db: Session, contract_id: str) -> Optional[ContractFile]:
        return (
            db.query(ContractFile)
            .filter(ContractFile.contract_id == contract_id)
            .first()
        )

    def get_clauses(self, db: Session, contract_id: str) -> List[ContractClause]:
        return (
            db.query(ContractClause)
            .filter(ContractClause.contract_id == contract_id)
            .order_by(ContractClause.order_num)
            .all()
        )

    def save_clauses(
        self, db: Session, contract_id: str, clauses: List[dict]
    ) -> List[ContractClause]:
        """保存解析后的条款。"""
        saved = []
        for i, c in enumerate(clauses):
            clause = ContractClause(
                contract_id=contract_id,
                clause_name=c.get("clause_name"),
                clause_type=c.get("clause_type"),
                content=c.get("content"),
                order_num=c.get("order_num", i),
            )
            db.add(clause)
            saved.append(clause)
        db.commit()
        return saved

    def update_status(self, db: Session, contract_id: str, status: str) -> None:
        contract = self.get_contract(db, contract_id)
        if contract:
            contract.status = status
            db.commit()


contract_service = ContractService()
