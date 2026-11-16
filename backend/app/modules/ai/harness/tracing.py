"""执行链路追踪：模型用量归一、MCP 调用汇总。

RAG 追踪属于按需能力，由调用方通过 ``rag_trace`` 参数注入，本模块不反向依赖 RAG。
"""

from contextvars import ContextVar

from app.config.setting import settings

_mcp_calls: ContextVar[list[dict]] = ContextVar("ai_harness_mcp_calls", default=None)


def record_mcp_call(call: dict) -> None:
    """记录一次 MCP 调用，供本轮执行结束时汇总。"""
    calls = _mcp_calls.get()
    if calls is None:
        calls = []
        _mcp_calls.set(calls)
    calls.append(call)


def take_mcp_calls() -> list[dict]:
    """取出并清空本轮 MCP 调用记录。"""
    calls = _mcp_calls.get() or []
    _mcp_calls.set(None)
    return calls


def _normalize_usage(usage: dict | None) -> dict | None:
    if not isinstance(usage, dict):
        return None
    in_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0
    out_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
    total_tokens = usage.get("total_tokens", 0) or (in_tokens + out_tokens)
    return {
        "input_tokens": int(in_tokens),
        "output_tokens": int(out_tokens),
        "total_tokens": int(total_tokens),
    }


def extract_usage_from_message(msg) -> dict | None:
    """从 LangChain 消息中提取 token 用量；两种来源都缺失时返回 None。"""
    if msg is None:
        return None
    normalized = _normalize_usage(getattr(msg, "usage_metadata", None))
    if normalized:
        return normalized
    response_meta = getattr(msg, "response_metadata", None) or {}
    if isinstance(response_meta, dict):
        normalized = _normalize_usage(response_meta.get("token_usage"))
        if normalized:
            return normalized
    return None


def _build_mcp_summary(mcp_calls: list[dict] | None) -> dict:
    calls = mcp_calls or []
    total = len(calls)
    success = sum(1 for item in calls if isinstance(item, dict) and item.get("success") is True)
    sources = sorted(
        {str(item.get("server_name")).strip() for item in calls if isinstance(item, dict) and item.get("server_name")}
    )
    return {"total": total, "success": success, "failed": max(0, total - success), "sources": sources}


def collect_trace(usage: dict | None, *, mcp_calls: list[dict] | None = None, rag_trace: dict | None = None) -> dict:
    """汇总一次执行的追踪信息（模型用量 / MCP 调用 / 可选的 RAG 追踪）。"""
    trace = dict(rag_trace or {})
    trace["token_usage"] = {"model": settings.OPENAI_MODEL, "usage": usage}
    trace["mcp_calls"] = mcp_calls or []
    trace["mcp_summary"] = _build_mcp_summary(mcp_calls)
    trace["mcp_used"] = bool(mcp_calls)
    return trace
