import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.sop.database import Base
from app.modules.sop.domain.warehouse_sync import WarehouseQueryService
from app.modules.sop.models.db_sop import SopForecastMonthly, SopSalesDaily, SopSourceSnapshot


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
        if "dw_c_sal_predict_jst_order" in sql:
            return _Rows([("C706", date(2026, 9, 1), 128.0)])
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

    def test_sync_records_only_domains_that_were_actually_imported(self):
        result = self._sync(4200)

        snapshots = self.db.query(SopSourceSnapshot).all()
        self.assertEqual(
            {item.domain for item in snapshots},
            {"spu_mapping", "forecast", "historical_sales"},
        )
        self.assertEqual(
            {item.domain: item.record_count for item in snapshots},
            {
                "spu_mapping": 1,
                "forecast": 1,
                "historical_sales": 1,
            },
        )
        self.assertEqual(result["spus_synced"], 1)
        self.assertEqual(result["forecasts_synced"], 1)
        self.assertEqual(result["sales_synced"], 1)
        sale = self.db.query(SopSalesDaily).one()
        self.assertEqual(sale.spu_code, "C706")
        self.assertEqual(sale.business_date, date(2026, 9, 1))
        self.assertEqual(float(sale.outbound_qty), 128.0)

    def test_sync_updates_existing_forecast_through_canonical_upsert(self):
        self._sync(4200)
        result = self._sync(4600)

        forecasts = self.db.query(SopForecastMonthly).all()
        self.assertEqual(len(forecasts), 1)
        self.assertEqual(float(forecasts[0].forecast_qty), 4600)
        self.assertEqual(result["forecasts_synced"], 1)


if __name__ == "__main__":
    unittest.main()
