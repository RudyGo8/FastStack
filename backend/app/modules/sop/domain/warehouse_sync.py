"""S&OP 数仓固定白名单查询与真实数仓同步服务 (基于 docs/sop数据清单.xlsx 与 big_data_dw)."""

from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.sop.domain.ingestion import SopIngestionService
from app.modules.sop.domain.source_database import get_source_engine, is_source_database_configured
from app.modules.sop.domain.warehouse_queries import (
    ACTIVATION_ETL_SQL,
    FORECAST_MONTHLY_SQL,
    HISTORICAL_SALES_SQL,
    HISTORICAL_SALES_SYNC_SQL,
    INVENTORY_STOCK_SQL,
)
from app.modules.sop.schemas.sop import (
    SopForecastImportRequest,
    SopForecastImportRow,
    SopImportMeta,
    SopSalesImportRequest,
    SopSalesImportRow,
    SopSpuImportRequest,
    SopSpuImportRow,
)
from app.modules.sop.utils.log import get_logger

logger = get_logger(__name__)


class WarehouseQueryService:
    """数仓只读白名单查询与同步网关."""

    def __init__(self, db: Session):
        self.db = db

    def execute_activation_query(self, spu_code: str) -> list[dict]:
        """执行激活数据数仓抽取 SQL (良发数仓大 SQL)."""
        if not is_source_database_configured():
            logger.warning("source_db_not_configured_for_activation_query")
            return []

        engine = get_source_engine()
        with engine.connect() as conn:
            result = conn.execute(text(ACTIVATION_ETL_SQL), {"spu_code": spu_code})
            return [dict(row._mapping) for row in result]

    def execute_sales_query(self, spu_code: str, start_date: date, end_date: date) -> list[dict]:
        """执行历史出库数仓查询 SQL."""
        if not is_source_database_configured():
            return []

        engine = get_source_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(HISTORICAL_SALES_SQL),
                {"spu_code": spu_code, "start_date": start_date, "end_date": end_date},
            )
            return [dict(row._mapping) for row in result]

    def execute_forecast_query(self, spu_code: str, start_month: date) -> list[dict]:
        """执行预测数仓查询 SQL."""
        if not is_source_database_configured():
            return []

        engine = get_source_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(FORECAST_MONTHLY_SQL),
                {"spu_code": spu_code, "start_month": start_month},
            )
            return [dict(row._mapping) for row in result]

    def execute_inventory_query(self, spu_code: str) -> list[dict]:
        """执行库存与在途数仓查询 SQL."""
        if not is_source_database_configured():
            return []

        engine = get_source_engine()
        with engine.connect() as conn:
            result = conn.execute(text(INVENTORY_STOCK_SQL), {"spu_code": spu_code})
            return [dict(row._mapping) for row in result]

    def sync_from_warehouse(self) -> dict[str, int]:
        """从真实数仓 (big_data_dw) 同步 SPU 主数据、预测事实与出库快照."""
        if not is_source_database_configured():
            raise RuntimeError("数仓未配置或无法连接")

        engine = get_source_engine()
        now = datetime.now()
        batch_id = f"sync_{now.strftime('%Y%m%d_%H%M%S_%f')}"

        with engine.connect() as conn:
            spu_sql = """
                SELECT DISTINCT spu, product_line, stage, bu
                FROM dwd_sales_forecast_import
                WHERE spu IS NOT NULL AND spu != ''
            """
            spu_rows = conn.execute(text(spu_sql)).fetchall()
            unique_spus: dict[str, SopSpuImportRow] = {}
            for r in spu_rows:
                code = str(r[0]).strip()
                if not code or code in unique_spus:
                    continue
                stage = str(r[2] or "在售").strip()
                unique_spus[code] = SopSpuImportRow(
                    spu_code=code,
                    source_spu_code=code,
                    spu_name=code,
                    product_line=str(r[1] or "智能硬件").strip(),
                    brand="Magene",
                    category=str(r[3] or "码表").strip(),
                    lifecycle_stage="成长期" if "在售" in stage else stage,
                    mapping_type="direct",
                    mapping_version="warehouse-sync-v1",
                )

            fc_sql = """
                SELECT spu, channel, forecast_month, forecast_value
                FROM dwd_sales_forecast_import
                WHERE forecast_value > 0
            """
            fc_rows = conn.execute(text(fc_sql)).fetchall()
            forecast_rows: list[SopForecastImportRow] = []
            for r in fc_rows:
                spu_code = str(r[0]).strip()
                if not spu_code or spu_code not in unique_spus:
                    continue
                channel = str(r[1] or "全渠道").strip()
                m_str = str(r[2]).strip()
                val = float(r[3] or 0)

                try:
                    parts = m_str.split(".")
                    if len(parts) == 2:
                        y = 2000 + int(parts[0])
                        m = int(parts[1])
                        fmonth = date(y, m, 1)
                    else:
                        continue
                except Exception:
                    continue

                forecast_rows.append(
                    SopForecastImportRow(
                        spu_code=spu_code,
                        forecast_month=fmonth,
                        forecast_type="sales_reported",
                        forecast_qty=val,
                        region="全球",
                        channel=channel,
                        version="2026_OFFICIAL",
                    )
                )

            sales_source_rows = conn.execute(text(HISTORICAL_SALES_SYNC_SQL)).fetchall()
            sales_rows = [
                SopSalesImportRow(
                    spu_code=str(row[0]).strip(),
                    business_date=row[1],
                    region="全球",
                    channel="全部渠道",
                    order_qty=float(row[2] or 0),
                    outbound_qty=float(row[2] or 0),
                )
                for row in sales_source_rows
                if row[0] and row[1] and float(row[2] or 0) >= 0
            ]

        ingestion = SopIngestionService(self.db)
        spu_count = 0
        forecast_count = 0
        sales_count = 0
        if unique_spus:
            spu_result = ingestion.import_spus(
                SopSpuImportRequest(
                    meta=SopImportMeta(
                        source_system="BIG_DATA_DW",
                        source_table="dwd_sales_forecast_import",
                        batch_id=batch_id,
                        snapshot_at=now,
                    ),
                    rows=list(unique_spus.values()),
                )
            )
            spu_count = spu_result.accepted

        if forecast_rows:
            forecast_result = ingestion.import_forecasts(
                SopForecastImportRequest(
                    meta=SopImportMeta(
                        source_system="BIG_DATA_DW",
                        source_table="dwd_sales_forecast_import",
                        batch_id=batch_id,
                        snapshot_at=now,
                    ),
                    rows=forecast_rows,
                )
            )
            forecast_count = forecast_result.accepted

        if sales_rows:
            sales_result = ingestion.import_sales(
                SopSalesImportRequest(
                    meta=SopImportMeta(
                        source_system="BIG_DATA_DW",
                        source_table="dw_c_sal_predict_jst_order",
                        batch_id=batch_id,
                        snapshot_at=now,
                    ),
                    rows=sales_rows,
                )
            )
            sales_count = sales_result.accepted

        return {
            "spus_synced": spu_count,
            "forecasts_synced": forecast_count,
            "sales_synced": sales_count,
            "snapshot_status": "ready",
        }
