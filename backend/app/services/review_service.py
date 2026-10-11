"""审查任务服务。"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.review import ReviewTask
from app.utils.file import now_iso
from app.utils.logger import logger


class ReviewService:
    """审查任务管理服务。"""

    def create_task(
        self, db: Session, contract_id: str, task_type: str = "full",
        creator_id: Optional[str] = None,
    ) -> ReviewTask:
        task = ReviewTask(
            contract_id=contract_id,
            task_type=task_type,
            creator_id=creator_id,
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def get_task(self, db: Session, task_id: str) -> Optional[ReviewTask]:
        return db.query(ReviewTask).filter(ReviewTask.id == task_id).first()

    def update_status(
        self, db: Session, task_id: str, status: str,
        progress: Optional[int] = None, current_step: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        task = self.get_task(db, task_id)
        if not task:
            return
        task.status = status
        if progress is not None:
            task.progress = progress
        if current_step is not None:
            task.current_step = current_step
        if error_message is not None:
            task.error_message = error_message
        if status in ("completed", "failed"):
            task.end_time = now_iso()
        elif status == "running" and not task.start_time:
            task.start_time = now_iso()
        db.commit()


review_service = ReviewService()
