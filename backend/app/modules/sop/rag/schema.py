"""
@create_time: 2026/4/27 下午3:58
@Author: GeChao
@File: schema.py
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class GradeDocuments(BaseModel):
    """相关性评估输出结构"""

    binary_score: str = Field(description="Relevance score: 'yes' if relevant, or 'no' if not relevant")


class RewriteStrategy(BaseModel):
    """查询重写策略输出结构"""

    strategy: Literal["step_back", "hyde", "complex"]


class RetrieveResult(BaseModel):
    """检索结果结构，后面拆 pipeline 时用"""

    docs: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}


class ExpansionResult(BaseModel):
    """查询扩展结果，后面拆 expander 时用"""

    strategy: str
    expanded_query: str
    step_back_question: str | None = None
    step_back_answer: str | None = None
    hypothetical_doc: str | None = None
