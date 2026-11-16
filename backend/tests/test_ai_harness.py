"""Agent Harness 单元测试：预算、权限、参数冻结、工具网关越权、工作流执行。

这些用例不依赖数据库与真实模型：Checkpoint 与持久任务的集成验证在
PostgreSQL 实例上单独执行（见 SKILL.md「Agent Harness」一节）。
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.modules.ai.harness.approval import parameters_digest, validate_approval
from app.modules.ai.harness.contracts import (
    Budget,
    BudgetExceeded,
    Principal,
    RunContext,
    current_run,
)
from app.modules.ai.harness.runtime import build_workflow
from app.modules.ai.harness.tools.gateway import ToolGateway, freeze_arguments
from app.modules.ai.harness.tools.registry import ToolRegistry, ToolSpec


def _principal(**kwargs) -> Principal:
    return Principal(**{"user_id": 1, "username": "tester", "permissions": frozenset(), "is_superuser": False, **kwargs})


# ─────────────────────────── 预算 ───────────────────────────


def test_budget_rejects_over_limit():
    budget = Budget(max_tools=1)
    budget.consume("tools")
    with pytest.raises(BudgetExceeded):
        budget.consume("tools")


def test_budget_rejects_negative_amount():
    with pytest.raises(ValueError):
        Budget().consume("tools", -1)


def test_budget_timeout_blocks_further_calls():
    budget = Budget(max_seconds=0)
    with pytest.raises(BudgetExceeded):
        budget.consume("models")


def test_budget_token_reservation_settles_delta():
    budget = Budget(max_tokens=1000)
    reservation = budget.reserve_tokens(100)
    budget.settle_tokens(reservation, 60)
    assert budget.snapshot()["tokens"] == 60


def test_budget_settle_twice_rejected():
    budget = Budget(max_tokens=1000)
    reservation = budget.reserve_tokens(100)
    budget.settle_tokens(reservation, 60)
    with pytest.raises(ValueError):
        budget.settle_tokens(reservation, 10)


# ─────────────────────────── 身份 ───────────────────────────


def test_principal_requires_valid_user():
    with pytest.raises(ValueError):
        Principal(user_id=0, username="tester")


def test_principal_superuser_allows_everything():
    assert _principal(is_superuser=True).allows({"a:b:c"})


def test_principal_requires_all_permissions():
    principal = _principal(permissions=frozenset({"a:b:c"}))
    assert principal.allows({"a:b:c"})
    assert not principal.allows({"a:b:c", "x:y:z"})


# ─────────────────────── 工具规格与权限 ───────────────────────


def _spec(**kwargs) -> ToolSpec:
    async def tool() -> str:
        return "ok"

    return ToolSpec(
        name=kwargs.pop("name", "demo"),
        tool=kwargs.pop("tool", tool),
        description="demo tool",
        **kwargs,
    )


def test_toolspec_requires_all_required_permissions():
    spec = _spec(required_permissions=frozenset({"m:r:q"}))
    assert spec.allows(_principal(permissions=frozenset({"m:r:q"})))
    assert not spec.allows(_principal())


def test_toolspec_any_permissions_grants_on_one_match():
    spec = _spec(any_permissions=frozenset({"a:b:c", "x:y:z"}))
    assert spec.allows(_principal(permissions=frozenset({"x:y:z"})))
    assert not spec.allows(_principal(permissions=frozenset({"other"})))


def test_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    registry.register(_spec(name="dup"))
    with pytest.raises(ValueError):
        registry.register(_spec(name="dup"))


# ─────────────────────────── 参数冻结 ───────────────────────────


def test_freeze_arguments_merges_scope_and_is_detached():
    spec = _spec(scope_keys=frozenset({"tenant"}))
    arguments = {"query": "x"}
    frozen = freeze_arguments(spec, arguments, {"tenant": "t1"})
    assert frozen == {"query": "x", "tenant": "t1"}
    arguments["query"] = "tampered"
    assert frozen["query"] == "x"


def test_freeze_arguments_keeps_explicit_value():
    spec = _spec(scope_keys=frozenset({"tenant"}))
    assert freeze_arguments(spec, {"tenant": "explicit"}, {"tenant": "scope"})["tenant"] == "explicit"


# ─────────────────────────── 工具网关 ───────────────────────────


class _Ctx:
    def __init__(self, **kwargs):
        self.token = None
        self.ctx = kwargs.pop("ctx", None)

    def __enter__(self):
        self.token = current_run.set(self.ctx)
        return self.ctx

    def __exit__(self, *exc):
        current_run.reset(self.token)


def _run_gateway(gateway, name, **kwargs):
    """在 RunContext 下走异步路径调用网关工具（与 LangGraph 实际执行一致）。"""

    async def call():
        tools = await gateway.get_tools()
        tool = next(item for item in tools if item.name == name)
        return await tool.ainvoke(kwargs)

    return asyncio.run(call())


def test_gateway_denies_tool_outside_allowlist():
    registry = ToolRegistry()
    registry.register(_spec(name="hidden"))
    ctx = RunContext(principal=_principal(is_superuser=True), allowed_tools=frozenset())
    with _Ctx(ctx=ctx):
        with pytest.raises(PermissionError):
            _run_gateway(ToolGateway(registry), "hidden")


def test_gateway_denies_when_principal_lacks_permission():
    registry = ToolRegistry()
    registry.register(_spec(name="needs_perm", required_permissions=frozenset({"m:r:q"})))
    ctx = RunContext(principal=_principal(), allowed_tools=frozenset({"needs_perm"}))
    with _Ctx(ctx=ctx):
        with pytest.raises(PermissionError):
            _run_gateway(ToolGateway(registry), "needs_perm")


def test_gateway_executes_and_records_result():
    registry = ToolRegistry()

    async def echo(value: str = "") -> str:
        return f"echo:{value}"

    registry.register(_spec(name="echo", tool=echo))
    ctx = RunContext(principal=_principal(is_superuser=True), allowed_tools=frozenset({"echo"}))
    with _Ctx(ctx=ctx):
        result = _run_gateway(ToolGateway(registry), "echo", value="1")
    assert result == "echo:1"
    assert ctx.tool_results and ctx.tool_results[0]["tool_name"] == "echo"
    assert ctx.budget.snapshot()["tools"] == 1


def test_gateway_enforces_tool_timeout():
    registry = ToolRegistry()

    async def slow() -> str:
        await asyncio.sleep(1)
        return "late"

    registry.register(_spec(name="slow", tool=slow, timeout_seconds=0.01))
    ctx = RunContext(principal=_principal(is_superuser=True), allowed_tools=frozenset({"slow"}))
    gateway = ToolGateway(registry)

    async def call():
        tools = await gateway.get_tools()
        tool = next(item for item in tools if item.name == "slow")
        await tool.ainvoke({})

    with _Ctx(ctx=ctx):
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(call())


# ─────────────────────────── 审批 ───────────────────────────


def _approved_record(**overrides) -> dict:
    record = {
        "approval_status": "approved",
        "task_id": "t1",
        "user_id": 1,
        "operation": "op",
        "parameters_digest": parameters_digest("op", {"a": 1}),
        "approver": "admin",
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }
    record.update(overrides)
    return record


def test_approval_accepts_matching_record():
    validate_approval(_approved_record(), task_id="t1", owner_id=1, operation="op", arguments={"a": 1})


@pytest.mark.parametrize(
    "override",
    [
        {"approval_status": "pending"},
        {"task_id": "other"},
        {"parameters_digest": parameters_digest("op", {"a": 2})},
        {"approver": ""},
        {"expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    ],
)
def test_approval_rejects_mismatch(override):
    with pytest.raises(PermissionError):
        validate_approval(
            _approved_record(**override), task_id="t1", owner_id=1, operation="op", arguments={"a": 1}
        )


# ─────────────────────────── 工作流 ───────────────────────────


class _FakeModel:
    """最小 ChatModel 替身：覆盖 budgeted_call 用到的 bind / ainvoke。"""

    def bind(self, **kwargs):
        return self

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages, **kwargs):
        latest = str(messages[-1].content)
        return AIMessage(content="步骤一\n步骤二" if "步骤清单" in latest else "最终结论")


def _run_workflow(budget: Budget | None = None) -> tuple[dict, RunContext]:
    ctx = RunContext(
        principal=_principal(is_superuser=True),
        allowed_tools=frozenset(),
        budget=budget or Budget(),
    )
    workflow = build_workflow(_FakeModel(), tools=[])
    token = current_run.set(ctx)
    try:
        state = asyncio.run(
            workflow.ainvoke(
                {"messages": [HumanMessage(content="请处理")], "plan": [], "step": 0, "evidence": []}
            )
        )
    finally:
        current_run.reset(token)
    return state, ctx


def test_workflow_produces_plan_and_answer():
    state, ctx = _run_workflow()
    assert state["plan"] == ["步骤一", "步骤二"]
    assert state["answer"]
    assert ctx.budget.snapshot()["models"] >= 1


def test_workflow_stops_when_budget_exhausted():
    with pytest.raises(BudgetExceeded):
        _run_workflow(Budget(max_models=1))


def test_workflow_reports_missing_evidence():
    ctx = RunContext(principal=_principal(is_superuser=True), allowed_tools=frozenset(), budget=Budget())
    ctx.tool_results.append({"tool_name": "demo", "arguments": {}, "result": "x"})
    token = current_run.set(ctx)
    try:
        workflow = build_workflow(_FakeModel(), tools=[])
        state = asyncio.run(
            workflow.ainvoke(
                {"messages": [HumanMessage(content="请处理")], "plan": [], "step": 0, "evidence": []}
            )
        )
    finally:
        current_run.reset(token)
    # 工具已有结果时 evidence 不得为空，verify 会给出显式错误标记
    assert state.get("evidence")
