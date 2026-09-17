"""会话上下文准备：滑动窗口截断，控制发给 LLM 的历史长度。

说明：
- 问答场景通常只需要最近几轮上下文，直接截断比 LLM 总结更快（总结需先阻塞调用一次模型）。
- 窗口外的历史仍完整保存在会话存储中，前端随时可回看，仅不参与下次推理。
"""

MAX_HISTORY_MESSAGES = 10  # 保留最近 10 条（约 5 轮对话）


def prepare_messages(messages: list) -> list:
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    return messages[-MAX_HISTORY_MESSAGES:]
