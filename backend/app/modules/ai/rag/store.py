"""pgvector 存储：写入、删除、稠密/稀疏/混合检索。

隔离方式：所有读写都必须带 ``tenant_id``，任何一条语句漏掉都会被这里拦住。
写入按文件名原子替换，并用 PostgreSQL 咨询锁串行化同一文件的并发入库。
"""

import json
import math

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.modules.ai.rag.chunker import lexical_embedding
from app.modules.ai.rag.model import VECTOR_DIMENSION, VectorChunkModel, VectorCollectionModel, VectorParentChunkModel

FIELDS = ("chunk_id", "text", "filename", "file_type", "page_number", "parent_chunk_id", "chunk_level")


def _check_vector(dense: list[float]) -> None:
    if len(dense) != VECTOR_DIMENSION or not all(math.isfinite(float(x)) for x in dense):
        raise ValueError(f"向量维度或数值非法：期望 {VECTOR_DIMENSION} 维有限浮点数")


def _require_tenant(tenant_id: str) -> str:
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id 不能为空")
    return tenant_id.strip()


class VectorStore:
    """基于 PostgreSQL + pgvector 的通用向量存储。"""

    @staticmethod
    async def ensure_collection(db: AsyncSession, *, tenant_id: str) -> None:
        """登记并校验嵌入模型/维度；不一致时直接拒绝，避免混写。"""
        if settings.RAG_EMBEDDING_DIM != VECTOR_DIMENSION:
            raise ValueError(
                f"RAG_EMBEDDING_DIM={settings.RAG_EMBEDDING_DIM} 与表结构 {VECTOR_DIMENSION} 不一致"
            )
        row = await db.get(VectorCollectionModel, tenant_id)
        if row is None:
            db.add(
                VectorCollectionModel(
                    name=tenant_id,
                    embedding_model=settings.RAG_EMBEDDING_MODEL,
                    dimension=settings.RAG_EMBEDDING_DIM,
                )
            )
            await db.flush()
            return
        if row.dimension != settings.RAG_EMBEDDING_DIM or row.embedding_model != settings.RAG_EMBEDDING_MODEL:
            raise ValueError(
                f"已有向量使用 {row.embedding_model}/{row.dimension} 维，"
                f"与当前配置 {settings.RAG_EMBEDDING_MODEL}/{settings.RAG_EMBEDDING_DIM} 维不一致"
            )

    @staticmethod
    async def replace_document(
        db: AsyncSession,
        *,
        tenant_id: str,
        filename: str,
        children: list[dict],
        parents: list[dict],
    ) -> int:
        """整篇替换：删除同租户同文件名的旧分块后写入新分块。"""
        tenant_id = _require_tenant(tenant_id)
        await VectorStore.ensure_collection(db, tenant_id=tenant_id)
        async with db.begin_nested():
            await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"{tenant_id}:{filename}"})
            await db.execute(
                delete(VectorChunkModel).where(
                    VectorChunkModel.tenant_id == tenant_id, VectorChunkModel.filename == filename
                )
            )
            await db.execute(
                delete(VectorParentChunkModel).where(
                    VectorParentChunkModel.tenant_id == tenant_id, VectorParentChunkModel.filename == filename
                )
            )
            db.add_all(
                [
                    VectorParentChunkModel(tenant_id=tenant_id, **{k: v for k, v in row.items() if k in VectorParentChunkModel.__table__.columns})
                    for row in parents
                ]
            )
            db.add_all(
                [
                    VectorChunkModel(tenant_id=tenant_id, **{k: v for k, v in row.items() if k in VectorChunkModel.__table__.columns})
                    for row in children
                ]
            )
        return len(children)

    @staticmethod
    async def delete_document(db: AsyncSession, *, tenant_id: str, filename: str) -> int:
        tenant_id = _require_tenant(tenant_id)
        result = await db.execute(
            delete(VectorChunkModel).where(
                VectorChunkModel.tenant_id == tenant_id, VectorChunkModel.filename == filename
            )
        )
        await db.execute(
            delete(VectorParentChunkModel).where(
                VectorParentChunkModel.tenant_id == tenant_id, VectorParentChunkModel.filename == filename
            )
        )
        return result.rowcount or 0

    @staticmethod
    async def document_stats(db: AsyncSession, *, tenant_id: str) -> list[dict]:
        tenant_id = _require_tenant(tenant_id)
        statement = (
            select(
                VectorChunkModel.filename,
                VectorChunkModel.file_type,
                func.count().label("chunks"),
            )
            .where(VectorChunkModel.tenant_id == tenant_id)
            .group_by(VectorChunkModel.filename, VectorChunkModel.file_type)
            .order_by(VectorChunkModel.filename)
        )
        return [dict(row) for row in (await db.execute(statement)).mappings()]

    @staticmethod
    async def dense_search(db: AsyncSession, *, tenant_id: str, dense: list[float], top_k: int) -> list[dict]:
        tenant_id = _require_tenant(tenant_id)
        _check_vector(dense)
        distance = VectorChunkModel.dense_embedding.max_inner_product(dense)
        statement = (
            select(VectorChunkModel, distance.label("distance"))
            .where(VectorChunkModel.tenant_id == tenant_id)
            .order_by(distance)
            .limit(max(0, top_k))
        )
        rows = await db.execute(statement)
        return [{**{f: getattr(row, f) for f in FIELDS}, "score": float(-dist)} for row, dist in rows]

    @staticmethod
    async def sparse_search(db: AsyncSession, *, tenant_id: str, sparse: dict, limit: int) -> list[dict]:
        tenant_id = _require_tenant(tenant_id)
        if not sparse:
            return []
        columns = ", ".join("c." + field for field in FIELDS)
        statement = text(
            f"""SELECT {columns}, SUM(s.value::float * q.value::float) AS score
                FROM ai_vector_chunk c CROSS JOIN LATERAL jsonb_each_text(c.sparse_embedding) s
                JOIN jsonb_each_text(CAST(:query AS jsonb)) q ON q.key = s.key
                WHERE c.tenant_id = :tenant
                  AND c.sparse_embedding ?| CAST(:keys AS text[])
                GROUP BY {columns}
                HAVING SUM(s.value::float * q.value::float) > 0
                ORDER BY score DESC LIMIT :limit"""
        )
        params = {
            "tenant": tenant_id,
            "query": json.dumps(sparse),
            "keys": [str(key) for key in sparse],
            "limit": max(0, limit),
        }
        result = await db.execute(statement, params)
        return [
            {**{field: row[field] for field in FIELDS}, "score": float(row["score"])}
            for row in result.mappings().all()
        ]

    @staticmethod
    def _merge(dense_hits: list[dict], sparse_hits: list[dict], top_k: int) -> list[dict]:
        """RRF 融合：按名次而非分数量纲合并两路结果。"""
        combined: dict[str, dict] = {}
        for hits in (dense_hits, sparse_hits):
            for rank, hit in enumerate(hits, 1):
                combined.setdefault(hit["chunk_id"], {**hit, "score": 0.0})["score"] += 1 / (60 + rank)
        return sorted(combined.values(), key=lambda item: -item["score"])[: max(0, top_k)]

    @staticmethod
    async def hybrid_search(
        db: AsyncSession, *, tenant_id: str, dense: list[float], query_text: str, top_k: int
    ) -> list[dict]:
        sparse = lexical_embedding(query_text)
        dense_hits = await VectorStore.dense_search(db, tenant_id=tenant_id, dense=dense, top_k=top_k * 2)
        sparse_hits = (
            await VectorStore.sparse_search(db, tenant_id=tenant_id, sparse=sparse, limit=top_k * 2) if sparse else []
        )
        return VectorStore._merge(dense_hits, sparse_hits, top_k)

    @staticmethod
    async def load_parents(db: AsyncSession, *, tenant_id: str, parent_ids: list[str]) -> dict[str, str]:
        """按父块 ID 取回完整上下文，供检索结果回溯。"""
        if not parent_ids:
            return {}
        statement = select(VectorParentChunkModel.chunk_id, VectorParentChunkModel.text).where(
            VectorParentChunkModel.tenant_id == _require_tenant(tenant_id),
            VectorParentChunkModel.chunk_id.in_(parent_ids),
        )
        return {row[0]: row[1] for row in (await db.execute(statement)).all()}
