"""原生 Agent Middleware：所有模型调用共享同一份任务预算。

预算参数由配置或工厂传入，不推测模型窗口大小；Token 走「预留 → 结算」，
拿不到可靠用量时保留全部预留，不把未知消耗当零。
"""

import asyncio
import json
from time import monotonic

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.utils.function_calling import convert_to_openai_tool

from app.config.setting import settings
from app.modules.ai.harness.context import prepare_messages
from app.modules.ai.harness.contracts import BudgetExceeded, current_run, persist_reserved_budget


def _reserve(messages, output_tokens, timeout_seconds, *, tools=None):
    if output_tokens <= 0 or timeout_seconds <= 0:
        raise ValueError("模型输出和超时预算必须为正数")
    run = current_run.get()
    if run is None:
        return None, None, timeout_seconds
    budget = run.budget
    budget.consume("models")
    reservation = budget.reserve_tokens(count_tokens_approximately(messages, tools=tools) + output_tokens)
    remaining = budget.max_seconds - (monotonic() - budget._started)
    if remaining <= 0:
        raise BudgetExceeded("任务执行时间已耗尽")
    return budget, reservation, min(timeout_seconds, remaining)


def _settle(budget, reservation, result):
    if budget is None:
        return
    usage = getattr(result, "usage_metadata", None) or (getattr(result, "response_metadata", None) or {}).get("token_usage")
    if usage and isinstance(usage.get("total_tokens"), int) and usage["total_tokens"] >= 0:
        budget.settle_tokens(reservation, usage["total_tokens"])
    # 没有可靠用量或调用失败时保留全部预留，不把未知消耗当零。


async def budgeted_call(
    model,
    messages,
    *,
    schema=None,
    output_tokens: int | None = None,
    timeout_seconds: float | None = None,
    context_tokens: int | None = None,
):
    """辅助调用（规划/摘要/分类）；与主模型、子任务共用 current_run 预算。"""
    output_tokens = settings.AI_HARNESS_OUTPUT_TOKENS if output_tokens is None else output_tokens
    timeout_seconds = settings.AI_HARNESS_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    context_tokens = settings.AI_HARNESS_CONTEXT_TOKENS if context_tokens is None else context_tokens
    messages = list(messages)
    tools = [convert_to_openai_tool(schema)] if schema is not None else None
    if count_tokens_approximately(messages, tools=tools) > context_tokens:
        raise BudgetExceeded("辅助模型输入超过上下文预算")
    budget, reservation, timeout = _reserve(messages, output_tokens, timeout_seconds, tools=tools)
    await persist_reserved_budget()
    configured = model.bind(max_tokens=output_tokens) if hasattr(model, "bind") else model
    if schema is not None:
        configured = model.with_structured_output(schema, method="function_calling", include_raw=True, max_tokens=output_tokens)
    async with asyncio.timeout(timeout):
        result = await configured.ainvoke(messages, **({} if hasattr(configured, "bind") else {"max_tokens": output_tokens}))
    if schema is not None:
        _settle(budget, reservation, result.get("raw"))
        if result.get("parsing_error"):
            raise result["parsing_error"]
        if result.get("parsed") is None:
            raise ValueError("结构化模型未返回有效结果")
        return result["parsed"]
    _settle(budget, reservation, result)
    return result


def _project_tool(message, max_tokens):
    """把超长工具结果投影为带截断标记的预览，原始结果仍保存在 tool_results。"""
    if not isinstance(message, ToolMessage) or count_tokens_approximately([message]) <= max_tokens:
        return message
    text = message.content if isinstance(message.content, str) else json.dumps(message.content, ensure_ascii=False)
    preview = text[: max_tokens * 2]
    while True:
        content = json.dumps(
            {
                "truncated": True,
                "notice": "工具原始结果已保留；此处仅为预览，不能据此声称结果完整。",
                "content_preview": preview,
            },
            ensure_ascii=False,
        )
        projected = message.model_copy(update={"content": content})
        if count_tokens_approximately([projected]) <= max_tokens:
            return projected
        if not preview:
            raise BudgetExceeded("工具输出投影预算不足")
        preview = preview[: len(preview) // 2]


class HarnessMiddleware(AgentMiddleware):
    """应用预算参数由配置/工厂传入，不推测模型窗口大小。"""

    def __init__(
        self,
        *,
        context_tokens: int | None = None,
        output_tokens: int | None = None,
        timeout_seconds: float | None = None,
        tool_output_tokens: int = 2048,
    ):
        self.context_tokens = settings.AI_HARNESS_CONTEXT_TOKENS if context_tokens is None else context_tokens
        self.output_tokens = settings.AI_HARNESS_OUTPUT_TOKENS if output_tokens is None else output_tokens
        self.timeout_seconds = settings.AI_HARNESS_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        self.tool_output_tokens = tool_output_tokens

    async def awrap_model_call(self, request, handler):
        messages = [_project_tool(message, self.tool_output_tokens) for message in request.messages]
        system = [request.system_message] if isinstance(request.system_message, SystemMessage) else []
        overhead = count_tokens_approximately(system, tools=request.tools)
        messages = prepare_messages(messages, max_tokens=self.context_tokens - overhead)
        model_settings = {
            **request.model_settings,
            "max_tokens": min(self.output_tokens, request.model_settings.get("max_tokens", self.output_tokens)),
        }
        budget, reservation, timeout = _reserve(
            [*system, *messages], model_settings["max_tokens"], self.timeout_seconds, tools=request.tools
        )
        await persist_reserved_budget()
        async with asyncio.timeout(timeout):
            response = await handler(request.override(messages=messages, model_settings=model_settings))
        if response.result:
            _settle(budget, reservation, response.result[-1])
        return response
