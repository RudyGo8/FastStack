"""
@create_time: 2026/02/02
@Author: GeChao
@File: document.py
"""

from pydantic import BaseModel


class DocumentInfo(BaseModel):
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class DocumentUploadResponse(BaseModel):
    filename: str
    chunks_processed: int
    message: str


class DocumentUploadResult(BaseModel):
    filename: str
    success: bool
    chunks_processed: int = 0
    message: str


class DocumentBatchUploadResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[DocumentUploadResult]
    message: str


class DocumentDeleteResponse(BaseModel):
    filename: str
    chunks_deleted: int
    message: str


class DocumentChunkInfo(BaseModel):
    chunk_id: str
    chunk_idx: int
    text_preview: str
    file_type: str
    page_number: int
    chunk_level: int


class DocumentChunkListResponse(BaseModel):
    filename: str
    chunks: list[DocumentChunkInfo]
