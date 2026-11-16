"""可配置的嵌入服务（OpenAI 兼容 ``/embeddings`` 接口）。

模型、维度、Base URL 与 Key 全部来自配置；维度与表结构不一致时直接拒绝，
避免写入不可检索的向量。
"""

import httpx

from app.config.setting import settings
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.modules.ai.rag.model import VECTOR_DIMENSION


def _base_url() -> str:
    return (settings.RAG_EMBEDDING_BASE_URL or settings.OPENAI_BASE_URL or "").rstrip("/")


def _api_key() -> str:
    return settings.RAG_EMBEDDING_API_KEY or settings.OPENAI_API_KEY


def check_dimension() -> None:
    """启动/使用前的维度一致性校验。"""
    if settings.RAG_EMBEDDING_DIM != VECTOR_DIMENSION:
        raise ValueError(
            f"RAG_EMBEDDING_DIM={settings.RAG_EMBEDDING_DIM} 与向量表结构 {VECTOR_DIMENSION} 不一致，"
            "请修改表结构并迁移后再启用"
        )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量生成稠密向量；任何一条失败都抛错，不写入部分结果。"""
    if not texts:
        return []
    check_dimension()
    base_url, api_key = _base_url(), _api_key()
    if not base_url or not api_key:
        raise CustomException(msg="未配置嵌入服务：请设置 RAG_EMBEDDING_BASE_URL / RAG_EMBEDDING_API_KEY 或 OPENAI_*")

    vectors: list[list[float]] = []
    batch_size = max(1, settings.RAG_EMBEDDING_BATCH_SIZE)
    async with httpx.AsyncClient(timeout=60.0) as client:
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = await client.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": settings.RAG_EMBEDDING_MODEL, "input": batch, "dimensions": settings.RAG_EMBEDDING_DIM},
            )
            if response.status_code >= 400:
                logger.warning(f"嵌入请求失败 status={response.status_code}")
                raise CustomException(msg=f"嵌入服务返回 {response.status_code}: {response.text[:200]}")
            payload = response.json()
            vectors.extend(item["embedding"] for item in payload.get("data", []))
    if len(vectors) != len(texts):
        raise CustomException(msg=f"嵌入返回数量不一致：期望 {len(texts)}，实际 {len(vectors)}")
    return vectors
