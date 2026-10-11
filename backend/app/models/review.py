"""审查任务与 Agent 执行日志模型。"""
from sqlalchemy import Column, String, Integer, Float, JSON

from app.database.session import Base
from app.utils.file import gen_uuid, now_iso


class ReviewTask(Base):
    """审查任务表。"""
    __tablename__ = "review_tasks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    contract_id = Column(String(36), nullable=False, index=True)
    creator_id = Column(String(36), nullable=True)
    task_type = Column(String(32), default="full")  # full/partial
    # pending -> running -> completed -> failed
    status = Column(String(32), default="pending")
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(64), nullable=True)
    error_message = Column(String(512), nullable=True)
    start_time = Column(String(32), nullable=True)
    end_time = Column(String(32), nullable=True)
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "creator_id": self.creator_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "error_message": self.error_message,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class AgentExecutionLog(Base):
    """Agent 执行记录表（项目A区别于项目B的重要设计）。"""
    __tablename__ = "agent_execution_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    task_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(64), nullable=False)  # ParserAgent/RiskAgent...
    action = Column(String(128), nullable=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    duration = Column(Float, nullable=True)  # 秒
    status = Column(String(32), default="success")  # success/failed
    created_at = Column(String(32), default=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "action": self.action,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "duration": self.duration,
            "status": self.status,
        }
