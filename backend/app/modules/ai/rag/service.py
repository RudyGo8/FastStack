"""RAG 编排：入库、检索、来源追踪。

入库 = 分块 → 批量嵌入 → 原子替换；检索 = 稠密 + 稀疏混合召回 → 回溯父块 → 汇总来源。
任何一步失败都不写入部分数据。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.core.exceptions import CustomException
from app.modules.ai.rag.chunker import lexical_embedding, split_document
from app.modules.ai.rag.embedding import embed_texts, check_dimension
from app.modules.ai.rag.store import VectorStore


def _tenant(tenant_id: str | None) -> str:
    return (tenant_id or "").strip() or settings.RAG_TENANT_ID


def _enabled() -> None:
    """未启用时返回业务错误而非 500，前端才能给出可读提示。"""
    if not settings.VECTOR_STORE_ENABLE:
        raise CustomException(msg="向量检索未启用：请设置 VECTOR_STORE_ENABLE=True 并使用 PostgreSQL")
    if settings.DATABASE_TYPE != "postgres":
        raise CustomException(msg="向量检索仅支持 DATABASE_TYPE=postgres")
    try:
        check_dimension()
    except ValueError as exc:
        raise CustomException(msg=str(exc)) from exc


class RagService:
    @staticmethod
    async def ingest_document(
        db: AsyncSession,
        *,
        filename: str,
        content: str,
        file_type: str = "",
        tenant_id: str | None = None,
    ) -> dict:
        """整篇替换入库，返回写入的分块数。"""
        _enabled()
        tenant = _tenant(tenant_id)
        parents, children = split_document(content, filename=filename, file_type=file_type)
        if not children:
            raise ValueError("文档内容为空或无法切分")
        vectors = await embed_texts([chunk.text for chunk in children])
        child_rows = [
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "filename": chunk.filename,
                "file_type": chunk.file_type,
                "page_number": chunk.page_number,
                "parent_chunk_id": chunk.parent_chunk_id,
                "chunk_level": chunk.chunk_level,
                "dense_embedding": vector,
                "sparse_embedding": lexical_embedding(chunk.text),
            }
            for chunk, vector in zip(children, vectors, strict=True)
        ]
        parent_rows = [
            {
                "chunk_id": parent.chunk_id,
                "text": parent.text,
                "filename": parent.filename,
                "file_type": parent.file_type,
                "page_number": parent.page_number,
                "parent_chunk_id": "",
                "root_chunk_id": parent.chunk_id,
                "chunk_level": parent.chunk_level,
                "chunk_idx": parent.chunk_idx,
            }
            for parent in parents
        ]
        written = await VectorStore.replace_document(
            db, tenant_id=tenant, filename=filename, children=child_rows, parents=parent_rows
        )
        return {"filename": filename, "chunks": written, "parents": len(parent_rows)}

    @staticmethod
    async def search(
        db: AsyncSession,
        *,
        query: str,
        top_k: int | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        """混合检索并回溯父块，返回命中与来源清单。"""
        _enabled()
        tenant = _tenant(tenant_id)
        limit = top_k or settings.RAG_TOP_K
        vector = (await embed_texts([query]))[0]
        hits = await VectorStore.hybrid_search(
            db, tenant_id=tenant, dense=vector, query_text=query, top_k=limit
        )
        parent_ids = sorted({hit["parent_chunk_id"] for hit in hits if hit.get("parent_chunk_id")})
        parents = await VectorStore.load_parents(db, tenant_id=tenant, parent_ids=parent_ids)
        for hit in hits:
            hit["parent_text"] = parents.get(hit.get("parent_chunk_id", ""), "")
        return {"hits": hits, "sources": sorted({hit["filename"] for hit in hits})}

    @staticmethod
    async def list_documents(db: AsyncSession, *, tenant_id: str | None = None) -> dict:
        _enabled()
        return {"documents": await VectorStore.document_stats(db, tenant_id=_tenant(tenant_id))}

    @staticmethod
    async def delete_document(db: AsyncSession, *, filename: str, tenant_id: str | None = None) -> dict:
        _enabled()
        deleted = await VectorStore.delete_document(db, tenant_id=_tenant(tenant_id), filename=filename)
        return {"filename": filename, "deleted_chunks": deleted}
