from pydantic import BaseModel, Field


class DistributionItem(BaseModel):
    """分布统计项"""

    name: str
    value: int = 0


class StatisticsSchema(BaseModel):
    """工作台统计卡片数据"""

    notice_published: int = 0  # 已发布通知数
    notice_total: int = 0  # 全部通知数
    today_logins: int = 0  # 今日登录次数
    week_logins: int = 0  # 近 7 天登录次数
    today_operations: int = 0  # 今日操作次数
    week_operations: int = 0  # 近 7 天操作次数


class LoginStatisticsSchema(BaseModel):
    """登录统计数据（近 7 天）"""

    os_distribution: list[DistributionItem] = Field(default_factory=list, description="操作系统分布")
    browser_distribution: list[DistributionItem] = Field(default_factory=list, description="浏览器分布")
    location_distribution: list[DistributionItem] = Field(default_factory=list, description="登录地区分布")


class LoginTrendSeriesItem(BaseModel):
    """登录趋势单条系列"""

    name: str
    data: list[int] = Field(default_factory=list)


class LoginTrendSchema(BaseModel):
    """登录趋势数据（近 7 天，按日聚合）"""

    dates: list[str] = Field(default_factory=list, description="日期列表(YYYY-MM-DD)")
    login_counts: list[int] = Field(default_factory=list, description="每日登录总次数")
    location_series: list[LoginTrendSeriesItem] = Field(default_factory=list, description="Top 地区每日登录系列")


class OperationStatisticsSchema(BaseModel):
    """操作统计数据（近 7 天）"""

    dates: list[str] = Field(default_factory=list, description="日期列表(YYYY-MM-DD)")
    type_distribution: list[DistributionItem] = Field(default_factory=list, description="操作类型分布")
    daily_trend: list[int] = Field(default_factory=list, description="每日操作次数")
    module_distribution: list[DistributionItem] = Field(default_factory=list, description="模块分布")
