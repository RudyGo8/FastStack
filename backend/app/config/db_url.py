"""数据库 / Redis 连接串构造。

统一使用百分号编码，避免密码中的 ``@ ! # / :`` 等特殊字符被当作
URL 分隔符；不要用字符串拼接后再手写 ``quote_plus``，否则用户名、
库名、host 与密码的编码规则容易不一致。
"""

from __future__ import annotations

from urllib.parse import quote

from sqlalchemy.engine import URL


def build_sqlalchemy_url(
    drivername: str,
    *,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str | None = None,
    query: dict[str, str] | None = None,
) -> str:
    """构造完整 SQLAlchemy URL（显式保留密码，供 SQLAlchemy 解析）。"""
    return URL.create(
        drivername=drivername,
        username=username or None,
        password=password or None,
        host=host or None,
        port=port or None,
        database=database or None,
        query=query or {},
    ).render_as_string(hide_password=False)


def build_redis_url(*, username: str, password: str, host: str, port: int, db: int) -> str:
    """构造 Redis URL；用户名/密码按 RFC 3986 百分号编码。"""
    auth = ""
    if username and password:
        auth = f"{quote(username, safe='')}:{quote(password, safe='')}@"
    elif password:
        auth = f":{quote(password, safe='')}@"
    elif username:
        auth = f"{quote(username, safe='')}@"
    return f"redis://{auth}{host}:{port}/{db}"
