"""统一工具入口：执行时强制核对服务端上下文。

任何工具调用都要依次通过：白名单 → 权限 → 参数冻结 → 审批（副作用工具）
→ 预算扣减 → 超时控制 → 结果记录。鉴权信息一律来自 ``current_run``，
不来自工具参数或客户端载荷。
"""

import asyncio
import json
from dataclasses import replace

from langchain_core.tools import StructuredTool
from langchain_core.tools import tool as lc_tool

from app.modules.ai.harness.approval import validate_approval
from app.modules.ai.harness.contracts import current_run, persist_reserved_budget
from app.modules.ai.harness.tools.registry import TOOL_REGISTRY, ToolRegistry, ToolSpec
from app.modules.ai.harness.tools.mcp import mcp_client_manager


def freeze_arguments(spec: ToolSpec, arguments: dict, resolved_scope: dict) -> dict:
    """冻结本次调用的参数：合并任务范围，并序列化副本防止调用期被篡改。"""
    frozen = dict(arguments)
    for key in spec.scope_keys:
        if key in resolved_scope and key not in frozen:
            frozen[key] = resolved_scope[key]
    return json.loads(json.dumps(frozen, sort_keys=True, ensure_ascii=False, allow_nan=False))


def _authorize(spec: ToolSpec, arguments: dict):
    ctx = current_run.get()
    if ctx is None:
        return None, None
    if not spec.agent_enabled or spec.name not in ctx.allowed_tools or not spec.allows(ctx.principal):
        raise PermissionError("当前执行身份未获准调用此工具")
    frozen = freeze_arguments(spec, arguments, ctx.resolved_scope)
    if ctx.step_arguments is not None and (spec.name != ctx.step_tool or frozen != ctx.step_arguments):
        raise PermissionError("子任务不能修改当前步骤绑定的工具或参数")
    operation_key = None
    if spec.side_effect != "read" or spec.requires_approval:
        if not (spec.idempotent and spec.idempotency_key_arg and spec.requires_approval):
            raise PermissionError("有副作用的工具必须声明幂等键与审批要求")
        digest = validate_approval(
            ctx.approval_record,
            task_id=ctx.task_id,
            owner_id=ctx.principal.user_id,
            operation=spec.name,
            arguments=frozen,
        )
        operation_key = f"{ctx.task_id}:{digest}"
    arguments.clear()
    arguments.update(frozen)
    ctx.budget.consume("tools")
    return ctx, operation_key


def _record(ctx, spec: ToolSpec, arguments: dict, result):
    if ctx is not None:
        record = {"tool_name": spec.name, "arguments": dict(arguments), "result": result}
        if ctx.step_id:
            record.update(step_id=ctx.step_id, agent_name=ctx.agent_name)
        ctx.tool_results.append(record)
    return result


def _as_lc_tool(spec: ToolSpec):
    """统一成 LangChain 工具：普通函数就地包装，已包装的保持一致。

    注册表允许直接登记普通可调用对象，网关负责补上 schema，
    避免要求业务方额外依赖 LangChain 的装饰器。
    """
    base = spec.tool
    if hasattr(base, "args_schema") and hasattr(base, "ainvoke"):
        return base
    return lc_tool(spec.name, description=spec.description)(base)


def _guarded_tool(spec: ToolSpec) -> StructuredTool:
    base = _as_lc_tool(spec)

    def invoke(**kwargs):
        ctx, operation_key = _authorize(spec, kwargs)
        call_kwargs = {**kwargs, spec.idempotency_key_arg: operation_key} if operation_key and spec.idempotency_key_arg else kwargs
        if operation_key and getattr(base, "func", None) is not None:
            raw = base.func(**call_kwargs)
        else:
            raw = base.invoke(call_kwargs)
        return _record(ctx, spec, kwargs, raw)

    async def ainvoke(**kwargs):
        ctx, operation_key = _authorize(spec, kwargs)
        await persist_reserved_budget()
        call_kwargs = {**kwargs, spec.idempotency_key_arg: operation_key} if operation_key and spec.idempotency_key_arg else kwargs
        # 同步业务工具复用既有受限线程；取消时等待在途查询释放容量。
        async with asyncio.timeout(spec.timeout_seconds):
            if operation_key and getattr(base, "coroutine", None) is not None:
                raw = await base.coroutine(**call_kwargs)
            else:
                raw = await base.ainvoke(call_kwargs)
        return _record(ctx, spec, kwargs, raw)

    return StructuredTool.from_function(
        func=invoke,
        coroutine=ainvoke,
        name=spec.name,
        description=spec.description,
        args_schema=base.args_schema,
    )


class ToolGateway:
    """本地工具 + MCP 工具的统一出口。"""

    def __init__(self, registry: ToolRegistry | None = None, mcp_manager=None):
        self._registry = registry or TOOL_REGISTRY
        self._mcp = mcp_manager

    async def get_tools(self, allowed_local: set[str] | None = None, include_mcp: bool = True):
        local = [
            _guarded_tool(spec)
            for name, spec in self._registry.all().items()
            if spec.source != "mcp" and (allowed_local is None or name in allowed_local)
        ]
        if self._mcp is None or not include_mcp:
            return local
        mcp = await self._mcp.get_agent_tools()
        ctx = current_run.get()
        if ctx is None:
            # 兼容无 HTTP 执行身份的内部集成；包装仍在真正调用时重新读上下文。
            return local + [self._wrap_mcp(tool) for tool in mcp]
        return local + [
            self._wrap_mcp(tool)
            for tool in mcp
            if tool.name in ctx.allowed_tools
        ]

    def _wrap_mcp(self, tool):
        spec = self._registry.get(tool.name)
        if spec is not None and spec.source == "mcp":
            return _guarded_tool(replace(spec, tool=tool))
        # 未登记工具即使被内部调用发现，进入 HTTP 上下文后仍受白名单约束。
        spec = ToolSpec(
            name=tool.name,
            tool=tool,
            description=tool.description,
            source="mcp",
            side_effect="external",
        )
        return _guarded_tool(spec)

    async def get_mcp_tool_names(self) -> set[str]:
        if self._mcp is None:
            return set()
        tools = await self._mcp.get_agent_tools()
        return {getattr(t, "name", "").strip() for t in tools if getattr(t, "name", None)}


tool_gateway = ToolGateway(TOOL_REGISTRY, mcp_client_manager)
