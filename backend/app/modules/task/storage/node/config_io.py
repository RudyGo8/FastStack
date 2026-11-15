"""存储源配置导出/导入（**不含凭据**）。

为什么不含 ``password``：导出文件最常见的去处是群聊/工单/博客，带上密码等于把凭据抄一份出去；
导入后让用户重填一次，比事后收不回来强。这个决定改之前请先想清楚后果。
``advanced_config`` 同样不导出（它是 SDK 参数 JSON，可能含代理等敏感信息）。

设计成纯函数，便于不依赖数据库直接测试；数据库读写留在 ``StorageNodeService``。
"""

from datetime import UTC, datetime
from typing import Any

from .model import StorageNodeModel

EXPORT_VERSION = 1

# 可导出的字段（纯配置；password / advanced_config / is_default 一律不导出）
EXPORT_FIELDS: tuple[str, ...] = (
    "name",
    "protocol",
    "host",
    "port",
    "username",
    "bucket",
    "endpoint",
    "region",
    "path_prefix",
    "is_secure",
    "implicit_tls",
    "scheme",
    "encrypt_type",
    "connection_mode",
    "encoding",
    "multipart_part_size",
    "multipart_concurrency",
    "multipart_memory_budget",
    "status",
    "description",
)

# 导入时的协议白名单（与 StorageProtocol 保持一致，避免把脏值写进库）
_VALID_PROTOCOLS = frozenset(
    {"ftp", "ftps", "sftp", "s3", "obs", "oss", "cos", "local"}
)


def build_export(nodes: list[StorageNodeModel]) -> dict[str, Any]:
    """把存储源列表打包成可传阅的 JSON 结构（不含凭据）。"""
    return {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "nodes": [{field: getattr(node, field) for field in EXPORT_FIELDS} for node in nodes],
    }


def plan_import(
    data: dict[str, Any], existing_names: set[str]
) -> tuple[list[dict[str, Any]], int, int]:
    """规划导入：按名称去重，**已存在的绝不覆盖**。

    返回:
    - tuple[list[dict[str, Any]], int, int]: (待创建条目, 跳过数, 非法数)
    """
    to_create: list[dict[str, Any]] = []
    skipped = 0
    invalid = 0
    seen = set(existing_names)

    items = data.get("nodes") if isinstance(data, dict) else None
    for item in items or []:
        if not isinstance(item, dict):
            invalid += 1
            continue
        name = str(item.get("name") or "").strip()
        protocol = str(item.get("protocol") or "").strip().lower()
        if not name or protocol not in _VALID_PROTOCOLS:
            invalid += 1
            continue
        if name in seen:
            skipped += 1
            continue
        payload: dict[str, Any] = {
            field: item[field] for field in EXPORT_FIELDS if field in item and item[field] is not None
        }
        payload["name"] = name
        payload["protocol"] = protocol
        # port 在库里非空且无默认值：缺失时给协议默认端口，避免插入失败
        try:
            payload["port"] = int(payload.get("port") or 0) or _default_port(protocol)
        except (TypeError, ValueError):
            payload["port"] = _default_port(protocol)
        to_create.append(payload)
        seen.add(name)

    return to_create, skipped, invalid


def _default_port(protocol: str) -> int:
    """按协议给出默认端口。"""
    return {
        "ftp": 21,
        "ftps": 21,
        "sftp": 22,
        "s3": 443,
        "oss": 443,
        "cos": 443,
        "obs": 443,
        "local": 0,
    }.get(protocol, 21)
