"""用户模型。"""
from sqlalchemy import Column, String, Integer, DateTime

from app.database.session import Base
from app.utils.file import gen_uuid, now_iso


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True)
    password_hash = Column(String(256), nullable=False)
    # 角色：admin / legal / employee
    role = Column(String(32), default="employee", nullable=False)
    department = Column(String(128), nullable=True)
    status = Column(Integer, default=1)  # 1=正常 0=禁用
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "status": self.status,
            "created_at": self.created_at,
        }
