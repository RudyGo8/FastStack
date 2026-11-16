"""数据库原子任务队列。

每个方法独立事务；所有执行期写入都校验租约与代次（fencing token），
保证被抢占的 worker 无法提交结果。
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.database import async_db_session
from app.modules.ai.harness.contracts import Budget, Principal
from app.modules.ai.harness.model import AgentTaskModel

SCHEMA_VERSION = 1
TERMINAL = frozenset({"completed", "failed", "cancelled"})
MAX_GENERATIONS = 64
DELETED_SESSION_REASON = "关联会话已删除"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def serialize_task(task: AgentTaskModel) -> dict:
    """仅在通过 owner 查询后用于 API；日期统一用 ISO UTC 表示。"""
    return {
        column.name: (value.isoformat() + "Z" if isinstance(value, datetime) else value)
        for column in AgentTaskModel.__table__.columns
        if (value := getattr(task, column.name)) is not None
    }


class TaskStore:
    def __init__(self, session_factory=async_db_session, *, retention_seconds: int = 604800):
        self.session_factory = session_factory
        self.retention_seconds = retention_seconds

    async def create(
        self,
        principal: Principal,
        session_id: str,
        request_key: str,
        prompt: str,
        resolved_scope: dict,
        budget: dict | None = None,
    ) -> AgentTaskModel:
        if not session_id or not request_key or len(session_id) > 120 or len(request_key) > 128:
            raise ValueError("会话及请求幂等键无效")
        now = _utcnow()
        default_budget = Budget()
        budget_state = {
            f"max_{kind}": getattr(default_budget, f"max_{kind}")
            for kind in ("models", "tools", "steps", "tokens", "seconds")
        }
        budget_state.update(used=default_budget.snapshot())
        budget_state.update(budget or {})
        task = AgentTaskModel(
            task_id=str(uuid4()),
            thread_id=str(uuid4()),
            owner_id=principal.user_id,
            username=principal.username,
            principal_snapshot={"permissions": sorted(principal.permissions), "is_superuser": principal.is_superuser},
            session_id=session_id,
            request_key=request_key,
            prompt=prompt,
            status="queued",
            schema_version=SCHEMA_VERSION,
            generation=0,
            resolved_scope=resolved_scope,
            steps=[],
            budget=budget_state,
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as db:
            db.add(task)
            try:
                await db.commit()
                await db.refresh(task)
            except IntegrityError:
                await db.rollback()
                existing = await db.scalar(
                    select(AgentTaskModel).where(
                        AgentTaskModel.owner_id == principal.user_id,
                        AgentTaskModel.session_id == session_id,
                        AgentTaskModel.request_key == request_key,
                    )
                )
                if existing is None:
                    raise
                return existing
        return task

    async def get(self, task_id: str, owner_id: int):
        async with self.session_factory() as db:
            return await db.scalar(
                select(AgentTaskModel).where(AgentTaskModel.task_id == task_id, AgentTaskModel.owner_id == owner_id)
            )

    async def list(self, owner_id: int, *, session_id: str | None = None, limit: int = 50):
        query = select(AgentTaskModel).where(AgentTaskModel.owner_id == owner_id)
        if session_id is not None:
            query = query.where(AgentTaskModel.session_id == session_id)
        async with self.session_factory() as db:
            rows = await db.scalars(
                query.order_by(AgentTaskModel.created_at.desc()).limit(max(1, min(limit, 200)))
            )
            return list(rows.all())

    async def pending(self, *, limit: int = 20):
        """仅供可信 worker 发现；调用方须在 claim 前重新加载当前系统身份。"""
        async with self.session_factory() as db:
            rows = await db.scalars(
                select(AgentTaskModel)
                .where(self._claimable(_utcnow()), AgentTaskModel.schema_version == SCHEMA_VERSION)
                .order_by(AgentTaskModel.created_at)
                .limit(limit)
            )
            return list(rows.all())

    @staticmethod
    def _claimable(now):
        return or_(
            AgentTaskModel.status == "queued",
            and_(AgentTaskModel.status == "running", AgentTaskModel.lease_expires_at <= now),
        )

    async def claim(self, task_id: str, owner_id: int, worker_id: str, *, lease_seconds: int = 60):
        now = _utcnow()
        if lease_seconds <= 0 or not worker_id:
            raise ValueError("执行租约无效")
        async with self.session_factory() as db:
            result = await db.scalar(
                update(AgentTaskModel)
                .where(
                    AgentTaskModel.task_id == task_id,
                    AgentTaskModel.owner_id == owner_id,
                    AgentTaskModel.schema_version == SCHEMA_VERSION,
                    self._claimable(now),
                )
                .where(AgentTaskModel.generation < MAX_GENERATIONS)
                .values(
                    status="running",
                    generation=AgentTaskModel.generation + 1,
                    worker_id=worker_id,
                    heartbeat_at=now,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                    updated_at=now,
                )
                .returning(AgentTaskModel)
            )
            await db.commit()
            return result

    @staticmethod
    def _fence(task_id, generation, worker_id, now):
        return (
            AgentTaskModel.task_id == task_id,
            AgentTaskModel.generation == generation,
            AgentTaskModel.worker_id == worker_id,
            AgentTaskModel.status == "running",
            AgentTaskModel.lease_expires_at > now,
            AgentTaskModel.schema_version == SCHEMA_VERSION,
        )

    async def heartbeat(self, task_id: str, generation: int, worker_id: str, *, lease_seconds: int = 60) -> bool:
        if lease_seconds <= 0:
            raise ValueError("执行租约无效")
        now = _utcnow()
        return await self._update(
            self._fence(task_id, generation, worker_id, now),
            heartbeat_at=now,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            updated_at=now,
        )

    async def commit(self, task_id: str, generation: int, worker_id: str, *, status: str = "running", **fields) -> bool:
        if status not in {"running", "waiting_approval", "completed", "failed"}:
            raise ValueError("非法执行状态转换")
        if fields.keys() - {"steps", "budget", "result", "approval", "error"}:
            raise ValueError("不能更改冻结任务字段")
        now = _utcnow()
        fields.update(status=status, updated_at=now)
        if status != "running":
            fields.update(worker_id=None, lease_expires_at=None)
        if status in TERMINAL:
            fields.update(finished_at=now, expires_at=now + timedelta(seconds=self.retention_seconds))
        return await self._update(self._fence(task_id, generation, worker_id, now), **fields)

    async def _update(self, conditions, **fields) -> bool:
        async with self.session_factory() as db:
            result = await db.execute(update(AgentTaskModel).where(*conditions).values(**fields))
            await db.commit()
            return result.rowcount == 1

    async def cancel(self, task_id: str, owner_id: int) -> bool:
        now = _utcnow()
        return await self._update(
            (
                AgentTaskModel.task_id == task_id,
                AgentTaskModel.owner_id == owner_id,
                AgentTaskModel.status.not_in(TERMINAL),
            ),
            status="cancelled",
            generation=AgentTaskModel.generation + 1,
            worker_id=None,
            lease_expires_at=None,
            updated_at=now,
            finished_at=now,
            expires_at=now + timedelta(seconds=self.retention_seconds),
        )

    async def fail_pending(self, task_id: str, owner_id: int, error: str) -> bool:
        """可信 worker 在领取前拒绝恢复，不触碰仍有租约的其他执行。"""
        now = _utcnow()
        return await self._update(
            (
                AgentTaskModel.task_id == task_id,
                AgentTaskModel.owner_id == owner_id,
                self._claimable(now),
            ),
            status="failed",
            error=error,
            generation=AgentTaskModel.generation + 1,
            worker_id=None,
            lease_expires_at=None,
            updated_at=now,
            finished_at=now,
            expires_at=now + timedelta(seconds=self.retention_seconds),
        )

    async def resume(self, task_id: str, owner_id: int, *, approval: dict | None = None) -> bool:
        """仅供服务端校验完审批对象/参数后调用，不接受客户端审批状态直接透传。"""
        task = await self.get(task_id, owner_id)
        if task is None or task.status not in {"waiting_approval", "failed"}:
            return False
        if task.status == "failed" and task.approval and task.approval.get("approval_status") == "pending":
            return False
        fields = {
            "status": "queued",
            "updated_at": _utcnow(),
            "finished_at": None,
            "expires_at": None,
            "error": None,
        }
        if approval is not None:
            fields["approval"] = approval
        return await self._update(
            (
                AgentTaskModel.task_id == task_id,
                AgentTaskModel.owner_id == owner_id,
                AgentTaskModel.status == task.status,
                AgentTaskModel.generation == task.generation,
                AgentTaskModel.schema_version == SCHEMA_VERSION,
            ),
            **fields,
        )

    async def delete_session(self, owner_id: int, session_id: str, *, checkpointer=None) -> int:
        now = _utcnow()
        async with self.session_factory() as db:
            tasks = list(
                (
                    await db.scalars(
                        select(AgentTaskModel).where(
                            AgentTaskModel.owner_id == owner_id, AgentTaskModel.session_id == session_id
                        )
                    )
                ).all()
            )
            deferred = {
                task.task_id: max(task.lease_expires_at or now, now + timedelta(seconds=60))
                for task in tasks
                if task.status == "running"
            }
            deferred.update(
                {
                    task.task_id: task.expires_at
                    for task in tasks
                    if task.error == DELETED_SESSION_REASON and task.expires_at and task.expires_at > now
                }
            )
            # 一次事务取消本次删除快照，阻止清理期间旧 worker 提交；清理失败保留记录便于重试。
            await db.execute(
                update(AgentTaskModel)
                .where(
                    AgentTaskModel.owner_id == owner_id,
                    AgentTaskModel.task_id.in_([task.task_id for task in tasks]),
                    AgentTaskModel.status.not_in(TERMINAL),
                )
                .values(
                    status="cancelled",
                    generation=AgentTaskModel.generation + 1,
                    worker_id=None,
                    lease_expires_at=None,
                    updated_at=now,
                    finished_at=now,
                    expires_at=now + timedelta(seconds=self.retention_seconds),
                )
            )
            if deferred:
                # 保留取消墓碑到旧租约结束，cleanup 会再次清理旧 worker 迟到的 checkpoint。
                await db.execute(
                    update(AgentTaskModel)
                    .where(
                        AgentTaskModel.owner_id == owner_id, AgentTaskModel.task_id.in_(deferred)
                    )
                    .values(error=DELETED_SESSION_REASON, expires_at=max(deferred.values()))
                )
            await db.commit()
        for task in tasks:
            if checkpointer is not None:
                await self._delete_checkpoints(task, checkpointer)
        async with self.session_factory() as db:
            await db.execute(
                delete(AgentTaskModel).where(
                    AgentTaskModel.owner_id == owner_id,
                    AgentTaskModel.task_id.in_([task.task_id for task in tasks if task.task_id not in deferred]),
                )
            )
            await db.commit()
            return len(tasks)

    async def cleanup(self, *, checkpointer=None) -> int:
        async with self.session_factory() as db:
            tasks = list(
                (
                    await db.scalars(
                        select(AgentTaskModel)
                        .where(
                            AgentTaskModel.status.in_(TERMINAL),
                            AgentTaskModel.expires_at <= _utcnow(),
                        )
                        .limit(200)
                    )
                ).all()
            )
        for task in tasks:
            if checkpointer is not None:
                await self._delete_checkpoints(task, checkpointer)
        async with self.session_factory() as db:
            result = await db.execute(
                delete(AgentTaskModel).where(
                    AgentTaskModel.task_id.in_([task.task_id for task in tasks]),
                    AgentTaskModel.status.in_(TERMINAL),
                )
            )
            await db.commit()
            return result.rowcount

    @staticmethod
    async def _delete_checkpoints(task, checkpointer):
        await checkpointer.adelete_thread(task.thread_id)
        for generation in range(1, min(task.generation, MAX_GENERATIONS) + 1):
            await checkpointer.adelete_thread(f"{task.thread_id}-{generation}")
