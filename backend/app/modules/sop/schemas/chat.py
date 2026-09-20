"""
@create_time: 2026/02/02
@Author: GeChao
@File: chat.py
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = "default_session"


class RetrievedChunk(BaseModel):
    filename: str
    page_number: str | int | None = None
    text: str | None = None
    score: float | None = None


class RagTrace(BaseModel):
    model_config = ConfigDict(extra="allow")
    tool_used: bool = False
    tool_name: str = ""
    query: str | None = None
    expanded_query: str | None = None
    retrieval_stage: str | None = None
    grade_score: str | None = None
    rewrite_strategy: str | None = None
    token_usage: dict[str, Any] | None = None
    retrieved_chunks: list[dict[str, Any]] | None = None


class MessageInfo(BaseModel):
    type: str
    content: str
    timestamp: str
    rag_trace: RagTrace | None = None


class SessionMessagesResponse(BaseModel):
    messages: list[MessageInfo]


class SessionInfo(BaseModel):
    session_id: str
    title: str = ""
    updated_at: str
    message_count: int


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]


class SessionDeleteResponse(BaseModel):
    session_id: str
    message: str
