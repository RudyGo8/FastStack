"""文档分块：父块保留完整上下文，子块用于检索。

父子分块的目的：检索只在小块上做（召回准），送给模型的是父块（上下文完整）。
切分按字符窗口滑动，不做语义切分——语义切分依赖模型且成本高，通用脚手架不默认开启。
"""

import hashlib
from dataclasses import dataclass

from app.config.setting import settings

FILE_TYPE_MAP = {
    "text/plain": "txt",
    "text/markdown": "md",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


@dataclass
class Chunk:
    chunk_id: str
    text: str
    parent_chunk_id: str
    chunk_level: int
    chunk_idx: int
    filename: str
    file_type: str
    page_number: int = 0


def _digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def _windows(text: str, size: int, overlap: int) -> list[str]:
    """按字符窗口滑动切分；overlap 必须小于 size，否则退化为无重叠。"""
    size = max(1, size)
    step = size - overlap if 0 <= overlap < size else size
    return [text[start : start + size] for start in range(0, len(text), step)] if text else []


def split_document(text: str, *, filename: str, file_type: str = "", page_number: int = 0) -> tuple[list[Chunk], list[Chunk]]:
    """返回 ``(父块列表, 子块列表)``。空文本返回两个空列表。"""
    normalized = "\n".join(line.rstrip() for line in (text or "").splitlines()).strip()
    if not normalized:
        return [], []

    parents: list[Chunk] = []
    children: list[Chunk] = []
    for p_index, parent_text in enumerate(_windows(normalized, settings.RAG_PARENT_CHUNK_SIZE, 0)):
        parent_id = _digest(filename, "p", str(p_index), parent_text)
        parents.append(
            Chunk(
                chunk_id=parent_id,
                text=parent_text,
                parent_chunk_id="",
                chunk_level=1,
                chunk_idx=p_index,
                filename=filename,
                file_type=file_type,
                page_number=page_number,
            )
        )
        for c_index, child_text in enumerate(
            _windows(parent_text, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP)
        ):
            children.append(
                Chunk(
                    chunk_id=_digest(filename, "c", str(p_index), str(c_index), child_text),
                    text=child_text,
                    parent_chunk_id=parent_id,
                    chunk_level=3,
                    chunk_idx=c_index,
                    filename=filename,
                    file_type=file_type,
                    page_number=page_number,
                )
            )
    return parents, children


def lexical_embedding(value: str) -> dict[str, float]:
    """稳定词项权重：中文按单字、英文按词切分，TF 归一化后做键哈希。

    不依赖进程内词表或语料统计，因此同一文本在任意节点上得分一致。
    """
    import math
    import re
    from collections import Counter

    tokens = Counter(re.findall(r"[a-z0-9]+|[一-鿿]", (value or "").lower()))
    norm = math.sqrt(sum(count * count for count in tokens.values()))
    if not norm:
        return {}
    return {"lex:" + hashlib.sha256(token.encode()).hexdigest(): count / norm for token, count in tokens.items()}
