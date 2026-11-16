"""最小可运行 Agent 示例。

演示完整的接入顺序：注册工具 → 构造身份与预算 → 设置执行上下文 → 跑工作流。

运行（需要先配置 OPENAI_API_KEY / OPENAI_MODEL，并开启 AI_HARNESS_ENABLE）：

    uv run python -m app.modules.ai.harness.example
"""

import asyncio
from datetime import datetime

from app.config.setting import settings
from app.modules.ai.harness.contracts import Principal, RunContext, current_run
from app.modules.ai.harness.runtime import build_model, run_agent
from app.modules.ai.harness.tools.gateway import ToolGateway
from app.modules.ai.harness.tools.registry import ToolRegistry, ToolSpec


def now() -> str:
    """返回服务器当前时间（ISO 8601）。只读工具示例。"""
    return datetime.now().isoformat(timespec="seconds")


def build_demo_registry() -> ToolRegistry:
    """构造一个只含示例工具的独立注册表，不污染全局 TOOL_REGISTRY。"""
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="now",
            tool=now,
            description="查询服务器当前时间",
            tags=["示例", "时间"],
            side_effect="read",
        )
    )
    return registry


async def demo(question: str = "现在几点了？") -> dict:
    """跑一轮完整工作流并返回结构化结果。"""
    if not settings.AI_HARNESS_ENABLE:
        raise RuntimeError("请先在 backend/env/.env.dev 设置 AI_HARNESS_ENABLE=True")
    if not settings.OPENAI_API_KEY or not settings.OPENAI_MODEL:
        raise RuntimeError("请先配置 OPENAI_API_KEY 与 OPENAI_MODEL")

    registry = build_demo_registry()
    gateway = ToolGateway(registry, mcp_manager=None)
    principal = Principal(user_id=1, username="demo", permissions=frozenset(), is_superuser=True)
    context = RunContext(principal=principal, allowed_tools=frozenset({"now"}))
    token = current_run.set(context)
    try:
        return await run_agent(question, model=build_model(), tools=gateway)
    finally:
        current_run.reset(token)


if __name__ == "__main__":
    print(asyncio.run(demo()))
