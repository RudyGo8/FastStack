from pydantic import BaseModel, Field


class CacheMonitorSchema(BaseModel):
    """缓存监控信息模型"""

    command_stats: list[dict] = Field(default_factory=list, description="Redis命令统计信息")
    db_size: int = Field(default=0, description="Redis数据库中的Key总数")
    info: dict = Field(default_factory=dict, description="Redis服务器信息")


class CacheInfoSchema(BaseModel):
    """缓存对象信息模型"""

    cache_key: str = Field(..., description="缓存键名")
    cache_name: str = Field(..., description="缓存名称")
    cache_value: str | None = Field(default=None, description="缓存值")
    remark: str | None = Field(default=None, description="备注说明")


# ── Redis 通用键空间浏览（只读）───────────────────────────────────────


class RedisDatabaseSchema(BaseModel):
    """Redis 逻辑库（INFO keyspace 口径）"""

    db: int = Field(..., description="逻辑库序号")
    keys: int = Field(default=0, description="键数量")
    expires: int = Field(default=0, description="带过期时间的键数量")


class RedisKeyMetaSchema(BaseModel):
    """键元信息（扫描列表用）"""

    key: str = Field(..., description="键名")
    type: str = Field(default="none", description="Redis 类型：string/hash/list/set/zset/stream/none")
    ttl: int = Field(default=-1, description="剩余有效期（秒）：-1 永不过期，-2 键不存在")


class RedisKeyPageSchema(BaseModel):
    """键扫描分页结果（SCAN 游标）"""

    cursor: int = Field(default=0, description="下一页游标；0 表示已扫完")
    keys: list[RedisKeyMetaSchema] = Field(default_factory=list, description="本页键")
    scanned: int = Field(default=0, description="本页数量")


class RedisValueSchema(BaseModel):
    """单键详情（只读）"""

    key: str = Field(..., description="键名")
    type: str = Field(..., description="Redis 类型")
    ttl: int = Field(default=-1, description="剩余有效期（秒）")
    size: int | None = Field(default=None, description="占用字节（MEMORY USAGE，可能不可用）")
    value: object = Field(default=None, description="值（按类型给出：字符串/列表/映射）")
    truncated: bool = Field(default=False, description="是否因超长被截断")
    masked: bool = Field(default=False, description="敏感键的值是否已脱敏")
