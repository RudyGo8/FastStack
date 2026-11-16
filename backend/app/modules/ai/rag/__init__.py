"""通用 RAG：pgvector 存储 + 父子分块 + 混合检索。

仅在 ``VECTOR_STORE_ENABLE=True`` 且 ``DATABASE_TYPE=postgres`` 时可用，
未启用时不影响普通项目启动，也不要求数据库预装 pgvector。
"""

from app.modules.ai.rag.service import RagService

__all__ = ["RagService"]
