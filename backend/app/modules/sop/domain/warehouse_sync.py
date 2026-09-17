"""S&OP 数仓固定白名单查询与真实数仓同步服务 (基于 docs/sop数据清单.xlsx 与 big_data_dw)."""

from datetime import date, datetime
from threading import Lock

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.sop.domain.ingestion import SopIngestionService
from app.modules.sop.domain.snapshot_service import SopSnapshotService
from app.modules.sop.domain.source_database import get_source_engine, is_source_database_configured
from app.modules.sop.domain.warehouse_queries import (
    ACTIVATION_ETL_SQL,
    CHANNEL_ACTUALS_SYNC_SQL,
    FORECAST_MONTHLY_SQL,
    HISTORICAL_SALES_SQL,
    INVENTORY_STOCK_SQL,
)
from app.modules.sop.models.db_sop import SopActivationDaily, SopForecastMonthly, SopSalesDaily
from app.modules.sop.schemas.sop import (
    SopActivationImportRequest,
    SopActivationImportRow,
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

CHANNEL_SALES_SOURCE_TABLE = "dw_c_base_product_events+dw_c_sal_outstock"
CHANNEL_ACTIVATION_SOURCE_TABLE = "dw_a_device"
FORECAST_SOURCE_TABLE = "dwd_sales_forecast_import"
FORECAST_TYPE = "sales_reported"
FORECAST_VERSION = "2026_OFFICIAL"
_SYNC_LOCK = Lock()


class WarehouseSyncInProgress(RuntimeError):
    pass


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

    def sync_from_warehouse(self) -> dict:
        """一次仅允许一个完整同步批次，跨进程通过 MySQL 命名锁保证。"""
        if not _SYNC_LOCK.acquire(blocking=False):
            raise WarehouseSyncInProgress("已有数仓同步正在进行，请稍后刷新")
        lock_conn = None
        acquired = False
        try:
            bind = self.db.get_bind()
            if bind.dialect.name == "mysql":
                lock_conn = bind.connect()
                acquired = lock_conn.execute(text("SELECT GET_LOCK('sopfast_warehouse_sync', 0)")).scalar() == 1
                if not acquired:
                    raise WarehouseSyncInProgress("已有数仓同步正在进行，请稍后刷新")
            return self._sync_from_warehouse()
        finally:
            try:
                if lock_conn is not None:
                    if acquired:
                        lock_conn.execute(text("SELECT RELEASE_LOCK('sopfast_warehouse_sync')"))
                    lock_conn.close()
            finally:
                _SYNC_LOCK.release()

    def _sync_from_warehouse(self) -> dict:
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
                        forecast_type=FORECAST_TYPE,
                        forecast_qty=val,
                        region="全球",
                        channel=channel,
                        version=FORECAST_VERSION,
                    )
                )

            # 使用数据清单第 9 项的销售出库单部门链路，同时生成渠道出库与激活事实。
            channel_actual_rows = conn.execute(text(CHANNEL_ACTUALS_SYNC_SQL)).fetchall()
            sales_rows = [
                SopSalesImportRow(
                    spu_code=str(row[1]).strip(),
                    business_date=row[2],
                    region="全球",
                    channel=str(row[3] or "未归属渠道").strip(),
                    order_qty=float(row[4] or 0),
                    outbound_qty=float(row[4] or 0),
                )
                for row in channel_actual_rows
                if row[0] == "outbound" and row[1] and str(row[1]).strip() in unique_spus and row[2] and float(row[4] or 0) > 0
            ]

            activation_rows = [
                SopActivationImportRow(
                    spu_code=str(row[1]).strip(),
                    business_date=row[2],
                    region="全球",
                    channel=str(row[3] or "未归属渠道").strip(),
                    activation_qty=float(row[4] or 0),
                )
                for row in channel_actual_rows
                if row[0] == "activation" and row[1] and str(row[1]).strip() in unique_spus and row[2] and float(row[4] or 0) > 0
            ]

        if not unique_spus:
            raise RuntimeError("数仓没有有效 SPU，已保留上次成功同步的数据")

        try:
            ingestion = SopIngestionService(self.db, autocommit=False)
            spu_count = 0
            forecast_count = 0
            sales_count = 0
            activation_count = 0

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

            self.db.query(SopForecastMonthly).filter(
                SopForecastMonthly.source_system == "BIG_DATA_DW",
                SopForecastMonthly.source_table == FORECAST_SOURCE_TABLE,
                SopForecastMonthly.forecast_type == FORECAST_TYPE,
                SopForecastMonthly.version == FORECAST_VERSION,
            ).delete(synchronize_session=False)
            if forecast_rows:
                forecast_result = ingestion.import_forecasts(
                    SopForecastImportRequest(
                        meta=SopImportMeta(
                            source_system="BIG_DATA_DW",
                            source_table=FORECAST_SOURCE_TABLE,
                            batch_id=batch_id,
                            snapshot_at=now,
                        ),
                        rows=forecast_rows,
                    )
                )
                forecast_count = forecast_result.accepted

            # 渠道事实是全量快照口径：整体替换 BIG_DATA_DW 名下事实（含旧 JST 口径残留），
            # 同步后只保留出库事件这一种真实口径。
            self.db.query(SopSalesDaily).filter(
                SopSalesDaily.source_system == "BIG_DATA_DW",
            ).delete(synchronize_session=False)
            if sales_rows:
                sales_result = ingestion.import_sales(
                    SopSalesImportRequest(
                        meta=SopImportMeta(
                            source_system="BIG_DATA_DW",
                            source_table=CHANNEL_SALES_SOURCE_TABLE,
                            batch_id=batch_id,
                            snapshot_at=now,
                        ),
                        rows=sales_rows,
                    )
                )
                sales_count = sales_result.accepted

            self.db.query(SopActivationDaily).filter(
                SopActivationDaily.source_system == "BIG_DATA_DW",
            ).delete(synchronize_session=False)
            if activation_rows:
                activation_result = ingestion.import_activations(
                    SopActivationImportRequest(
                        meta=SopImportMeta(
                            source_system="BIG_DATA_DW",
                            source_table=CHANNEL_ACTIVATION_SOURCE_TABLE,
                            batch_id=batch_id,
                            snapshot_at=now,
                        ),
                        rows=activation_rows,
                    )
                )
                activation_count = activation_result.accepted

            # 同步完成后立即生成当天快照，避免报表接口继续命中同步前的旧快照。
            snapshot_result = SopSnapshotService(self.db, autocommit=False).generate_nightly_snapshots(
                as_of_date=date.today(),
                report_version=f"SNAP_{batch_id}",
            )

            self.db.commit()

            return {
                "spus_synced": spu_count,
                "forecasts_synced": forecast_count,
                "sales_synced": sales_count,
                "activations_synced": activation_count,
                "snapshots_generated": snapshot_result.generated_count,
                "snapshot_status": "ready",
            }
        except Exception:
            self.db.rollback()
            raise
