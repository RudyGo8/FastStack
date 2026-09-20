from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.modules.system.log.model import LoginLogModel, OperationLogModel
from app.modules.system.notice.model import NoticeModel

from .schema import (
    DistributionItem,
    LoginStatisticsSchema,
    LoginTrendSchema,
    LoginTrendSeriesItem,
    OperationStatisticsSchema,
    StatisticsSchema,
)

# 请求方式 → 操作类型
OPERATION_TYPE_MAP = {"GET": "查询", "POST": "新增", "PUT": "修改", "PATCH": "更新", "DELETE": "删除"}

DISTRIBUTION_LIMIT = 10  # 分布统计最多返回条数
LOCATION_SERIES_LIMIT = 4  # 登录趋势最多展示的地区数


class DashboardService:
    """工作台统计服务"""

    @staticmethod
    def _week_start() -> datetime:
        """近 7 天起点（含今天共 7 天的零点）"""
        return datetime.combine(datetime.now().date() - timedelta(days=6), datetime.min.time())

    @staticmethod
    def _today_start() -> datetime:
        return datetime.combine(datetime.now().date(), datetime.min.time())

    @staticmethod
    def _login_scope(auth: AuthSchema) -> list:
        """数据范围：超管看全局，普通用户只看自己的登录记录"""
        base = [LoginLogModel.is_deleted.is_(False), LoginLogModel.status == 1]
        if not auth.user.is_superuser:
            base.append(LoginLogModel.username == auth.user.username)
        return base

    @staticmethod
    def _operation_scope(auth: AuthSchema) -> list:
        """数据范围：超管看全局，普通用户只看自己的操作记录"""
        base = [OperationLogModel.is_deleted.is_(False)]
        if not auth.user.is_superuser:
            base.append(OperationLogModel.username == auth.user.username)
        return base

    @staticmethod
    def _to_distribution(counter: Counter, empty_label: str) -> list[DistributionItem]:
        return [DistributionItem(name=name or empty_label, value=value) for name, value in counter.most_common(DISTRIBUTION_LIMIT)]

    @staticmethod
    def _normalize_location(raw: str | None) -> str:
        location = (raw or "").strip()
        return location.split(" ")[0] if location else ""

    @staticmethod
    def _date_labels(start: datetime) -> list[str]:
        base = start.date()
        return [(base + timedelta(days=offset)).isoformat() for offset in range(7)]

    @classmethod
    async def get_statistics(cls, db: AsyncSession, auth: AuthSchema) -> StatisticsSchema:
        """工作台统计卡片：通知公告 + 今日/近 7 天登录与操作次数"""
        today_start = cls._today_start()
        week_start = cls._week_start()

        login_base = cls._login_scope(auth)
        operation_base = cls._operation_scope(auth)

        async def count(model, base: list, start: datetime) -> int:
            sql = select(func.count()).select_from(model).where(*base, model.created_time >= start)
            return (await db.execute(sql)).scalar() or 0

        notice_total_sql = select(func.count()).select_from(NoticeModel).where(NoticeModel.is_deleted.is_(False))
        notice_published_sql = (
            select(func.count()).select_from(NoticeModel).where(NoticeModel.is_deleted.is_(False), NoticeModel.status == 1)
        )

        return StatisticsSchema(
            notice_published=(await db.execute(notice_published_sql)).scalar() or 0,
            notice_total=(await db.execute(notice_total_sql)).scalar() or 0,
            today_logins=await count(LoginLogModel, login_base, today_start),
            week_logins=await count(LoginLogModel, login_base, week_start),
            today_operations=await count(OperationLogModel, operation_base, today_start),
            week_operations=await count(OperationLogModel, operation_base, week_start),
        )

    @classmethod
    async def get_login_statistics(cls, db: AsyncSession, auth: AuthSchema) -> LoginStatisticsSchema:
        """近 7 天登录的操作系统 / 浏览器 / 地区分布"""
        sql = (
            select(LoginLogModel.request_os, LoginLogModel.request_browser, LoginLogModel.login_location)
            .where(*cls._login_scope(auth), LoginLogModel.created_time >= cls._week_start())
        )
        rows = (await db.execute(sql)).all()

        os_counter: Counter = Counter()
        browser_counter: Counter = Counter()
        location_counter: Counter = Counter()
        for row in rows:
            os_counter[row.request_os or ""] += 1
            browser_counter[row.request_browser or ""] += 1
            location_counter[cls._normalize_location(row.login_location)] += 1

        return LoginStatisticsSchema(
            os_distribution=cls._to_distribution(os_counter, "未知系统"),
            browser_distribution=cls._to_distribution(browser_counter, "未知浏览器"),
            location_distribution=cls._to_distribution(location_counter, "未知地区"),
        )

    @classmethod
    async def get_login_trend(cls, db: AsyncSession, auth: AuthSchema) -> LoginTrendSchema:
        """近 7 天登录趋势：每日总次数 + Top 地区每日系列"""
        week_start = cls._week_start()
        date_labels = cls._date_labels(week_start)

        sql = (
            select(LoginLogModel.created_time, LoginLogModel.login_location)
            .where(*cls._login_scope(auth), LoginLogModel.created_time >= week_start)
        )
        rows = (await db.execute(sql)).all()

        daily_counter: dict[str, int] = dict.fromkeys(date_labels, 0)
        location_counters: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(date_labels, 0))
        for row in rows:
            day = row.created_time.date().isoformat()
            if day not in daily_counter:
                continue
            daily_counter[day] += 1
            location_counters[cls._normalize_location(row.login_location)][day] += 1

        top_locations = sorted(
            ((name, sum(days.values())) for name, days in location_counters.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:LOCATION_SERIES_LIMIT]

        return LoginTrendSchema(
            dates=date_labels,
            login_counts=[daily_counter[day] for day in date_labels],
            location_series=[
                LoginTrendSeriesItem(name=name, data=[location_counters[name][day] for day in date_labels])
                for name, _ in top_locations
            ],
        )

    @classmethod
    async def get_operation_statistics(cls, db: AsyncSession, auth: AuthSchema) -> OperationStatisticsSchema:
        """近 7 天操作统计：类型分布 / 每日趋势 / 模块分布"""
        week_start = cls._week_start()
        date_labels = cls._date_labels(week_start)

        sql = (
            select(OperationLogModel.created_time, OperationLogModel.request_method, OperationLogModel.request_path)
            .where(*cls._operation_scope(auth), OperationLogModel.created_time >= week_start)
        )
        rows = (await db.execute(sql)).all()

        daily_counter: dict[str, int] = dict.fromkeys(date_labels, 0)
        type_counter: Counter = Counter()
        module_counter: Counter = Counter()
        for row in rows:
            day = row.created_time.date().isoformat()
            if day in daily_counter:
                daily_counter[day] += 1
            type_counter[OPERATION_TYPE_MAP.get(row.request_method.upper(), "其他")] += 1
            module_counter[cls._normalize_module(row.request_path)] += 1

        return OperationStatisticsSchema(
            dates=date_labels,
            type_distribution=cls._to_distribution(type_counter, "其他"),
            daily_trend=[daily_counter[day] for day in date_labels],
            module_distribution=cls._to_distribution(module_counter, "未知模块"),
        )

    @staticmethod
    def _normalize_module(request_path: str | None) -> str:
        """从请求路径提取功能模块名，如 /api/v1/system/user/list → user"""
        segments = [part for part in (request_path or "").strip("/").split("/") if part]
        # 跳过 api/v1 前缀
        while segments and segments[0] in ("api", "v1"):
            segments.pop(0)
        if not segments:
            return ""
        return segments[1] if len(segments) > 1 else segments[0]
