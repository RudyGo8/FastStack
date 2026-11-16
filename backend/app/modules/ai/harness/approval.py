"""高风险工具的人工审批（LangGraph interrupt）。

审批记录必须由服务端从数据库载入后校验；恢复载荷本身不授予任何权限。
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


def parameters_digest(operation: str, arguments: dict) -> str:
    """对「工具名 + 冻结参数」取摘要，保证审批对象与执行对象逐字节一致。"""
    payload = json.dumps(
        {"operation": operation, "arguments": arguments},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class ApprovalState(TypedDict, total=False):
    task_id: str
    owner_id: int
    operation: str
    arguments: dict
    result: str


def validate_approval(record, *, task_id, owner_id, operation, arguments):
    """校验服务端审批记录：状态、对象、参数摘要与有效期缺一不可。"""
    if not record or record.get("approval_status") != "approved":
        raise PermissionError("操作尚未获得服务端审批")
    digest = parameters_digest(operation, arguments)
    if (
        record.get("task_id") != task_id
        or record.get("user_id") != owner_id
        or record.get("operation") != operation
        or record.get("parameters_digest") != digest
        or not record.get("approver")
    ):
        raise PermissionError("审批对象或操作参数不匹配")
    expires = datetime.fromisoformat(record["expires_at"])
    if expires.tzinfo is None or expires <= datetime.now(UTC):
        raise PermissionError("审批已过期")
    return digest


def build_approval_workflow(execute, checkpointer, *, approval_lookup=None):
    """构建「中断 → 审批校验 → 执行」图。

    ``execute`` 必须接受并实际实施幂等键；本函数不声称外部操作 exactly-once。
    """

    async def approval_node(state):
        digest = parameters_digest(state["operation"], state["arguments"])
        interrupt(
            {
                "task_id": state["task_id"],
                "operation": state["operation"],
                "parameters_digest": digest,
            }
        )
        record = await approval_lookup(state["task_id"]) if approval_lookup else None
        validate_approval(
            record,
            task_id=state["task_id"],
            owner_id=state["owner_id"],
            operation=state["operation"],
            arguments=state["arguments"],
        )
        key = f"{state['task_id']}:{digest}"
        return {"result": await execute(state["arguments"], key)}

    graph = StateGraph(ApprovalState)
    graph.add_node("approval", approval_node)
    graph.add_edge(START, "approval")
    graph.add_edge("approval", END)
    return graph.compile(checkpointer=checkpointer)
