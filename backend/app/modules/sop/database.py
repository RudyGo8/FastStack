"""
SOP 模块同步数据库引擎：业务代码保留 SopAgent 的同步 SQLAlchemy 访问方式，
指向与脚手架异步引擎相同的 sopfast_mysql 库。
"""

import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.modules.sop.config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USERNAME
from app.modules.sop.utils.log import get_logger

logger = get_logger(__name__)
pymysql.install_as_MySQLdb()

SQLALCHEMY_DATABASE_URL = f"mysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    pool_size=10,
    pool_recycle=3600,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库模型元数据与连接预热。

    架构治理要求：不再在应用启动时隐式调用 create_all 进行数据库迁移，
    统一通过 Alembic 执行版本化迁移（如 `alembic upgrade head`）。
    """
    try:
        # Import all models before metadata initialization so SQLAlchemy can
        # resolve relationship() string targets consistently.
        import app.modules.sop.models  # noqa: F401

        logger.info("database_metadata_initialized")
    except Exception:
        logger.exception("database_init_failed")
        raise


def init_sop_tables() -> None:
    """在 sopfast_mysql 库中创建 SOP 业务表（幂等，供应用启动时调用）。"""
    init_db()
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("sop_tables_ready")
