"""Agent Harness 可信执行上下文：身份、预算、工具白名单与执行事件。

设计要点：
- ``Principal`` 只能来自有效登录用户，权限在恢复任务时重新加载，不信任任务快照；
- ``Budget`` 用锁保护并发扣减，模型调用走「预留 → 结算」，未知用量按预留计，不当作零消耗；
- ``RunContext`` 通过 ContextVar 传递，工具网关在真正调用时重新读取，禁止跨请求复用。
"""

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from threading import Lock
from time import monotonic
from typing import Literal
from uuid import uuid4

from app.config.setting import settings

StepError = Literal[
    "transient",
    "invalid_result",
    "missing_data",
    "permission_denied",
    "budget_exceeded",
    "version_conflict",
]


class BudgetExceeded(RuntimeError):
    """任务资源已耗尽，不应继续调用模型或工具。"""


@dataclass(frozen=True)
class Principal:
    """执行身份：来自登录会话，恢复任务时从数据库重新加载。"""

    user_id: int
    username: str
    permissions: frozenset[str] = frozenset()
    is_superuser: bool = False

    def __post_init__(self):
        if self.user_id <= 0 or not self.username:
            raise ValueError("执行身份必须来自有效登录用户")

    def allows(self, permissions) -> bool:
        return self.is_superuser or set(permissions).issubset(self.permissions)

    @classmethod
    def from_auth(cls, auth) -> "Principal":
        return cls(
            user_id=auth.user.id,
            username=auth.user.username,
            permissions=frozenset(auth.permissions),
            is_superuser=auth.user.is_superuser,
        )


@dataclass
class Budget:
    """任务级资源预算；所有扣减经同一把锁，避免并发放行。"""

    max_models: int = 12
    max_tools: int = 24
    max_steps: int = 24
    max_tokens: int = 64000
    max_seconds: float = 180
    used: dict = field(default_factory=lambda: {"models": 0, "tools": 0, "steps": 0, "tokens": 0})
    _lock: Lock = field(default_factory=Lock, repr=False)
    _reservations: dict = field(default_factory=dict, repr=False)
    _started: float = field(default_factory=monotonic, repr=False)

    def consume(self, kind: str, amount: int = 1):
        if amount < 0:
            raise ValueError("预算用量不能为负")
        with self._lock:
            if monotonic() - self._started >= self.max_seconds or self.used[kind] + amount > getattr(self, f"max_{kind}"):
                raise BudgetExceeded("任务预算已耗尽")
            self.used[kind] += amount

    def reserve_tokens(self, amount: int) -> str:
        self.consume("tokens", amount)
        reservation = str(uuid4())
        with self._lock:
            self._reservations[reservation] = amount
        return reservation

    def settle_tokens(self, reservation: str, actual: int):
        if actual < 0:
            raise ValueError("Token 用量无效")
        with self._lock:
            if reservation not in self._reservations:
                raise ValueError("Token 预留不存在或已结算")
            reserved = self._reservations.pop(reservation)
            self.used["tokens"] += actual - reserved
            if self.used["tokens"] > self.max_tokens:
                raise BudgetExceeded("任务 Token 预算已耗尽")

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.used)


@dataclass
class RunContext:
    """一次 Agent 执行的上下文；子 Agent 通过 ``child`` 继承预算与身份。"""

    principal: Principal
    allowed_tools: frozenset[str]
    task_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = "default_session"
    resolved_scope: dict = field(default_factory=dict)
    budget: Budget = field(default_factory=Budget)
    agent_name: str = "main"
    step_id: str = ""
    step_tool: str = ""
    step_arguments: dict | None = None
    depth: int = 0
    evidence: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    events: list = field(default_factory=list)
    skill_instructions: str = ""
    approval_record: dict | None = None
    persist_budget: Callable[[], Awaitable[bool]] | None = None
    emit: Callable[[dict], Awaitable[None]] | None = None

    def child(self, name: str, tools: set[str]) -> "RunContext":
        if self.depth >= settings.AI_HARNESS_MAX_DEPTH:
            raise ValueError("不允许递归委派")
        return replace(
            self,
            allowed_tools=self.allowed_tools.intersection(tools),
            agent_name=name,
            depth=self.depth + 1,
            resolved_scope=dict(self.resolved_scope),
            evidence=[],
            tool_results=[],
            events=[],
        )


current_run: ContextVar[RunContext | None] = ContextVar("ai_harness_run", default=None)


async def persist_reserved_budget():
    """每次外部调用前确认任务执行权仍有效（租约被抢占则以预算耗尽中止）。"""
    context = current_run.get()
    if context is not None and context.persist_budget is not None:
        if not await context.persist_budget():
            raise BudgetExceeded("任务执行权已失效，已拒绝新的外部调用")


def configured_budget() -> Budget:
    return Budget(
        max_models=settings.AI_HARNESS_MAX_MODEL_CALLS,
        max_tools=settings.AI_HARNESS_MAX_TOOL_CALLS,
        max_steps=settings.AI_HARNESS_MAX_STEPS,
        max_tokens=settings.AI_HARNESS_MAX_TOKENS,
        max_seconds=settings.AI_HARNESS_TIMEOUT_SECONDS,
    )


def budget_configuration(budget: Budget) -> dict:
    return {
        **{key: getattr(budget, key) for key in ("max_models", "max_tools", "max_steps", "max_tokens", "max_seconds")},
        "used": budget.snapshot(),
    }
