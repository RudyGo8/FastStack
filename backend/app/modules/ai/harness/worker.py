"""持久任务执行器。

职责边界：
- 领取任务前**重新加载身份与权限**，不信任任务里的 principal 快照；
- 每次外部调用前通过 ``persist_budget`` 续租，租约丢失立即中止；
- 结果只经 ``TaskStore.commit`` 回写，代次不匹配即视为被抢占。
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.config.setting import settings
from app.core.logger import logger
from app.modules.ai.harness.checkpoint import open_checkpointer
from app.modules.ai.harness.contracts import Budget, Principal, RunContext, current_run
from app.modules.ai.harness.policy import load_principal
from app.modules.ai.harness.runtime import run_agent
from app.modules.ai.harness.tasks import MAX_GENERATIONS, TaskStore

LEASE_SECONDS = 60


class LeaseLost(RuntimeError):
    """租约已失效：本 worker 不应再写入任何结果。"""


def _budget_from_snapshot(snapshot: dict) -> Budget:
    budget = Budget(
        max_models=int(snapshot.get("max_models", settings.AI_HARNESS_MAX_MODEL_CALLS)),
        max_tools=int(snapshot.get("max_tools", settings.AI_HARNESS_MAX_TOOL_CALLS)),
        max_steps=int(snapshot.get("max_steps", settings.AI_HARNESS_MAX_STEPS)),
        max_tokens=int(snapshot.get("max_tokens", settings.AI_HARNESS_MAX_TOKENS)),
        max_seconds=float(snapshot.get("max_seconds", settings.AI_HARNESS_TIMEOUT_SECONDS)),
    )
    used = snapshot.get("used") or {}
    for kind, value in used.items():
        if kind in budget.used and isinstance(value, int) and value >= 0:
            budget.used[kind] = value
    return budget


async def execute_task(
    candidate,
    *,
    store: TaskStore | None = None,
    model=None,
    checkpointer=None,
    worker_id: str | None = None,
) -> dict:
    """领取并执行一个任务；返回执行结果摘要。"""
    store = store or TaskStore()
    worker_id = worker_id or f"worker-{uuid4()}"
    if settings.DATABASE_TYPE != "postgres":
        raise RuntimeError("持久任务仅支持 PostgreSQL")

    task = await store.claim(candidate.task_id, candidate.owner_id, worker_id, lease_seconds=LEASE_SECONDS)
    if task is None:
        return {"task_id": candidate.task_id, "status": "skipped"}

    generation = task.generation
    if generation > MAX_GENERATIONS:
        await store.commit(task.task_id, generation, worker_id, status="failed", error="执行代次超限")
        return {"task_id": task.task_id, "status": "failed"}

    async def _renew() -> bool:
        return await store.heartbeat(task.task_id, generation, worker_id, lease_seconds=LEASE_SECONDS)

    try:
        # 恢复任务一律重新鉴权，任务里的权限快照只作审计用。
        principal: Principal = await load_principal(task.owner_id)
        budget = _budget_from_snapshot(task.budget or {})
        ctx = RunContext(
            principal=principal,
            allowed_tools=frozenset(),
            task_id=task.task_id,
            session_id=task.session_id,
            resolved_scope=dict(task.resolved_scope or {}),
            budget=budget,
            persist_budget=_renew,
        )
        token = current_run.set(ctx)
        try:
            result = await run_agent(
                task.prompt,
                model=model,
                tools=None,
                checkpointer=checkpointer,
                thread_id=f"{task.thread_id}-{generation}",
            )
        finally:
            current_run.reset(token)

        ok = await store.commit(
            task.task_id,
            generation,
            worker_id,
            status="completed",
            result=result,
            budget={**ctx.budget.snapshot(), "max_seconds": ctx.budget.max_seconds},
            steps=[],
        )
        if not ok:
            raise LeaseLost("租约已失效，结果未写入")
        return {"task_id": task.task_id, "status": "completed", "answer": result.get("answer", "")}
    except Exception as exc:
        logger.warning(f"Agent 任务执行失败 task={task.task_id} 错误类型={type(exc).__name__}")
        await store.commit(
            task.task_id,
            generation,
            worker_id,
            status="failed",
            error=f"{type(exc).__name__}: {exc}"[:500],
        )
        return {"task_id": task.task_id, "status": "failed", "error": type(exc).__name__}


async def run_worker_loop(stop_event: asyncio.Event | None = None, *, store: TaskStore | None = None, interval: float = 2.0):
    """常驻 worker：持续领取可执行任务，直到 stop_event 置位。"""
    store = store or TaskStore()
    stop_event = stop_event or asyncio.Event()
    if not settings.AI_HARNESS_ENABLE:
        logger.info("AI_HARNESS_ENABLE 未开启，worker 不启动")
        return
    while not stop_event.is_set():
        try:
            async with open_checkpointer() as checkpointer:
                for candidate in await store.pending(limit=5):
                    if stop_event.is_set():
                        break
                    await execute_task(candidate, store=store, checkpointer=checkpointer)
        except Exception as exc:
            logger.warning(f"Agent worker 轮询失败 错误类型={type(exc).__name__}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


def next_expiry(seconds: int = 60) -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=seconds)
