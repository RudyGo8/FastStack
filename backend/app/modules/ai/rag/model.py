"""通用 RAG 向量存储模型。

表名统一 ``ai_*``，与任何业务模块无关；``tenant_id`` 提供项目/租户级隔离。
向量列在 PostgreSQL 用 pgvector 原生类型，其余方言退化为 JSON 仅用于隔离测试。
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase

# 稠密向量维度：改这里必须同步迁移表结构，启动时会校验配置一致性
VECTOR_DIMENSION = 1536


class VectorCollectionModel(MappedBase):
    """向量集合的嵌入模型与维度登记，用于启动时兼容性校验。"""

    __tablename__: str = "ai_vector_collection"
    __table_args__ = ({"comment": "RAG 向量集合配置表"},)

    name: Mapped[str] = mapped_column(String(128), primary_key=True, comment="向量集合名称")
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False, comment="生成向量的嵌入模型标识")
    dimension: Mapped[int] = mapped_column(Integer, nullable=False, comment="嵌入向量维度")


class VectorParentChunkModel(MappedBase):
    """父分块：保留完整上下文，检索命中子块后回溯父块送给模型。"""

    __tablename__: str = "ai_vector_parent_chunk"
    __table_args__ = (
        Index("ix_ai_vector_parent_chunk_tenant", "tenant_id", "filename"),
        {"comment": "RAG 文档父分块表"},
    )

    chunk_id: Mapped[str] = mapped_column(String(512), primary_key=True, comment="分块唯一标识")
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default", comment="租户/项目隔离标识")
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="分块正文")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="来源文件名")
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="来源文件类型")
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="来源页码")
    parent_chunk_id: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="父分块标识")
    root_chunk_id: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="根分块标识")
    chunk_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="分块层级")
    chunk_idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="文档内顺序")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, comment="扩展元数据")
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")


class VectorChunkModel(MappedBase):
    """检索叶子块：稠密向量 + 稀疏词项权重。"""

    __tablename__: str = "ai_vector_chunk"
    __table_args__ = (
        Index("ix_ai_vector_chunk_tenant_filename", "tenant_id", "filename"),
        Index(
            "ix_ai_vector_chunk_sparse_gin",
            "sparse_embedding",
            postgresql_using="gin",
            postgresql_ops={"sparse_embedding": "jsonb_ops"},
        ),
        Index(
            "ix_ai_vector_chunk_hnsw",
            "dense_embedding",
            postgresql_using="hnsw",
            postgresql_ops={"dense_embedding": "vector_ip_ops"},
            postgresql_with={"m": 16, "ef_construction": 256},
        ),
        {"comment": "RAG 向量叶子分块表"},
    )

    chunk_id: Mapped[str] = mapped_column(String(512), primary_key=True, comment="分块唯一标识")
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default", comment="租户/项目隔离标识")
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="分块正文")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="来源文件名")
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="来源文件类型")
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="来源页码")
    parent_chunk_id: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="父分块标识")
    chunk_level: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="分块层级")
    dense_embedding: Mapped[list] = mapped_column(
        Vector(VECTOR_DIMENSION).with_variant(JSON(), "sqlite"),
        nullable=False,
        comment="稠密语义向量",
    )
    sparse_embedding: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
        comment="稀疏词项权重（JSON）",
    )
