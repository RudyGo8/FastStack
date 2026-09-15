import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.sop.database import Base
from app.modules.sop.domain.snapshot_service import SopSnapshotService
from app.modules.sop.models.db_sop import (
    SopActivationDaily,
    SopForecastMonthly,
    SopSalesDaily,
    SopSpu,
    SopSpuMapping,
)


class SopSnapshotServiceTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.service = SopSnapshotService(self.db)

        # 准备基础数据
        self.db.add(SopSpu(spu_code="C706", spu_name="GPS智能码表 C706", is_active=True))
        self.db.add(SopSpu(spu_code="C406", spu_name="GPS智能码表 C406", is_active=True))
        self.db.add(SopSpu(spu_code="INACTIVE_01", spu_name="已停用产品", is_active=False))

        self.db.add(
            SopSpuMapping(
                source_system="test_dw",
                source_spu_code="C706-SRC",
                canonical_spu_code="C706",
            )
        )
        self.db.add(
            SopSalesDaily(
                spu_code="C706",
                business_date=date(2026, 8, 1),
                outbound_qty=120,
                source_system="test_dw",
                source_table="sales_view",
                batch_id="sales_b1",
                snapshot_at=datetime(2026, 9, 1, 0, 0),
            )
        )
        self.db.add(
            SopActivationDaily(
                spu_code="C706",
                business_date=date(2026, 8, 1),
                activation_qty=110,
                source_system="test_dw",
                source_table="act_view",
                batch_id="act_b1",
                snapshot_at=datetime(2026, 9, 1, 0, 0),
            )
        )
        self.db.add(
            SopForecastMonthly(
                spu_code="C706",
                forecast_month=date(2026, 9, 1),
                forecast_qty=130,
                source_system="test_dw",
                source_table="fc_view",
                batch_id="fc_b1",
                snapshot_at=datetime(2026, 9, 1, 0, 0),
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_create_spu_snapshot_with_default_t1(self):
        """测试生成单个 SPU 快照，默认采用 T-1 业务日期."""
        yesterday = date.today() - timedelta(days=1)
        snapshot = self.service.create_spu_snapshot(spu_code="C706")

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.spu_code, "C706")
        self.assertEqual(snapshot.as_of_date, yesterday)
        self.assertTrue(snapshot.report_version.startswith(f"SNAP_{yesterday.strftime('%Y%m%d')}_T1"))
        self.assertIn("monthly_actuals", snapshot.payload_json)
        self.assertIn("forecasts", snapshot.payload_json)

    def test_generate_nightly_snapshots_for_active_spus_only(self):
        """测试夜间自动批量快照只为活跃 SPU 生成快照."""
        target_date = date(2026, 9, 10)
        res = self.service.generate_nightly_snapshots(
            as_of_date=target_date,
            report_version="SNAP_20260910_NIGHTLY",
        )

        self.assertEqual(res.status, "success")
        self.assertEqual(res.as_of_date, target_date)
        self.assertEqual(res.generated_count, 2)
        self.assertIn("C706", res.spu_codes)
        self.assertIn("C406", res.spu_codes)
        self.assertNotIn("INACTIVE_01", res.spu_codes)

        # 检查持久化快照列表
        snapshots = self.service.list_snapshots(as_of_date=target_date)
        self.assertEqual(len(snapshots), 2)

    def test_get_latest_snapshot(self):
        """测试获取最新快照详情."""
        d1 = date(2026, 9, 8)
        d2 = date(2026, 9, 10)
        self.service.create_spu_snapshot("C706", as_of_date=d1, report_version="SNAP_20260908")
        self.service.create_spu_snapshot("C706", as_of_date=d2, report_version="SNAP_20260910")

        latest = self.service.get_latest_snapshot("C706")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.as_of_date, d2)
        self.assertEqual(latest.report_version, "SNAP_20260910")
        self.assertEqual(latest.payload["spu"]["spu_code"], "C706")
