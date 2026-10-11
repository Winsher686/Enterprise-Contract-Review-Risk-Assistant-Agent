"""合同管理 API。"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.contract_service import contract_service
from app.utils.logger import logger

router = APIRouter(prefix="/contracts", tags=["合同管理"])


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """上传合同文件并创建合同记录。"""
    file_bytes = await file.read()
    filename = file.filename or "contract.pdf"
    # 推断文件类型
    file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    # 合同名称默认用文件名
    contract_name = name or filename

    # 创建合同记录
    contract = contract_service.create_contract(db, name=contract_name)
    contract_file = contract_service.save_file(
        db, contract.id, file_bytes, filename, file_type
    )

    return {
        "contract_id": contract.id,
        "file_id": contract_file.id,
        "name": contract_name,
        "file_type": file_type,
        "status": "uploaded",
    }


@router.get("")
def list_contracts(db: Session = Depends(get_db)):
    contracts = contract_service.list_contracts(db)
    return [c.to_dict() for c in contracts]


@router.get("/{contract_id}")
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = contract_service.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    data = contract.to_dict()
    # 附带条款
    clauses = contract_service.get_clauses(db, contract_id)
    data["clauses"] = [c.to_dict() for c in clauses]
    return data
