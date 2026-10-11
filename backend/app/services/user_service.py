"""用户认证服务。"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.core.config import settings
from app.utils.logger import logger


class UserService:
    """用户管理服务。"""

    def create_user(
        self, db: Session, username: str, password: str, role: str = "employee"
    ) -> User:
        user = User(
            username=username,
            password_hash=self._hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate(
        self, db: Session, username: str, password: str
    ) -> Optional[User]:
        """验证用户名密码。"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if self._verify_password(password, user.password_hash):
            return user
        return None

    def get_user(self, db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    # ---------- 密码处理（简化实现） ----------
    @staticmethod
    def _hash_password(password: str) -> str:
        """密码哈希（简化：SHA256；生产建议 bcrypt）。"""
        import hashlib

        salt = settings.SECRET_KEY
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        import hashlib

        salt = settings.SECRET_KEY
        expected = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
        return expected == password_hash

    def ensure_default_admin(self, db: Session) -> None:
        """确保存在默认管理员账号（用于首次启动）。"""
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            self.create_user(db, "admin", "admin123", role="admin")
            logger.info("已创建默认管理员账号 admin/admin123")


user_service = UserService()
