"""工具注册表。

框架本身**不内置任何业务工具**：业务方通过 ``register_tool`` 接入，声明所需权限、
副作用类型与幂等要求。注册表只做登记与查询，鉴权在网关执行时进行。

MCP 工具由网关在运行时发现后动态登记（``source="mcp"``）。
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from app.config.setting import settings

SideEffect = Literal["read", "write", "external"]


@dataclass(frozen=True)
class ToolSpec:
    """一个可被 Agent 调用的工具。

    - ``required_permissions``：全部满足才放行（``模块:资源:操作`` 三段式）
    - ``any_permissions``：命中任意一个即可（用于「二选一」权限场景）
    - ``side_effect``：非 ``read`` 时必须声明幂等键与审批要求
    - ``scope_keys``：参与任务范围冻结的参数名，调用时与 ``RunContext.resolved_scope`` 合并
    """

    name: str
    tool: Callable
    description: str
    tags: list[str] = field(default_factory=list)
    source: str | None = None
    required_permissions: frozenset[str] = frozenset()
    any_permissions: frozenset[str] = frozenset()
    side_effect: SideEffect = "read"
    idempotent: bool = True
    requires_approval: bool = False
    idempotency_key_arg: str | None = None
    agent_enabled: bool = True
    timeout_seconds: float = 30.0
    scope_keys: frozenset[str] = frozenset()

    def allows(self, principal) -> bool:
        if not principal.allows(self.required_permissions):
            return False
        if self.any_permissions and not any(principal.allows({p}) for p in self.any_permissions):
            return False
        return True


class ToolRegistry:
    """工具登记表；重复名称直接拒绝，避免静默覆盖。"""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if not spec.name or not callable(spec.tool):
            raise ValueError("工具必须有名称且可调用")
        if spec.name in self._specs:
            raise ValueError(f"工具已注册: {spec.name}")
        self._specs[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def all(self) -> dict[str, ToolSpec]:
        return dict(self._specs)

    def names(self) -> set[str]:
        return set(self._specs)

    def agent_tools(self) -> dict[str, ToolSpec]:
        return {name: spec for name, spec in self._specs.items() if spec.agent_enabled}


TOOL_REGISTRY = ToolRegistry()


def register_tool(
    name: str,
    *,
    description: str,
    tags: list[str] | None = None,
    required_permissions: frozenset[str] = frozenset(),
    any_permissions: frozenset[str] = frozenset(),
    side_effect: SideEffect = "read",
    idempotent: bool = True,
    requires_approval: bool = False,
    idempotency_key_arg: str | None = None,
    agent_enabled: bool = True,
    timeout_seconds: float | None = None,
    scope_keys: frozenset[str] = frozenset(),
    registry: ToolRegistry | None = None,
):
    """业务侧注册工具的统一入口（可作装饰器使用）。"""

    def decorator(func: Callable) -> Callable:
        (registry or TOOL_REGISTRY).register(
            ToolSpec(
                name=name,
                tool=func,
                description=description,
                tags=list(tags or []),
                required_permissions=required_permissions,
                any_permissions=any_permissions,
                side_effect=side_effect,
                idempotent=idempotent,
                requires_approval=requires_approval,
                idempotency_key_arg=idempotency_key_arg,
                agent_enabled=agent_enabled,
                timeout_seconds=settings.AI_HARNESS_TOOL_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds,
                scope_keys=scope_keys,
            )
        )
        return func

    return decorator
