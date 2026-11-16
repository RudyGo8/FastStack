"""LangGraph Agent Harness（通用执行框架，不依赖任何业务模块）。

分层：

- ``contracts``：RunContext / Principal / Budget / 执行事件
- ``policy``：任务恢复时的身份重载与权限重算
- ``approval``：高风险操作的人工审批（LangGraph interrupt）
- ``checkpoint``：LangGraph PostgreSQL Checkpoint 生命周期
- ``middleware`` / ``context``：模型调用预算与上下文裁剪
- ``runtime``：Plan → Execute → Verify → Synthesize 工作流
- ``tasks`` / ``worker``：持久任务队列与执行器
- ``tools``：工具注册表与统一网关（含 MCP 适配）
"""

from app.modules.ai.harness.contracts import (
    Budget,
    BudgetExceeded,
    Principal,
    RunContext,
    current_run,
    persist_reserved_budget,
)
from app.modules.ai.harness.runtime import build_model, build_workflow, run_agent
from app.modules.ai.harness.tasks import TaskStore

__all__ = [
    "Budget",
    "BudgetExceeded",
    "Principal",
    "RunContext",
    "current_run",
    "persist_reserved_budget",
    "build_model",
    "build_workflow",
    "run_agent",
    "TaskStore",
]
