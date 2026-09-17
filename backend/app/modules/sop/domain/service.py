from collections import defaultdict
from datetime import date, datetime, time, timedelta
from uuid import uuid4

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.modules.sop.domain.channels import (
    REPORT_CHANNEL_ALIASES,
    REPORT_CHANNELS,
    RETAINED_CHANNEL_NAMES,
    ROLLUP_CHANNELS,
    normalize_report_channel,
)
from app.modules.sop.domain.rules import validate_forecast
from app.modules.sop.domain.source_catalog import CORE_DOMAINS, SOURCE_CATALOG
from app.modules.sop.domain.source_database import is_source_database_configured
from app.modules.sop.models.db_sop import (
    SopActivationDaily,
    SopAuditLog,
    SopDataQualityIssue,
    SopForecastMonthly,
    SopMonthlyEvent,
    SopSalesDaily,
    SopSourceSnapshot,
    SopSpu,
    SopSpuMapping,
)
from app.modules.sop.schemas.sop import (
    SopChannelMonthlyActual,
    SopDataStatusResponse,
    SopDimensionOptionsResponse,
    SopFirstPhaseReportResponse,
    SopForecastCheck,
    SopForecastPoint,
    SopMonthlyActual,
    SopMonthlyEventInfo,
    SopProvenance,
    SopReportFilters,
    SopSourceStatus,
    SopSpuInfo,
    SopSpuListResponse,
)


def _spu_info(row: SopSpu) -> SopSpuInfo:
    return SopSpuInfo(
        spu_code=row.spu_code,
        spu_name=row.spu_name,
        product_line=row.product_line,
        brand=row.brand,
        category=row.category,
        lifecycle_stage=row.lifecycle_stage,
    )


def _month_key(value: date) -> str:
    return value.strftime("%Y-%m")


SUBMITTED_FORECAST_TYPES = ("sales_submission", "sales_reported", "submit")


def _prefer_channel_detail(rows):
    """明细渠道存在时舍弃旧版全渠道汇总行，避免事实被重复累计。"""
    detail_dates = {row.business_date for row in rows if str(row.channel or "").strip() not in ROLLUP_CHANNELS}
    return [row for row in rows if str(row.channel or "").strip() not in ROLLUP_CHANNELS or row.business_date not in detail_dates]


class SopService:
    def __init__(self, db: Session):
        self.db = db

    def list_spus(self, search: str = "", limit: int = 100) -> SopSpuListResponse:
        query = self.db.query(SopSpu).filter(
            SopSpu.is_active.is_(True),
            SopSpu.source_system != "seed-demo",
        )
        keyword = search.strip()
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    SopSpu.spu_code.like(pattern),
                    SopSpu.spu_name.like(pattern),
                    SopSpu.product_line.like(pattern),
                )
            )
        total = query.count()
        rows = query.order_by(SopSpu.spu_code.asc()).limit(min(max(limit, 1), 500)).all()
        return SopSpuListResponse(items=[_spu_info(row) for row in rows], total=total)

    def list_dimension_options(self, spu_code: str) -> SopDimensionOptionsResponse | None:
        canonical_code = spu_code.strip()
        exists = self.db.query(SopSpu.id).filter(SopSpu.spu_code == canonical_code).first()
        if not exists:
            return None

        regions: set[str] = set()
        channels: set[str] = set()
        for model in (SopSalesDaily, SopActivationDaily, SopForecastMonthly):
            rows = (
                self.db.query(model.region, model.channel)
                .filter(
                    model.spu_code == canonical_code,
                    model.source_system != "seed-demo",
                )
                .distinct()
                .all()
            )
            regions.update(row.region for row in rows if row.region)
            channels.update(normalize_report_channel(row.channel) for row in rows if row.channel and row.channel.strip() not in ROLLUP_CHANNELS)
        return SopDimensionOptionsResponse(
            regions=sorted(regions),
            channels=[name for name in REPORT_CHANNELS if name in channels],
        )

    def get_data_status(self) -> SopDataStatusResponse:
        latest_by_domain: dict[str, SopSourceSnapshot] = {}
        snapshots = self.db.query(SopSourceSnapshot).filter(SopSourceSnapshot.source_system != "seed-demo").order_by(SopSourceSnapshot.snapshot_at.desc(), SopSourceSnapshot.id.desc()).all()
        for snapshot in snapshots:
            latest_by_domain.setdefault(snapshot.domain, snapshot)

        sources: list[SopSourceStatus] = []
        ready_core = 0
        for definition in SOURCE_CATALOG:
            latest = latest_by_domain.get(definition.domain)
            ingestion_status = latest.status if latest else "not_started"
            if definition.domain in CORE_DOMAINS and ingestion_status == "completed":
                ready_core += 1
            sources.append(
                SopSourceStatus(
                    domain=definition.domain,
                    label=definition.label,
                    source_objects=list(definition.source_objects),
                    phase_scope=definition.phase_scope,
                    contract_status=definition.contract_status,
                    ingestion_status=ingestion_status,
                    latest_snapshot_at=latest.snapshot_at if latest else None,
                    max_business_date=latest.max_business_date if latest else None,
                    record_count=latest.record_count if latest else 0,
                    note=definition.note,
                )
            )

        if ready_core == len(CORE_DOMAINS):
            overall_status = "ready"
        elif snapshots:
            overall_status = "partial"
        else:
            overall_status = "not_started"

        issue_count = self.db.query(SopDataQualityIssue).filter(SopDataQualityIssue.status == "open").count()
        return SopDataStatusResponse(
            overall_status=overall_status,
            source_connection_configured=is_source_database_configured(),
            sources=sources,
            open_quality_issues=issue_count,
        )

    def build_first_phase_report(
        self,
        spu_code: str,
        as_of_date: date | None = None,
        region: str = "",
        channel: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> SopFirstPhaseReportResponse | None:
        canonical_code = spu_code.strip()
        spu = self.db.query(SopSpu).filter(SopSpu.spu_code == canonical_code).first()
        if not spu:
            return None

        cutoff = as_of_date or date.today()
        history_start = start_date or (cutoff - timedelta(days=370)).replace(day=1)
        history_end = min(end_date or cutoff, cutoff)
        if start_date and end_date and start_date > end_date:
            raise ValueError("开始月份不能晚于结束月份")
        forecast_end = cutoff + timedelta(days=370)

        selected_region = region.strip()
        selected_channel = channel.strip()

        sales_query = self.db.query(SopSalesDaily).filter(
            SopSalesDaily.spu_code == canonical_code,
            SopSalesDaily.source_system != "seed-demo",
            SopSalesDaily.business_date >= history_start,
            SopSalesDaily.business_date <= history_end,
        )
        activation_query = self.db.query(SopActivationDaily).filter(
            SopActivationDaily.spu_code == canonical_code,
            SopActivationDaily.source_system != "seed-demo",
            SopActivationDaily.business_date >= history_start,
            SopActivationDaily.business_date <= history_end,
        )
        forecast_query = self.db.query(SopForecastMonthly).filter(
            SopForecastMonthly.spu_code == canonical_code,
            SopForecastMonthly.source_system != "seed-demo",
            SopForecastMonthly.forecast_type.in_(SUBMITTED_FORECAST_TYPES),
            SopForecastMonthly.forecast_month >= (cutoff - timedelta(days=370)).replace(day=1),
            SopForecastMonthly.forecast_month <= forecast_end,
            SopForecastMonthly.snapshot_at < datetime.combine(cutoff + timedelta(days=1), time.min),
        )
        if selected_region:
            sales_query = sales_query.filter(SopSalesDaily.region == selected_region)
            activation_query = activation_query.filter(SopActivationDaily.region == selected_region)
            forecast_query = forecast_query.filter(SopForecastMonthly.region == selected_region)
        if selected_channel:

            def channel_filter(model):
                column = func.trim(func.coalesce(model.channel, ""))
                if selected_channel == "其他":
                    return column.notin_((*RETAINED_CHANNEL_NAMES, *ROLLUP_CHANNELS))
                aliases = REPORT_CHANNEL_ALIASES.get(normalize_report_channel(selected_channel))
                return column.in_(aliases) if aliases else column == selected_channel

            sales_query = sales_query.filter(channel_filter(SopSalesDaily))
            activation_query = activation_query.filter(channel_filter(SopActivationDaily))
            forecast_query = forecast_query.filter(channel_filter(SopForecastMonthly))

        sales_rows = _prefer_channel_detail(sales_query.order_by(SopSalesDaily.business_date.asc()).all())
        activation_rows = _prefer_channel_detail(activation_query.order_by(SopActivationDaily.business_date.asc()).all())
        forecast_candidates = forecast_query.order_by(SopForecastMonthly.forecast_month.asc()).all()
        latest_forecasts: dict[tuple[date, str, str], SopForecastMonthly] = {}
        for row in forecast_candidates:
            key = (row.forecast_month, row.region, row.channel)
            existing = latest_forecasts.get(key)
            if existing is None or (row.snapshot_at, row.id) > (existing.snapshot_at, existing.id):
                latest_forecasts[key] = row
        detail_forecast_grains = {(row.forecast_month, row.region) for row in latest_forecasts.values() if str(row.channel or "").strip() not in ROLLUP_CHANNELS}
        forecast_rows = sorted(
            (row for row in latest_forecasts.values() if str(row.channel or "").strip() not in ROLLUP_CHANNELS or (row.forecast_month, row.region) not in detail_forecast_grains),
            key=lambda row: (row.forecast_month, row.region, row.channel),
        )
        event_rows = (
            self.db.query(SopMonthlyEvent)
            .filter(
                SopMonthlyEvent.spu_code == canonical_code,
                SopMonthlyEvent.source_system != "seed-demo",
                SopMonthlyEvent.event_month >= history_start.replace(day=1),
                SopMonthlyEvent.event_month <= forecast_end,
            )
            .order_by(SopMonthlyEvent.event_month.asc())
            .all()
        )

        monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"outbound_qty": 0.0, "activation_qty": 0.0})
        scoped_sales: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        scoped_activations: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for row in sales_rows:
            period = _month_key(row.business_date)
            value = float(row.outbound_qty or 0)
            monthly[period]["outbound_qty"] += value
            scoped_sales[(row.region, row.channel)][period] += value
        for row in activation_rows:
            period = _month_key(row.business_date)
            value = float(row.activation_qty or 0)
            monthly[period]["activation_qty"] += value
            scoped_activations[(row.region, row.channel)][period] += value

        monthly_actuals = [SopMonthlyActual(period=period, **monthly[period]) for period in sorted(monthly)]
        channel_actuals = [
            SopChannelMonthlyActual(
                period=period,
                region=actual_region,
                channel=actual_channel,
                outbound_qty=scoped_sales.get((actual_region, actual_channel), {}).get(period, 0.0),
                activation_qty=scoped_activations.get((actual_region, actual_channel), {}).get(period, 0.0),
            )
            for actual_region, actual_channel, period in sorted(
                {(actual_region, actual_channel, period) for (actual_region, actual_channel), periods in scoped_sales.items() for period in periods}
                | {(actual_region, actual_channel, period) for (actual_region, actual_channel), periods in scoped_activations.items() for period in periods}
            )
        ]

        all_history = [point.activation_qty if point.activation_qty > 0 else point.outbound_qty for point in monthly_actuals]
        forecasts: list[SopForecastPoint] = []
        checks: list[SopForecastCheck] = []
        for row in forecast_rows:
            quantity = float(row.forecast_qty)
            forecasts.append(
                SopForecastPoint(
                    forecast_month=row.forecast_month,
                    region=row.region,
                    channel=row.channel,
                    forecast_type=row.forecast_type,
                    forecast_qty=quantity,
                    version=row.version,
                    source_table=row.source_table,
                    snapshot_at=row.snapshot_at,
                )
            )
            scoped_activation = scoped_activations.get((row.region, row.channel), {})
            scoped_sales_history = scoped_sales.get((row.region, row.channel), {})
            scoped = scoped_activation or scoped_sales_history
            history = [scoped[key] for key in sorted(scoped)] if scoped else all_history
            result = validate_forecast(quantity, history)
            checks.append(
                SopForecastCheck(
                    forecast_month=row.forecast_month,
                    region=row.region,
                    channel=row.channel,
                    forecast_qty=quantity,
                    **result,
                )
            )

        mapping_exists = (
            self.db.query(SopSpuMapping.id)
            .filter(
                SopSpuMapping.canonical_spu_code == canonical_code,
                SopSpuMapping.source_system != "seed-demo",
            )
            .first()
            is not None
        )
        available_domains = {"spu_mapping"} if mapping_exists else set()
        if sales_rows:
            available_domains.add("historical_sales")
        if activation_rows:
            available_domains.add("activation")
        if forecast_rows:
            available_domains.add("forecast")
        missing_domains = sorted(CORE_DOMAINS - available_domains)

        if not monthly_actuals and not forecasts:
            completeness_status = "not_ready"
        elif missing_domains:
            completeness_status = "partial"
        else:
            completeness_status = "complete"

        warnings = [f"核心数据域缺失：{domain}" for domain in missing_domains]
        if any(not check.evaluable for check in checks):
            warnings.append("部分预测因历史数据不足或输入无效，暂不能评分。")
        if not checks and forecast_rows:
            warnings.append("预测数据存在，但未生成有效校验结果。")

        # A complete batch watermark remains available even when the selected channel has no rows.
        batch_domains: dict[str, dict[str, datetime]] = defaultdict(dict)
        source_synced_at = None
        completed = (
            self.db.query(SopSourceSnapshot)
            .filter(
                SopSourceSnapshot.source_system == "BIG_DATA_DW",
                SopSourceSnapshot.status == "completed",
                SopSourceSnapshot.domain.in_(CORE_DOMAINS),
                SopSourceSnapshot.snapshot_at < datetime.combine(cutoff + timedelta(days=1), time.min),
            )
            .order_by(SopSourceSnapshot.snapshot_at.desc(), SopSourceSnapshot.id.desc())
            .limit(64)
            .all()
        )
        for item in completed:
            batch_domains[item.batch_id][item.domain] = item.snapshot_at
            if CORE_DOMAINS.issubset(batch_domains[item.batch_id]):
                source_synced_at = min(batch_domains[item.batch_id].values())
                break

        provenance = self._collect_provenance(sales_rows, activation_rows, forecast_rows)
        events = [SopMonthlyEventInfo(event_month=row.event_month, event=row.event_text) for row in event_rows]
        return SopFirstPhaseReportResponse(
            spu=_spu_info(spu),
            as_of_date=cutoff,
            source_synced_at=source_synced_at,
            filters=SopReportFilters(region=selected_region, channel=selected_channel),
            completeness_status=completeness_status,
            missing_domains=missing_domains,
            warnings=warnings,
            monthly_actuals=monthly_actuals,
            channel_actuals=channel_actuals,
            events=events,
            forecasts=forecasts,
            forecast_checks=checks,
            provenance=provenance,
        )

    @staticmethod
    def _collect_provenance(*row_groups) -> list[SopProvenance]:
        domain_by_model = {
            SopSalesDaily: "historical_sales",
            SopActivationDaily: "activation",
            SopForecastMonthly: "forecast",
        }
        seen: set[tuple] = set()
        result: list[SopProvenance] = []
        for rows in row_groups:
            for row in rows:
                key = (
                    type(row),
                    row.source_system,
                    row.source_table,
                    row.batch_id,
                    row.snapshot_at,
                )
                if key in seen:
                    continue
                seen.add(key)
                result.append(
                    SopProvenance(
                        domain=domain_by_model[type(row)],
                        source_system=row.source_system,
                        source_table=row.source_table,
                        batch_id=row.batch_id,
                        snapshot_at=row.snapshot_at,
                    )
                )
        return sorted(result, key=lambda item: (item.domain, item.source_table, item.snapshot_at))

    def write_audit(
        self,
        username: str,
        action: str,
        resource: str,
        result_status: str,
        details: dict | None = None,
    ) -> None:
        self.db.add(
            SopAuditLog(
                username=username,
                action=action,
                resource=resource,
                result_status=result_status,
                request_id=uuid4().hex,
                details_json=details or {},
            )
        )
        self.db.commit()
