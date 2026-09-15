"""Read-only S&OP warehouse connection boundary.

Adapters may use this engine after their field contracts are approved. The
connection is deliberately separate from the application's writable database.
"""

from functools import lru_cache

from sqlalchemy import URL, create_engine

from app.modules.sop.config import (
    SOP_SOURCE_MYSQL_DATABASE,
    SOP_SOURCE_MYSQL_HOST,
    SOP_SOURCE_MYSQL_PASSWORD,
    SOP_SOURCE_MYSQL_PORT,
    SOP_SOURCE_MYSQL_USERNAME,
)


def is_source_database_configured() -> bool:
    return bool(SOP_SOURCE_MYSQL_HOST and SOP_SOURCE_MYSQL_DATABASE and SOP_SOURCE_MYSQL_USERNAME and SOP_SOURCE_MYSQL_PASSWORD)


@lru_cache(maxsize=1)
def get_source_engine():
    if not is_source_database_configured():
        raise RuntimeError("S&OP 数据仓库只读连接尚未配置")

    url = URL.create(
        drivername="mysql+pymysql",
        username=SOP_SOURCE_MYSQL_USERNAME,
        password=SOP_SOURCE_MYSQL_PASSWORD,
        host=SOP_SOURCE_MYSQL_HOST,
        port=SOP_SOURCE_MYSQL_PORT,
        database=SOP_SOURCE_MYSQL_DATABASE,
        query={"charset": "utf8mb4"},
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"read_timeout": 30, "write_timeout": 30},
    )
