"""RAG 接口：文档入库、检索、清单与删除。

权限统一为 ``module_ai:rag:*`` 三段式；向量检索未启用时接口返回业务错误而非 500。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import (
    RagDocumentListOut,
    RagIngestIn,
    RagIngestOut,
    RagSearchIn,
    RagSearchOut,
)
from .service import RagService

RagRouter = APIRouter(route_class=OperationLogRoute, prefix="/rag", tags=["RAG 知识库"])


@RagRouter.post("/document", summary="文档入库（整篇替换）", response_model=ResponseSchema[RagIngestOut])
async def ingest_document_controller(
    data: RagIngestIn,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:rag:upload"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await RagService.ingest_document(
        db,
        filename=data.filename,
        content=data.content,
        file_type=data.file_type,
        tenant_id=data.tenant_id,
    )
    return SuccessResponse(data=result, msg="文档入库成功")


@RagRouter.post("/search", summary="知识库检索", response_model=ResponseSchema[RagSearchOut])
async def search_controller(
    data: RagSearchIn,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:rag:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await RagService.search(db, query=data.query, top_k=data.top_k or None, tenant_id=data.tenant_id)
    return SuccessResponse(data=result, msg="检索成功")


@RagRouter.get("/documents", summary="已入库文档清单", response_model=ResponseSchema[RagDocumentListOut])
async def list_documents_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:rag:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    tenant_id: str = "",
) -> JSONResponse:
    result = await RagService.list_documents(db, tenant_id=tenant_id)
    return SuccessResponse(data=result, msg="获取文档清单成功")


@RagRouter.delete("/document", summary="删除文档及其分块", response_model=ResponseSchema)
async def delete_document_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:rag:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    filename: str,
    tenant_id: str = "",
) -> JSONResponse:
    result = await RagService.delete_document(db, filename=filename, tenant_id=tenant_id)
    return SuccessResponse(data=result, msg="删除成功")
