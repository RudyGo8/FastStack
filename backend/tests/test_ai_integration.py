"""Agent Harness 集成测试（需要真实 PostgreSQL + pgvector）。

默认跳过；显式开启后才会连接数据库：

    AI_INTEGRATION_PG=1 \
    DATABASE_HOST=127.0.0.1 DATABASE_PORT=5434 \
    DATABASE_USER=postgres DATABASE_PASSWORD=123456 DATABASE_NAME=faststack \
    uv run pytest tests/test_ai_integration.py -q

覆盖：Checkpoint schema 初始化 → 工作流落盘 → 同线程恢复 → 任务队列租约与抢占。
"""

import asyncio
import os
import uuid

import pytest
from langchain_core.messages import AIMessage, HumanMessage

pytestmark = pytest.mark.skipif(
    os.getenv("AI_INTEGRATION_PG") != "1",
    reason="集成测试需要真实 PostgreSQL：设置 AI_INTEGRATION_PG=1 后运行",
)


class _FakeModel:
    def bind(self, **kwargs):
        return self

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages, **kwargs):
        latest = str(messages[-1].content)
        return AIMessage(content="步骤一\n步骤二" if "步骤清单" in latest else "最终结论")


def _context():
    from app.modules.ai.harness.contracts import Principal, RunContext

    return RunContext(
        principal=Principal(user_id=1, username="integration", permissions=frozenset(), is_superuser=True),
        allowed_tools=frozenset(),
    )


def test_checkpoint_schema_initializes_and_persists_thread():
    from app.modules.ai.harness.checkpoint import initialize_checkpoint_schema, open_checkpointer
    from app.modules.ai.harness.contracts import current_run
    from app.modules.ai.harness.runtime import build_workflow

    thread_id = f"it-{uuid.uuid4()}"

    async def run():
        await initialize_checkpoint_schema()
        async with open_checkpointer() as saver:
            workflow = build_workflow(_FakeModel(), tools=[], checkpointer=saver)
            ctx = _context()
            token = current_run.set(ctx)
            try:
                state = await workflow.ainvoke(
                    {"messages": [HumanMessage(content="请处理")], "plan": [], "step": 0, "evidence": []},
                    {"configurable": {"thread_id": thread_id}},
                )
            finally:
                current_run.reset(token)
            # 同一线程可再次读取到已落盘的状态
            snapshot = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
            return state, snapshot

    state, snapshot = asyncio.run(run())
    assert state["answer"]
    assert snapshot is not None, "Checkpoint 未落盘"


def test_task_store_lease_and_fencing():
    """同一任务不能被两个 worker 同时持有；旧代次提交必须失败。"""
    from app.modules.ai.harness.contracts import Principal
    from app.modules.ai.harness.tasks import TaskStore

    store = TaskStore()
    principal = Principal(user_id=1, username="integration", permissions=frozenset(), is_superuser=True)
    session_id = f"it-{uuid.uuid4()}"

    async def run():
        task = await store.create(principal, session_id, f"req-{uuid.uuid4()}", "集成测试任务", {})
        first = await store.claim(task.task_id, principal.user_id, "worker-a", lease_seconds=30)
        second = await store.claim(task.task_id, principal.user_id, "worker-b", lease_seconds=30)
        heartbeat = await store.heartbeat(task.task_id, first.generation, "worker-a", lease_seconds=30)
        stale = await store.commit(task.task_id, first.generation, "worker-b", status="completed", result={})
        await store.cancel(task.task_id, principal.user_id)
        return first, second, heartbeat, stale

    first, second, heartbeat, stale = asyncio.run(run())
    assert first is not None, "首个 worker 应领取成功"
    assert second is None, "第二个 worker 不应重复领取"
    assert heartbeat is True, "持锁 worker 应能续租"
    assert stale is False, "非持锁 worker 的提交必须被拒绝"
