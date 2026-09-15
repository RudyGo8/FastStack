import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.sop.database import Base
from app.modules.sop.domain.service import SopService
from app.modules.sop.domain.source_catalog import CORE_DOMAINS
from app.modules.sop.models.db_sop import (
    SopActivationDaily,
    SopForecastMonthly,
    SopSalesDaily,
    SopSourceSnapshot,
    SopSpu,
    SopSpuMapping,
)


class SopServiceTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def _add_core_snapshots(self):
        for domain in CORE_DOMAINS:
            self.db.add(
                SopSourceSnapshot(
                    domain=domain,
                    source_system="test_dw",
                    source_table=f"test_{domain}",
                    batch_id=f"batch_{domain}",
                    snapshot_at=datetime(2026, 9, 9, 2, 0),
                    max_business_date=date(2026, 9, 8),
                    record_count=3,
                    status="completed",
                )
            )

    def test_build_complete_first_phase_report(self):
        self.db.add(SopSpu(spu_code="C706", spu_name="样例产品"))
        self.db.add(
            SopSpuMapping(
                source_system="test_dw",
                source_spu_code="C706-source",
                canonical_spu_code="C706",
            )
        )
        for month, outbound, activation in (
            (6, 105, 100),
            (7, 115, 110),
            (8, 125, 120),
        ):
            snapshot_at = datetime(2026, 9, 9, 2, 0)
            self.db.add(
                SopSalesDaily(
                    spu_code="C706",
                    business_date=date(2026, month, 1),
                    outbound_qty=outbound,
                    source_system="test_dw",
                    source_table="sales_view",
                    batch_id="sales_20260909",
                    snapshot_at=snapshot_at,
                )
            )
            self.db.add(
                SopActivationDaily(
                    spu_code="C706",
                    business_date=date(2026, month, 1),
                    activation_qty=activation,
                    source_system="test_dw",
                    source_table="activation_view",
                    batch_id="activation_20260909",
                    snapshot_at=snapshot_at,
                )
            )
        self.db.add(
            SopForecastMonthly(
                spu_code="C706",
                forecast_month=date(2026, 10, 1),
                forecast_qty=200,
                source_system="test_dw",
                source_table="forecast_view",
                batch_id="forecast_20260909",
                snapshot_at=datetime(2026, 9, 9, 2, 0),
            )
        )
        self._add_core_snapshots()
        self.db.commit()

        service = SopService(self.db)
        report = service.build_first_phase_report("C706", date(2026, 9, 9))

        self.assertIsNotNone(report)
        self.assertEqual(report.completeness_status, "complete")
        self.assertEqual(report.missing_domains, [])
        self.assertEqual(len(report.monthly_actuals), 3)
        self.assertEqual(report.monthly_actuals[-1].activation_qty, 120)
        self.assertEqual(len(report.forecast_checks), 1)
        self.assertTrue(report.forecast_checks[0].evaluable)
        self.assertGreaterEqual(len(report.provenance), 3)
        self.assertEqual(service.get_data_status().overall_status, "ready")

    def test_report_does_not_invent_missing_data(self):
        self.db.add(SopSpu(spu_code="606", spu_name="无数据样例"))
        self.db.commit()

        report = SopService(self.db).build_first_phase_report("606", date(2026, 9, 9))

        self.assertEqual(report.completeness_status, "not_ready")
        self.assertEqual(report.monthly_actuals, [])
        self.assertEqual(report.forecasts, [])
        self.assertEqual(
            set(report.missing_domains),
            {"spu_mapping", "historical_sales", "activation", "forecast"},
        )
        self.assertEqual(
            set(report.warnings),
            {
                "核心数据域缺失：spu_mapping",
                "核心数据域缺失：historical_sales",
                "核心数据域缺失：activation",
                "核心数据域缺失：forecast",
            },
        )

    def test_dimensions_and_report_filters_use_imported_values(self):
        self.db.add(SopSpu(spu_code="C706", spu_name="筛选样例"))
        snapshot_at = datetime(2026, 9, 9, 2, 0)
        for region, quantity in (("CN", 100), ("EU", 250)):
            self.db.add(
                SopSalesDaily(
                    spu_code="C706",
                    business_date=date(2026, 8, 1),
                    region=region,
                    channel="Retail",
                    outbound_qty=quantity,
                    source_system="test_dw",
                    source_table="sales_view",
                    batch_id="sales_20260909",
                    snapshot_at=snapshot_at,
                )
            )
        self.db.commit()

        service = SopService(self.db)
        dimensions = service.list_dimension_options("C706")
        report = service.build_first_phase_report(
            "C706",
            date(2026, 9, 9),
            region="CN",
            channel="Retail",
        )

        self.assertEqual(dimensions.regions, ["CN", "EU"])
        self.assertEqual(dimensions.channels, ["Retail"])
        self.assertEqual(report.filters.region, "CN")
        self.assertEqual(report.filters.channel, "Retail")
        self.assertEqual(report.monthly_actuals[0].outbound_qty, 100)

    def test_report_excludes_seed_demo_facts_from_real_business_totals(self):
        self.db.add(SopSpu(spu_code="C706", spu_name="C706"))
        snapshot_at = datetime(2026, 9, 9, 2, 0)
        self.db.add_all(
            [
                SopSalesDaily(
                    spu_code="C706",
                    business_date=date(2026, 8, 1),
                    region="全球",
                    channel="全部渠道",
                    outbound_qty=128,
                    source_system="BIG_DATA_DW",
                    source_table="real_sales",
                    batch_id="real_batch",
                    snapshot_at=snapshot_at,
                ),
                SopSalesDaily(
                    spu_code="C706",
                    business_date=date(2026, 8, 1),
                    region="DEMO",
                    channel="演示渠道",
                    outbound_qty=9999,
                    source_system="seed-demo",
                    source_table="sop_demo_sales",
                    batch_id="demo_batch",
                    snapshot_at=snapshot_at,
                ),
                SopForecastMonthly(
                    spu_code="C706",
                    forecast_month=date(2026, 10, 1),
                    forecast_qty=200,
                    source_system="BIG_DATA_DW",
                    source_table="real_forecast",
                    batch_id="real_batch",
                    snapshot_at=snapshot_at,
                ),
                SopForecastMonthly(
                    spu_code="C706",
                    forecast_month=date(2026, 10, 1),
                    forecast_type="demo",
                    forecast_qty=9999,
                    source_system="seed-demo",
                    source_table="sop_demo_forecast",
                    batch_id="demo_batch",
                    snapshot_at=snapshot_at,
                ),
            ]
        )
        self.db.commit()

        service = SopService(self.db)
        dimensions = service.list_dimension_options("C706")
        report = service.build_first_phase_report("C706", date(2026, 9, 9))

        self.assertNotIn("DEMO", dimensions.regions)
        self.assertNotIn("演示渠道", dimensions.channels)
        self.assertIn("全球", dimensions.regions)
        self.assertIn("全部渠道", dimensions.channels)
        self.assertEqual(sum(item.outbound_qty for item in report.monthly_actuals), 128)
        self.assertEqual([item.forecast_qty for item in report.forecasts], [200])


if __name__ == "__main__":
    unittest.main()
