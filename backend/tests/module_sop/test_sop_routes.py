"""SOP 模块路由注册与鉴权冒烟测试。

- 未登录访问 sop 接口应被拒绝（401/403）
- 登录后路由存在（非 404；业务异常如基础设施未就绪不算失败）

注意：不要从 conftest import 辅助函数 —— tests/ 非包，命名空间包方式二次导入
conftest 会重复执行模块级初始化（临时库/引擎错位），曾导致迁移守卫误报。
"""

from fastapi.testclient import TestClient
from unittest.mock import patch


def test_sop_routes_require_auth(test_client: TestClient) -> None:
    for path in [
        "/sop/data/status",
        "/sop/data/spus",
        "/sop/documents/list",
        "/sop/chat/sessions",
        "/sop/report/snapshots",
    ]:
        resp = test_client.get(path)
        assert resp.status_code in (401, 403), f"GET {path} 未登录应被拒绝，实际 {resp.status_code}"


def test_sop_routes_registered(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    for path in [
        "/sop/data/spus",
        "/sop/chat/sessions",
        "/sop/documents/list",
        "/sop/report/snapshots",
    ]:
        resp = test_client.get(path, headers=auth_headers)
        assert resp.status_code != 404, f"GET {path} 返回 404，路由未注册"


def test_document_chunks_are_filtered_by_filename(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    chunks = [{"chunk_id": "c1", "ordinal": 2, "text": "第二段", "metadata": {"filename": "policy.pdf"}}]
    with patch("app.modules.sop.document.controller.parent_chunk_store.get_chunks_by_filename", return_value=chunks):
        response = test_client.get("/sop/documents/policy.pdf/chunks", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["filename"] == "policy.pdf"
    assert response.json()["data"]["chunks"] == chunks
