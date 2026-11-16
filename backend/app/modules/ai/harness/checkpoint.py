"""LangGraph PostgreSQL Checkpoint 生命周期。

运行期只做检查，schema 初始化必须由人工迁移命令显式调用——避免服务启动时
隐式建表/改表。仅支持 PostgreSQL；MySQL/SQLite 不提供持久任务体系。
"""

from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url

from app.config.setting import settings


def checkpoint_schema() -> str:
    return settings.AI_HARNESS_CHECKPOINT_SCHEMA


def application_conn_string() -> str:
    """复用应用数据库连接串；Checkpoint 与业务表同库、独立 schema。"""
    url = make_url(settings.DB_URI)
    if url.get_backend_name() != "postgresql":
        raise ValueError("持久任务 Checkpoint 仅支持应用 PostgreSQL")
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


async def check_checkpoint_schema(saver: AsyncPostgresSaver) -> None:
    schema = checkpoint_schema()
    async with saver.conn.cursor() as cursor:
        await cursor.execute(
            "SELECT to_regclass(%s) AS name", (f"{schema}.checkpoint_migrations",)
        )
        if (await cursor.fetchone())["name"] is None:
            raise RuntimeError("Agent Checkpoint schema 尚未显式初始化")
        await cursor.execute("SELECT max(v) AS version FROM checkpoint_migrations")
        if (await cursor.fetchone())["version"] != len(saver.MIGRATIONS) - 1:
            raise RuntimeError("Agent Checkpoint schema 版本不兼容，请显式迁移")
        for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
            await cursor.execute("SELECT to_regclass(%s) AS name", (f"{schema}.{table}",))
            if (await cursor.fetchone())["name"] is None:
                raise RuntimeError("Agent Checkpoint 表结构缺失")


@asynccontextmanager
async def open_checkpointer(conn_string: str | None = None):
    """与应用同库、独立连接；禁止在应用启动路径调用 setup。"""
    schema = checkpoint_schema()
    async with AsyncPostgresSaver.from_conn_string(conn_string or application_conn_string()) as saver:
        await saver.conn.execute(f"SET search_path TO {schema}")
        await check_checkpoint_schema(saver)
        yield saver


async def initialize_checkpoint_schema(conn_string: str | None = None) -> None:
    """仅供人工迁移命令显式调用；调用方负责核对目标与备份授权。"""
    schema = checkpoint_schema()
    target = conn_string or application_conn_string()
    async with await AsyncConnection.connect(target, autocommit=True, row_factory=dict_row) as conn:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    async with AsyncPostgresSaver.from_conn_string(target) as saver:
        await saver.conn.execute(f"SET search_path TO {schema}")
        await saver.setup()
        await check_checkpoint_schema(saver)
