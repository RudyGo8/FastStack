"""按应用 Token 预算选择完整消息。

这里给出的是**应用输入预算**，不代表任何模型的窗口大小，调用方可显式覆盖。
不截断消息正文、不拆散工具调用组——宁可让调用方缩小请求范围，也不产生孤立 tool 消息。
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages

DEFAULT_CONTEXT_TOKENS = 16000


def _complete_pairs(messages: list) -> list:
    """只保留完整的「AI 工具调用 + 对应 ToolMessage」组。"""
    result = []
    index = 0
    while index < len(messages):
        message = messages[index]
        if isinstance(message, ToolMessage):
            index += 1
            continue
        if isinstance(message, AIMessage) and message.tool_calls:
            end = index + 1
            while end < len(messages) and isinstance(messages[end], ToolMessage):
                end += 1
            expected = {call["id"] for call in message.tool_calls}
            actual = [item.tool_call_id for item in messages[index + 1 : end]]
            if expected == set(actual) and len(expected) == len(actual):
                result.extend(messages[index:end])
            index = end
            continue
        result.append(message)
        index += 1
    return result


def prepare_messages(messages: list, *, max_tokens: int = DEFAULT_CONTEXT_TOKENS) -> list:
    """按预算裁剪为最近上下文；最近一轮用户条件必须完整保留。"""
    if max_tokens <= 0:
        raise ValueError("上下文预算必须为正数")
    if not messages:
        return []
    clean = _complete_pairs(messages)
    recent_user = next((item for item in reversed(clean) if isinstance(item, HumanMessage)), None)
    if recent_user is not None and count_tokens_approximately([recent_user]) > max_tokens:
        raise ValueError("最近用户条件超过上下文预算，请缩小请求范围")
    selected = trim_messages(
        clean,
        max_tokens=max_tokens,
        token_counter=count_tokens_approximately,
        strategy="last",
        start_on="human",
        include_system=True,
        allow_partial=False,
    )
    selected = _complete_pairs(selected)
    # 旧的长 AI 回答应先让位于用户条件，不能让「继续」丢失原始要求。
    first = next((index for index, item in enumerate(clean) if selected and item is selected[0]), len(clean))
    conditions = []
    for item in reversed(clean[:first]):
        if isinstance(item, HumanMessage):
            candidate = [item, *conditions, *selected]
            if count_tokens_approximately(candidate) > max_tokens:
                break
            conditions.insert(0, item)
    selected = [*conditions, *selected]
    if recent_user is not None and not any(item is recent_user for item in selected):
        raise ValueError("最近一轮完整上下文超过预算，请缩小请求范围")
    return selected
