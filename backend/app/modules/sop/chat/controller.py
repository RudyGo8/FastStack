"""SOP 知识问答：会话管理与 SSE 流式对话（收编自 SopAgent api/routes/chat.py）"""

from typing import Annotated

from fastapi import APIRouter, Body, Security
from fastapi.responses import StreamingResponse

from app.common.response import JSONResponse, ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute
from app.modules.sop.agent import chat_with_agent_stream
from app.modules.sop.schemas.chat import (
    ChatRequest,
    MessageInfo,
    SessionDeleteResponse,
    SessionInfo,
    SessionListResponse,
    SessionMessagesResponse,
)
from app.modules.sop.services.conversation_service import conversation_service

SopChatRouter = APIRouter(route_class=OperationLogRoute, prefix="/chat", tags=["SOP 知识问答"])


@SopChatRouter.post("/stream", summary="流式问答(SSE)")
async def chat_stream_endpoint(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:chat:stream"]))],
    request: Annotated[ChatRequest, Body(description="对话请求")],
) -> StreamingResponse:
    session_id = request.session_id or "default_session"
    return StreamingResponse(
        chat_with_agent_stream(request.message, auth.user.username, session_id),
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
    messages = conversation_service.get_session_messages(auth.user.username, session_id)
    data = SessionMessagesResponse(messages=[MessageInfo(**msg) for msg in messages])
    return SuccessResponse(data=data, msg="获取会话消息成功")


@SopChatRouter.get("/sessions", summary="获取会话列表", response_model=ResponseSchema[SessionListResponse])
async def get_session_list(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:chat:query"]))],
) -> JSONResponse:
    sessions = conversation_service.list_session_infos(auth.user.username)
    data = SessionListResponse(sessions=[SessionInfo(**item) for item in sessions])
    return SuccessResponse(data=data, msg="获取会话列表成功")


@SopChatRouter.delete("/sessions/{session_id}", summary="删除会话", response_model=ResponseSchema[SessionDeleteResponse])
async def delete_session(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:chat:delete"]))],
    session_id: str,
) -> JSONResponse:
    success = conversation_service.delete_session(auth.user.username, session_id)
    data = SessionDeleteResponse(session_id=session_id, message="会话已删除" if success else "会话不存在")
    return SuccessResponse(data=data, msg="删除会话成功" if success else "会话不存在")
