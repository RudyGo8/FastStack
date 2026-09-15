"""
@create_time: 2026/4/27 下午3:58
@Author: GeChao
@File: state.py
"""

from typing import TypedDict


# 检索流程状态定义
class RAGState(TypedDict):
    question: str
    query: str
    context: str
    docs: list[dict]
    route: str | None
    expansion_type: str | None
    expanded_query: str | None
    step_back_question: str | None
    step_back_answer: str | None
    hypothetical_doc: str | None
    rag_trace: dict | None
