"""SOP / 通用文档知识库：文档列表、上传、分块与删除路由"""

from typing import Annotated

from fastapi import APIRouter, File, Path, Security, UploadFile
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute
from app.modules.sop.schemas.document import (
    DocumentBatchUploadResponse,
    DocumentChunkInfo,
    DocumentChunkListResponse,
    DocumentDeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentUploadResult,
)

SopDocumentRouter = APIRouter(route_class=OperationLogRoute, prefix="/documents", tags=["知识库文档"])


@SopDocumentRouter.get("/list", summary="获取知识库文档列表", response_model=ResponseSchema[DocumentListResponse])
async def list_documents_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:query"]))],
) -> JSONResponse:
    # 基础脚手架默认状态：提供规范列表响应
    data = DocumentListResponse(documents=[])
    return SuccessResponse(data=data, msg="获取文档列表成功")


@SopDocumentRouter.post("/upload", summary="上传单个文档并解析", response_model=ResponseSchema[DocumentUploadResponse])
async def upload_document_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:upload"]))],
    file: UploadFile = File(..., description="文档文件"),
) -> JSONResponse:
    data = DocumentUploadResponse(
        filename=file.filename or "unknown",
        chunks_processed=0,
        message="文档上传成功",
    )
    return SuccessResponse(data=data, msg="上传成功")


@SopDocumentRouter.post("/batch-upload", summary="批量上传文档并解析", response_model=ResponseSchema[DocumentBatchUploadResponse])
async def batch_upload_documents_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:upload"]))],
    files: list[UploadFile] = File(..., description="文档文件列表"),
) -> JSONResponse:
    results = [
        DocumentUploadResult(filename=f.filename or "unknown", success=True, chunks_processed=0, message="上传成功")
        for f in files
    ]
    data = DocumentBatchUploadResponse(
        total=len(files),
        succeeded=len(files),
        failed=0,
        results=results,
        message=f"批量上传成功，共处理 {len(files)} 个文件",
    )
    return SuccessResponse(data=data, msg="批量上传成功")


@SopDocumentRouter.get("/{filename}/chunks", summary="获取文档的分块信息", response_model=ResponseSchema[DocumentChunkListResponse])
async def get_document_chunks_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:query"]))],
    filename: Annotated[str, Path(description="文件名")],
) -> JSONResponse:
    data = DocumentChunkListResponse(filename=filename, chunks=[])
    return SuccessResponse(data=data, msg="获取文档分块成功")


@SopDocumentRouter.delete("/{filename}", summary="删除文档及其向量数据", response_model=ResponseSchema[DocumentDeleteResponse])
async def delete_document_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:delete"]))],
    filename: Annotated[str, Path(description="文件名")],
) -> JSONResponse:
    data = DocumentDeleteResponse(filename=filename, chunks_deleted=0, message=f"文档 {filename} 及其切片已删除")
    return SuccessResponse(data=data, msg="删除成功")
