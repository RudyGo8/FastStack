"""SOP / 通用 AI 知识问答：会话管理与 SSE 流式对话"""

import asyncio
import json
import time
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Security
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, redis_getter
from app.core.logger import logger
from app.core.router_class import OperationLogRoute
from app.modules.ai.chat.crud import _row_session_name, ChatSessionCRUD
from app.modules.ai.chat.schema import ChatQuerySchema
from app.modules.ai.chat.service import ChatService, get_user_model_config
from app.modules.sop.schemas.chat import (
    ChatRequest,
    MessageInfo,
    SessionDeleteResponse,
    SessionInfo,
    SessionListResponse,
    SessionMessagesResponse,
)

SopChatRouter = APIRouter(route_class=OperationLogRoute, prefix="/chat", tags=["AI 智能问答"])


@SopChatRouter.post("/stream", summary="流式问答(SSE)")
async def chat_stream_endpoint(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:chat:stream"]))],
    redis: Annotated[Redis, Depends(redis_getter)],
    request: Annotated[ChatRequest, Body(description="对话请求")],
) -> StreamingResponse:
    session_id = request.session_id or f"s_{int(time.time() * 1000)}"
    service = ChatService(auth)
    model_config = await get_user_model_config(redis, auth.user.id)
    query = ChatQuerySchema(message=request.message, session_id=session_id)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'rag_step', 'step': '正在思考中...'}, ensure_ascii=False)}\n\n"
            async for chunk in service.chat_query(query=query, model_config=model_config):
                if chunk:
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("SSE 流式生成异常: {}", e)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@SopChatRouter.get("/sessions/{session_id}", summary="获取会话消息", response_model=ResponseSchema[SessionMessagesResponse])
async def get_session_messages(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:chat:query"]))],
    session_id: str,
) -> JSONResponse:
    service = ChatService(auth)
    session = await service.get_session(session_id=session_id)
    raw_msgs = session.messages or [] if session else []
    messages = [
        MessageInfo(
            type="human" if m.get("role") == "user" else "ai",
            content=m.get("content", ""),
            timestamp=m.get("created_at", datetime.now().isoformat()),
        )
        for m in raw_msgs
    ]
    data = SessionMessagesResponse(messages=messages)
    return SuccessResponse(data=data, msg="获取会话消息成功")


@SopChatRouter.get("/sessions", summary="获取会话列表", response_model=ResponseSchema[SessionListResponse])
async def get_session_list(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:chat:query"]))],
) -> JSONResponse:
    crud = ChatSessionCRUD(auth)
    rows, _ = await crud.list_page(page_no=1, page_size=100)
    sessions = []
    for r in rows:
        sid = r.get("session_id") or ""
        title = _row_session_name(r) or "未命名会话"
        updated_at = r.get("updated_at")
        if isinstance(updated_at, (int, float)):
            updated_at = datetime.fromtimestamp(updated_at).isoformat()
        elif not updated_at:
            updated_at = datetime.now().isoformat()
        else:
            updated_at = str(updated_at)

        sessions.append(
            SessionInfo(
                session_id=sid,
                title=title,
                updated_at=updated_at,
                message_count=0,
            )
        )
    data = SessionListResponse(sessions=sessions)
    return SuccessResponse(data=data, msg="获取会话列表成功")


@SopChatRouter.delete("/sessions/{session_id}", summary="删除会话", response_model=ResponseSchema[SessionDeleteResponse])
async def delete_session(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:chat:delete"]))],
    session_id: str,
) -> JSONResponse:
    service = ChatService(auth)
    await service.delete(session_ids=[session_id])
    data = SessionDeleteResponse(session_id=session_id, message="会话已删除")
    return SuccessResponse(data=data, msg="删除会话成功")
