import sqlite3
import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.sop.database import Base
from app.modules.sop.domain.warehouse_queries import CHANNEL_ACTUALS_SYNC_SQL
from app.modules.sop.domain.warehouse_sync import WarehouseQueryService
from app.modules.sop.models.db_sop import (
    SopActivationDaily,
    SopForecastMonthly,
    SopReportSnapshot,
    SopSalesDaily,
    SopSourceSnapshot,
)


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class _SourceConnection:
    def __init__(self, forecast_value):
        self.forecast_value = forecast_value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, statement, _params=None):
        sql = str(statement)
        if "WITH channel_base" in sql:
            return _Rows(
                [
                    ("outbound", "C706", date(2026, 9, 1), "国内渠道", 128.0),
                    ("activation", "C706", date(2026, 9, 1), "国内渠道", 88.0),
                ]
            )
        if "dw_a_device" in sql:
            return _Rows([("C706", date(2026, 9, 1), 88.0, "国内渠道")])
        if "dw_c_base_product_events" in sql and "销售出库" in sql:
            return _Rows([("C706", date(2026, 9, 1), 128.0, "国内渠道")])
        if "SELECT DISTINCT spu" in sql:
            return _Rows([("C706", "骑行", "在售", "码表")])
        if "SELECT spu, channel" in sql:
            return _Rows([("C706", "全渠道", "26.09", self.forecast_value)])
        raise AssertionError(f"unexpected warehouse query: {sql}")


class _SourceEngine:
    def __init__(self, forecast_value):
        self.forecast_value = forecast_value

    def connect(self):
        return _SourceConnection(self.forecast_value)


class WarehouseDocumentDateTests(unittest.TestCase):
    def test_outbound_month_uses_document_date_instead_of_event_date(self):
        with sqlite3.connect(":memory:") as conn:
            conn.create_function("SUBSTRING_INDEX", 3, lambda value, delimiter, count: delimiter.join(value.split(delimiter)[count:]) if count < 0 else delimiter.join(value.split(delimiter)[:count]))
            conn.executescript("""
                ATTACH DATABASE ':memory:' AS big_data_dw;
                CREATE TABLE big_data_dw.dw_c_base_product_header (SN TEXT, active_at TEXT, passed INTEGER);
                CREATE TABLE big_data_dw.dw_c_base_product_events (SN TEXT, ID TEXT, events_name TEXT, material_id_1 INTEGER, events_date TEXT);
                CREATE TABLE big_data_dw.dw_c_base_material (material_id INTEGER, material_spu INTEGER);
                CREATE TABLE big_data_dw.dw_c_base_auxiliary_information (id INTEGER, name TEXT);
                CREATE TABLE big_data_dw.dw_c_sal_outstock (outstock_number TEXT, outstock_dept_id INTEGER, outstock_date TEXT);
                CREATE TABLE big_data_dw.dw_c_base_department (department_id INTEGER, department_relation_id_new INTEGER);
                CREATE TABLE big_data_dw.dw_c_base_department_relation_new (id INTEGER, department_two_name TEXT);
                CREATE TABLE big_data_dw.dw_a_device (device_sn TEXT, device_status INTEGER);
                CREATE TABLE dwd_sales_forecast_import (spu TEXT);
                INSERT INTO dwd_sales_forecast_import VALUES ('C706');
                INSERT INTO big_data_dw.dw_c_base_material VALUES (1,1);
                INSERT INTO big_data_dw.dw_c_base_auxiliary_information VALUES (1,'C706');
                INSERT INTO big_data_dw.dw_c_base_department VALUES (1,1);
                INSERT INTO big_data_dw.dw_c_base_department_relation_new VALUES (1,'国内渠道销售部');
                INSERT INTO big_data_dw.dw_c_base_product_header VALUES ('SN1','2026-09-05',1),('SN2','2026-09-05',1),('SN3',NULL,1);
                INSERT INTO big_data_dw.dw_c_base_product_events VALUES ('SN1','销售出库单DOC1','销售出库',1,'2026-08-31'),('SN2','销售出库单DOC2','销售出库',1,'2026-09-01'),('SN3','销售出库单MISSING','销售出库',1,'2026-09-01');
                INSERT INTO big_data_dw.dw_c_sal_outstock VALUES ('DOC1',1,'2026-09-01'),('DOC2',1,'2026-08-15');
                INSERT INTO big_data_dw.dw_a_device VALUES ('SN1',7),('SN2',7);
            """)
            rows = conn.execute(CHANNEL_ACTUALS_SYNC_SQL).fetchall()
            outbound = {(row[2], row[3]): row[4] for row in rows if row[0] == "outbound"}
            self.assertEqual(outbound, {("2026-08-15", "国内渠道"): 1, ("2026-09-01", "国内渠道"): 1})


class WarehouseSyncTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def _sync(self, forecast_value):
        with (
            patch(
                "app.modules.sop.domain.warehouse_sync.is_source_database_configured",
                return_value=True,
            ),
            patch(
                "app.modules.sop.domain.warehouse_sync.get_source_engine",
                return_value=_SourceEngine(forecast_value),
            ),
        ):
            return WarehouseQueryService(self.db).sync_from_warehouse()

    def test_sync_failure_does_not_publish_part_of_a_new_batch(self):
        self._sync(4200)
        old_batch = self.db.query(SopForecastMonthly).one().batch_id
        with patch("app.modules.sop.domain.warehouse_sync.SopSnapshotService.generate_nightly_snapshots", side_effect=RuntimeError("snapshot failure")):
            with self.assertRaisesRegex(RuntimeError, "snapshot failure"):
                self._sync(4600)
        self.db.expire_all()
        forecast = self.db.query(SopForecastMonthly).one()
        self.assertEqual(float(forecast.forecast_qty), 4200)
        self.assertEqual(forecast.batch_id, old_batch)
        self.assertEqual(self.db.query(SopSourceSnapshot).count(), 4)

    def test_sync_records_only_domains_that_were_actually_imported(self):
        result = self._sync(4200)

        snapshots = self.db.query(SopSourceSnapshot).all()
        self.assertEqual(
            {item.domain for item in snapshots},
            {"spu_mapping", "forecast", "historical_sales", "activation"},
        )
        self.assertEqual(
            {item.domain: item.record_count for item in snapshots},
            {
                "spu_mapping": 1,
                "forecast": 1,
                "historical_sales": 1,
                "activation": 1,
            },
        )
        self.assertEqual(result["spus_synced"], 1)
        self.assertEqual(result["forecasts_synced"], 1)
        self.assertEqual(result["sales_synced"], 1)
        self.assertEqual(result["activations_synced"], 1)
        self.assertEqual(result["snapshots_generated"], 1)
        self.assertEqual(self.db.query(SopReportSnapshot).count(), 1)
        sale = self.db.query(SopSalesDaily).one()
        self.assertEqual(sale.spu_code, "C706")
        self.assertEqual(sale.business_date, date(2026, 9, 1))
        self.assertEqual(float(sale.outbound_qty), 128.0)

    def test_sync_updates_existing_forecast_through_canonical_upsert(self):
        self._sync(4200)
        self.db.query(SopForecastMonthly).one().channel = "旧渠道"
        self.db.commit()
        result = self._sync(4600)

        forecasts = self.db.query(SopForecastMonthly).all()
        self.assertEqual(len(forecasts), 1)
        self.assertEqual(forecasts[0].channel, "全渠道")
        self.assertEqual(float(forecasts[0].forecast_qty), 4600)
        self.assertEqual(result["forecasts_synced"], 1)

    def test_sync_preserves_channels_for_outbound_and_activation_facts(self):
        self._sync(4200)

        sale = self.db.query(SopSalesDaily).one()
        activation = self.db.query(SopActivationDaily).one()
        self.assertEqual(sale.channel, "国内渠道")
        self.assertEqual(float(sale.outbound_qty), 128.0)
        self.assertEqual(activation.channel, "国内渠道")
        self.assertEqual(float(activation.activation_qty), 88.0)

    def test_sync_replaces_stale_channel_facts_instead_of_accumulating_them(self):
        self._sync(4200)
        self.db.query(SopSalesDaily).one().channel = "旧渠道"
        self.db.query(SopActivationDaily).one().channel = "旧渠道"
        self.db.commit()

        self._sync(4200)

        sales = self.db.query(SopSalesDaily).all()
        activations = self.db.query(SopActivationDaily).all()
        self.assertEqual([(row.channel, float(row.outbound_qty)) for row in sales], [("国内渠道", 128.0)])
        self.assertEqual(
            [(row.channel, float(row.activation_qty)) for row in activations],
            [("国内渠道", 88.0)],
        )


if __name__ == "__main__":
    unittest.main()
