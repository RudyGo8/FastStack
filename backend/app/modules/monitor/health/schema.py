from pydantic import BaseModel, Field


class ServiceInfoOut(BaseModel):
    """健康状态：应用进程元信息 + 服务器 / 数据库 / Redis 连通状态"""

    name: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本号")
    environment: str = Field(..., description="运行环境")
    db_status: int = Field(..., description="数据库状态(0:异常 1:正常)")
    redis_status: int = Field(..., description="Redis状态(0:异常 1:正常)")
    code_exec_enabled: bool = Field(
        default=False,
        description="定时任务是否允许执行用户提交的代码块(SCHEDULER_ALLOW_CODE_EXEC)；关闭时节点型的代码块任务不可调度",
    )
    cors_origins_configured: bool = Field(
        default=True,
        description="生产环境是否已显式配置 PROD_CORS_ORIGINS；false 表示生产已按安全默认拒绝全部跨域请求",
    )
