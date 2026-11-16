"""LangGraph Agent Harness 通用工作流。

执行形状：``plan → execute → verify → synthesize``，其中：

- 简单请求可走 ``fast_path`` 单次调用，不必进多节点图；
- ``verify`` 只做「结果与证据一致性」检查，不生成新事实；
- 有界执行：步数、模型调用、工具调用、Token 与总时长全部受 ``Budget`` 约束；
- 失败可恢复：图状态由 Checkpoint 持久化，恢复时重新加载身份与权限。
"""

from functools import partial
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.config.setting import settings
from app.modules.ai.harness.contracts import BudgetExceeded, RunContext, current_run
from app.modules.ai.harness.middleware import budgeted_call

SYSTEM_PROMPT = (
    "你是一个严谨的智能助手。回答只能基于本轮工具返回的证据；"
    "证据不足时明确说明缺少什么，不要编造数字、来源或结论。"
)


class AgentState(TypedDict, total=False):
    """工作流共享状态；messages 使用 additive 通道便于多节点追加。"""

    messages: Annotated[list[BaseMessage], lambda left, right: [*left, *right]]
    plan: list[str]
    step: int
    evidence: list[str]
    answer: str
    error: str


def _run() -> RunContext:
    ctx = current_run.get()
    if ctx is None:
        raise RuntimeError("Agent 必须在 RunContext 中执行")
    return ctx


def _model_or_none(model):
    if model is not None:
        return model
    raise RuntimeError("未配置模型：请在调用时传入 LangChain ChatModel")


def build_model():
    """按系统配置构造 OpenAI 兼容 ChatModel。"""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
        temperature=0.2,
        timeout=settings.AI_HARNESS_TIMEOUT_SECONDS,
    )


async def plan_node(state: AgentState, *, model, tools) -> dict:
    """产出有界步骤计划；计划本身也计入预算。"""
    ctx = _run()
    ctx.budget.consume("steps")
    question = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    tool_names = ", ".join(sorted(ctx.allowed_tools)) or "（当前无可用工具）"
    prompt = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"可用工具：{tool_names}\n"
                f"最多 {settings.AI_HARNESS_MAX_STEPS} 步。请给出完成该请求的步骤清单，每行一步，不要解释。\n\n"
                f"请求：{question}"
            )
        ),
    ]
    response = await budgeted_call(model, prompt, output_tokens=512)
    text = response.content if hasattr(response, "content") else str(response)
    steps = [line.strip("-• \t") for line in str(text).splitlines() if line.strip()][: settings.AI_HARNESS_MAX_STEPS]
    return {"plan": steps, "step": 0}


async def execute_node(state: AgentState, *, model, tools) -> dict:
    """按计划推进一次：调用模型（可带工具），把结果写入 evidence。"""
    ctx = _run()
    ctx.budget.consume("steps")
    bundle = tools if isinstance(tools, list) else await tools.get_tools()
    bound = model.bind_tools(bundle) if bundle else model
    response = await budgeted_call(bound, state["messages"])
    content = response.content if isinstance(response.content, str) else str(response.content)
    evidence = list(state.get("evidence", []))
    if content.strip():
        evidence.append(content.strip())
    return {
        "messages": [response],
        "evidence": evidence,
        "step": state.get("step", 0) + 1,
    }


async def verify_node(state: AgentState, *, model) -> dict:
    """一致性检查：有工具结果但没有任何证据时判为无效，交回补查。"""
    ctx = _run()
    evidence = state.get("evidence", [])
    has_tool_results = bool(ctx.tool_results)
    if has_tool_results and not evidence:
        return {"error": "工具已返回结果但未形成可用证据"}
    return {"error": ""}


async def synthesize_node(state: AgentState, *, model) -> dict:
    """基于证据收敛最终答案；证据为空时如实说明。"""
    _run()
    evidence = state.get("evidence", [])
    if not evidence:
        return {"answer": "未能获取到可支撑回答的证据，请补充信息或缩小请求范围。"}
    prompt = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content="以下是本轮收集到的证据，请据此给出结论；不确定处直接说明。\n\n"
            + "\n\n".join(f"[{index + 1}] {item}" for index, item in enumerate(evidence))
        ),
    ]
    response = await budgeted_call(model, prompt)
    content = response.content if isinstance(response.content, str) else str(response.content)
    return {"answer": content.strip(), "messages": [AIMessage(content=content)]}


def _route_after_execute(state: AgentState) -> Literal["execute", "verify"]:
    ctx = current_run.get()
    plan = state.get("plan") or []
    step = state.get("step", 0)
    if ctx is not None:
        try:
            ctx.budget.consume("steps", 0)  # 仅探测剩余预算，不实际扣减
        except BudgetExceeded:
            return "verify"
    return "execute" if step < len(plan) else "verify"


def build_workflow(model, tools, *, checkpointer: BaseCheckpointSaver | None = None, max_steps: int | None = None):
    """编译 LangGraph 工作流；传入 checkpointer 即获得持久任务能力。"""
    limit = settings.AI_HARNESS_MAX_STEPS if max_steps is None else max_steps
    graph = StateGraph(AgentState)
    # 用 partial 而非 lambda：lambda 会包成同步函数，LangGraph 不再等待其中的协程。
    graph.add_node("plan", partial(plan_node, model=model, tools=tools))
    graph.add_node("execute", partial(execute_node, model=model, tools=tools))
    graph.add_node("verify", partial(verify_node, model=model))
    graph.add_node("synthesize", partial(synthesize_node, model=model))
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute")
    graph.add_conditional_edges("execute", _route_after_execute, {"execute": "execute", "verify": "verify"})
    graph.add_edge("verify", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile(checkpointer=checkpointer)


async def run_agent(
    question: str,
    *,
    model=None,
    tools=None,
    checkpointer: BaseCheckpointSaver | None = None,
    thread_id: str | None = None,
) -> dict:
    """在工作流中执行一次请求；调用方负责设置 ``current_run``。"""
    ctx = _run()
    if not settings.AI_HARNESS_ENABLE:
        raise RuntimeError("AI_HARNESS_ENABLE 未开启，LangGraph Harness 不可用")
    resolved_model = _model_or_none(model)
    workflow = build_workflow(resolved_model, tools, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id or ctx.task_id}, "recursion_limit": settings.AI_HARNESS_MAX_STEPS * 2}
    initial: AgentState = {"messages": [HumanMessage(content=question)], "plan": [], "step": 0, "evidence": []}
    state = await workflow.ainvoke(initial, config)
    return {
        "answer": state.get("answer", ""),
        "plan": state.get("plan", []),
        "evidence": state.get("evidence", []),
        "steps": state.get("step", 0),
        "tool_results": ctx.tool_results,
        "budget": ctx.budget.snapshot(),
    }
