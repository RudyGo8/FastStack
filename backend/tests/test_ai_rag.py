"""RAG 单元测试：分块、词项权重、结果融合与参数校验。

存储层与真实 pgvector 的集成验证在 PostgreSQL 实例上单独执行（见 SKILL.md）。
"""

import pytest

from app.modules.ai.rag.chunker import lexical_embedding, split_document
from app.modules.ai.rag.model import VECTOR_DIMENSION
from app.modules.ai.rag.store import VectorStore, _check_vector, _require_tenant


# ─────────────────────────── 分块 ───────────────────────────


def test_split_empty_document_returns_empty():
    assert split_document("   \n\n  ", filename="a.txt") == ([], [])


def test_split_produces_children_bound_to_parent():
    text = "内容段落。" * 500
    parents, children = split_document(text, filename="a.txt", file_type="txt")
    assert parents and children
    parent_ids = {parent.chunk_id for parent in parents}
    assert all(child.parent_chunk_id in parent_ids for child in children)
    min_parent_level = min(parent.chunk_level for parent in parents)
    assert all(child.chunk_level > min_parent_level for child in children)


def test_split_chunk_ids_are_stable():
    first = split_document("同一份内容" * 200, filename="a.txt")
    second = split_document("同一份内容" * 200, filename="a.txt")
    assert [c.chunk_id for c in first[1]] == [c.chunk_id for c in second[1]]


def test_split_different_filename_yields_different_ids():
    a = split_document("同样内容" * 200, filename="a.txt")[1]
    b = split_document("同样内容" * 200, filename="b.txt")[1]
    assert {c.chunk_id for c in a}.isdisjoint({c.chunk_id for c in b})


def test_child_chunks_cover_document_content():
    text = "第一段。" * 100
    _, children = split_document(text, filename="a.txt")
    assert "".join(child.text for child in children[:1]) in text


# ─────────────────────── 词项权重（稀疏向量） ───────────────────────


def test_lexical_embedding_is_deterministic():
    first = lexical_embedding("FastStack 使用 PostgreSQL")
    second = lexical_embedding("FastStack 使用 PostgreSQL")
    assert first == second and first


def test_lexical_embedding_normalized():
    weights = lexical_embedding("aa aa bb")
    norm = sum(value * value for value in weights.values())
    assert abs(norm - 1.0) < 1e-9


def test_lexical_embedding_empty_text():
    assert lexical_embedding("") == {}


# ─────────────────────────── 结果融合（RRF） ───────────────────────────


def _hit(chunk_id: str) -> dict:
    return {"chunk_id": chunk_id, "text": chunk_id, "filename": "a.txt", "file_type": "txt", "page_number": 0}


def test_merge_prefers_documents_hit_by_both_paths():
    dense = [_hit("only_dense"), _hit("both")]
    sparse = [_hit("both"), _hit("only_sparse")]
    merged = VectorStore._merge(dense, sparse, top_k=3)
    assert merged[0]["chunk_id"] == "both"
    assert {item["chunk_id"] for item in merged} == {"both", "only_dense", "only_sparse"}


def test_merge_respects_top_k():
    dense = [_hit(f"d{i}") for i in range(10)]
    assert len(VectorStore._merge(dense, [], top_k=3)) == 3


def test_merge_empty_inputs():
    assert VectorStore._merge([], [], top_k=5) == []


# ─────────────────────────── 参数校验 ───────────────────────────


def test_check_vector_rejects_wrong_dimension():
    with pytest.raises(ValueError):
        _check_vector([0.1] * (VECTOR_DIMENSION - 1))


def test_check_vector_rejects_non_finite():
    vector = [0.0] * VECTOR_DIMENSION
    vector[0] = float("nan")
    with pytest.raises(ValueError):
        _check_vector(vector)


def test_require_tenant_rejects_blank():
    with pytest.raises(ValueError):
        _require_tenant("   ")


def test_require_tenant_trims():
    assert _require_tenant(" t1 ") == "t1"
