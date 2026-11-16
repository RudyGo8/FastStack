"""持久任务队列模型。

与业务表解耦：只描述「任务 + 执行租约 + 预算 + 审批」，不携带任何业务字段。
Conversation 记录与 LangGraph Checkpoint 分别持久化，互不依赖。
"""

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase

TASK_STATUSES = (
    "created",
    "queued",
    "running",
    "waiting_approval",
    "completed",
    "failed",
    "cancelling",
    "cancelled",
)


class AgentTaskModel(MappedBase):
    """Agent 持久任务及执行租约。"""

    __tablename__: str = "ai_agent_task"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created','queued','running','waiting_approval','completed','failed','cancelling','cancelled')",
            name="ck_ai_agent_task_status",
        ),
        Index("uq_ai_agent_task_request", "owner_id", "session_id", "request_key", unique=True),
        Index("ix_ai_agent_task_owner_created", "owner_id", "created_at"),
        Index("ix_ai_agent_task_queue", "status", "lease_expires_at"),
        {"comment": "Agent 持久任务及执行租约"},
    )

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="服务端任务ID")
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="稳定系统用户ID")
    username: Mapped[str] = mapped_column(String(128), nullable=False, comment="创建时用户名快照")
    principal_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, comment="创建身份快照，恢复必须重新授权")
    session_id: Mapped[str] = mapped_column(String(120), nullable=False, comment="所属会话")
    thread_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, comment="服务端生成的独立 checkpoint 线程")
    request_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="会话内幂等请求键")
    prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="任务原始请求")
    status: Mapped[str] = mapped_column(String(24), nullable=False, comment="服务端生命周期状态")
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, comment="任务状态 schema 版本")
    generation: Mapped[int] = mapped_column(Integer, nullable=False, comment="执行代次 fencing token")
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="当前执行 worker 标识")
    lease_expires_at: Mapped[object | None] = mapped_column(DateTime, nullable=True, comment="UTC 执行租约截止")
    heartbeat_at: Mapped[object | None] = mapped_column(DateTime, nullable=True, comment="UTC 最近心跳")
    resolved_scope: Mapped[dict] = mapped_column(JSON, nullable=False, comment="冻结的绝对查询范围及时区")
    steps: Mapped[list] = mapped_column(JSON, nullable=False, comment="结构化步骤与副作用记录")
    budget: Mapped[dict] = mapped_column(JSON, nullable=False, comment="总预算配置及已用预算")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="验证后的结构化结果")
    approval: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="审批对象、参数摘要及服务端审批记录")
    error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="脱敏错误说明")
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, comment="UTC 创建时点")
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False, comment="UTC 更新时点")
    finished_at: Mapped[object | None] = mapped_column(DateTime, nullable=True, comment="UTC 终止时点")
    expires_at: Mapped[object | None] = mapped_column(DateTime, nullable=True, comment="终态保留截止")
