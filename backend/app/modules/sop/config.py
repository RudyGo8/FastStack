"""
SOP 模块配置：沿用 SopAgent 的 os.getenv 风格，从脚手架 env 目录加载。
认证/跨域已由脚手架统一负责，此处只保留业务所需配置。
"""

import os

from dotenv import load_dotenv

from app.config.path_conf import ENV_DIR

load_dotenv(ENV_DIR / f".env.{os.getenv('ENVIRONMENT', 'dev')}", override=False)

# 模块总开关：关闭后 lifespan 不启动 MCP 监听/快照调度等后台任务
SOP_ENABLE = os.getenv("SOP_ENABLE", "true").lower() == "true"

# mysql（业务表，与脚手架系统表同库 sopfast_mysql）
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3309"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "sopfast_mysql")

# S&OP 公司数据仓库（必须使用独立只读账号；未配置时只展示待接入状态）
SOP_SOURCE_MYSQL_HOST = os.getenv("SOP_SOURCE_MYSQL_HOST", "")
SOP_SOURCE_MYSQL_PORT = int(os.getenv("SOP_SOURCE_MYSQL_PORT", "3306"))
SOP_SOURCE_MYSQL_DATABASE = os.getenv("SOP_SOURCE_MYSQL_DATABASE", "big_data_dw")
SOP_SOURCE_MYSQL_USERNAME = os.getenv("SOP_SOURCE_MYSQL_USERNAME", "")
SOP_SOURCE_MYSQL_PASSWORD = os.getenv("SOP_SOURCE_MYSQL_PASSWORD", "")

# redis（sop 栈 6381，业务缓存用 db2 与脚手架 db1 隔离）
REDIS_URL = os.getenv("SOP_REDIS_URL", "redis://localhost:6381/2")
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "sop_agent")
REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "300"))

# milvus
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19532")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "sop_embeddings")

# 通用模型
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
GRADE_MODEL = os.getenv("GRADE_MODEL", "qwen-plus")
# RAG辅助任务(改写/扩展/路由)用小模型,不配置则跟随MODEL
REWRITE_MODEL = os.getenv("REWRITE_MODEL", MODEL)
EXPAND_MODEL = os.getenv("EXPAND_MODEL", MODEL)
ROUTER_MODEL = os.getenv("ROUTER_MODEL") or REWRITE_MODEL
# 主模型失败时兜底
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "")
# 主模型思考模式(知识问答场景检索内容已锚定答案,默认关闭提速)
MAIN_MODEL_THINKING = os.getenv("MAIN_MODEL_THINKING", "false").lower() == "true"
# 评测裁判模型(独立家族,避免自我偏好)
EVAL_MODEL = os.getenv("EVAL_MODEL", GRADE_MODEL)

# 向量模型
EMBEDDER = os.getenv("EMBEDDER", "text-embedding-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))

# RAGAS 测评
RAGAS_API_KEY = os.getenv("RAGAS_API_KEY", ARK_API_KEY)
RAGAS_BASE_URL = os.getenv("RAGAS_BASE_URL", BASE_URL)
RAGAS_LLM_MODEL = os.getenv("RAGAS_LLM_MODEL") or EVAL_MODEL
RAGAS_EMBEDDING_MODEL = os.getenv("RAGAS_EMBEDDING_MODEL", EMBEDDER)

# merge
AUTO_MERGE_ENABLED = os.getenv("AUTO_MERGE_ENABLED", "true")
AUTO_MERGE_THRESHOLD = os.getenv("AUTO_MERGE_THRESHOLD", "2")
LEAF_RETRIEVE_LEVEL = os.getenv("LEAF_RETRIEVE_LEVEL", "3")

# mcp权限
MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() == "true"

# 循环限制
AGENT_RECURSION_LIMIT = max(8, int(os.getenv("AGENT_RECURSION_LIMIT", "16")))
