"""SOP 文档管理：上传解析入向量库（收编自 SopAgent api/routes/document.py）"""

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Security, UploadFile

from app.common.response import JSONResponse, ResponseSchema, SuccessResponse
from app.config.path_conf import BASE_DIR
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
from app.modules.sop.services.milvus_service import milvus_service
from app.modules.sop.services.milvus_writer import milvus_writer
from app.modules.sop.services.parent_chunk_store import parent_chunk_store
from app.modules.sop.utils.log import get_logger

logger = get_logger(__name__)

SopDocumentRouter = APIRouter(route_class=OperationLogRoute, prefix="/documents", tags=["SOP 文档管理"])

UPLOAD_DIR = BASE_DIR / "data" / "sop" / "documents"
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".doc", ".xlsx", ".xls")


def _sanitize_filename(raw_name: str) -> str:
    name = (raw_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename is required")
    safe_name = Path(name).name.strip()
    if safe_name != name or safe_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="invalid filename")
    return safe_name


def _validate_supported_file(filename: str) -> None:
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only PDF, Word, and Excel documents are supported")


def _escape_milvus_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _write_upload_to_milvus(file_path: Path, filename: str) -> int:
    return milvus_writer.write_documents(str(file_path), filename)


@SopDocumentRouter.get("/list", summary="文档列表", response_model=ResponseSchema[DocumentListResponse])
async def list_documents(
    _: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:query"]))],
) -> JSONResponse:
    try:
        milvus_service.init_collection()
        results = milvus_service.query(output_fields=["filename", "file_type"], limit=10000)

        file_stats = {}
        for item in results:
            filename = item.get("filename", "")
            file_type = item.get("file_type", "")
            if filename not in file_stats:
                file_stats[filename] = {"filename": filename, "file_type": file_type, "chunk_count": 0}
            file_stats[filename]["chunk_count"] += 1

        documents = [DocumentInfo(**stats) for stats in file_stats.values()]
        return SuccessResponse(data=DocumentListResponse(documents=documents), msg="获取文档列表成功")
    except Exception as e:
        logger.exception("Failed to load document list")
        raise HTTPException(status_code=500, detail=f"Failed to load document list: {str(e)}")


@SopDocumentRouter.post("/upload", summary="上传文档", response_model=ResponseSchema[DocumentUploadResponse])
async def upload_document(
    _: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:upload"]))],
    file: Annotated[UploadFile, File(...)],
) -> JSONResponse:
    filename = _sanitize_filename(file.filename or "")
    _validate_supported_file(filename)

    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as f:
            f.write(await file.read())

        chunk_count = _write_upload_to_milvus(file_path, filename)
        data = DocumentUploadResponse(
            filename=filename,
            chunks_processed=chunk_count,
            message=f"Uploaded {filename}, processed {chunk_count} chunks",
        )
        return SuccessResponse(data=data, msg="文档上传成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Document upload failed: %s", filename)
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@SopDocumentRouter.post("/batch-upload", summary="批量上传文档", response_model=ResponseSchema[DocumentBatchUploadResponse])
async def batch_upload_document(
    _: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:upload"]))],
    files: Annotated[list[UploadFile], File(...)],
) -> JSONResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    results: list[DocumentUploadResult] = []

    for file in files:
        filename = file.filename or "unknown"
        try:
            filename = _sanitize_filename(filename)
            _validate_supported_file(filename)

            file_path = UPLOAD_DIR / filename
            with open(file_path, "wb") as f:
                f.write(await file.read())

            chunk_count = _write_upload_to_milvus(file_path, filename)
            results.append(
                DocumentUploadResult(
                    filename=filename,
                    success=True,
                    chunks_processed=chunk_count,
                    message=f"Uploaded {filename}, processed {chunk_count} chunks",
                )
            )
        except HTTPException as e:
            results.append(DocumentUploadResult(filename=filename, success=False, chunks_processed=0, message=str(e.detail)))
        except Exception as e:
            logger.exception("Batch upload failed for: %s", filename)
            results.append(DocumentUploadResult(filename=filename, success=False, chunks_processed=0, message=str(e)))

    succeeded = sum(1 for item in results if item.success)
    failed = len(results) - succeeded
    data = DocumentBatchUploadResponse(
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        results=results,
        message=f"Batch upload completed: {succeeded} succeeded, {failed} failed",
    )
    return SuccessResponse(data=data, msg="批量上传完成")


@SopDocumentRouter.get("/{filename}/chunks", summary="文档分块预览", response_model=ResponseSchema[DocumentChunkListResponse])
async def get_document_chunks(
    _: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:query"]))],
    filename: str,
) -> JSONResponse:
    safe_filename = _sanitize_filename(filename)
    chunks = parent_chunk_store.get_chunks_by_filename(safe_filename)
    if not chunks:
        raise HTTPException(status_code=404, detail=f"No chunks found for {safe_filename}")
    data = DocumentChunkListResponse(
        filename=safe_filename,
        chunks=[DocumentChunkInfo(**c) for c in chunks],
    )
    return SuccessResponse(data=data, msg="获取分块列表成功")


@SopDocumentRouter.delete("/{filename}", summary="删除文档向量", response_model=ResponseSchema[DocumentDeleteResponse])
async def delete_document(
    _: Annotated[AuthSchema, Security(AuthPermission(["module_sop:document:delete"]))],
    filename: str,
) -> JSONResponse:
    try:
        safe_filename = _sanitize_filename(filename)
        milvus_service.init_collection()
        delete_expr = f'filename == "{_escape_milvus_string(safe_filename)}"'
        result = milvus_service.delete(delete_expr)

        data = DocumentDeleteResponse(
            filename=safe_filename,
            chunks_deleted=result.get("delete_count", 0) if isinstance(result, dict) else 0,
            message=f"Deleted vector data for {safe_filename}",
        )
        return SuccessResponse(data=data, msg="删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Document delete failed: %s", filename)
        raise HTTPException(status_code=500, detail=f"Document delete failed: {str(e)}")
