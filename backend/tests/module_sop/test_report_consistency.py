import json
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common.enums import RET
from app.modules.sop.data.controller import sync_warehouse
from app.modules.sop.database import Base
from app.modules.sop.domain.service import SopService
from app.modules.sop.domain.snapshot_service import SopSnapshotService
from app.modules.sop.models.db_sop import SopSalesDaily, SopSpu
from app.modules.sop.report.controller import get_first_phase_report, refresh_report_data


class ReportConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add(SopSpu(spu_code="C416", spu_name="C416"))
        self.sale = SopSalesDaily(
            spu_code="C416",
            business_date=date(2026, 9, 1),
            region="全球",
            channel="国内渠道",
            outbound_qty=10,
            source_system="test_dw",
            source_table="sale",
            batch_id="b",
            snapshot_at=datetime(2026, 9, 17),
        )
        self.db.add(self.sale)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_sync_endpoint_uses_the_standard_success_envelope(self):
        auth = SimpleNamespace(user=SimpleNamespace(username="audit"))
        with patch("app.modules.sop.data.controller.WarehouseQueryService.sync_from_warehouse", return_value={"sales_synced": 1}):
            response = sync_warehouse(auth, self.db)
        self.assertTrue(hasattr(response, "body"), "同步响应必须使用标准 JSON 响应封装")
        payload = json.loads(response.body)
        self.assertEqual(payload["code"], RET.OK.code)
        self.assertEqual(payload["data"]["sales_synced"], 1)

    def test_report_refresh_endpoint_has_the_same_success_envelope(self):
        auth = SimpleNamespace(user=SimpleNamespace(username="audit"))
        with patch("app.modules.sop.report.controller.WarehouseQueryService.sync_from_warehouse", return_value={"sales_synced": 1}):
            payload = json.loads(refresh_report_data(auth, self.db).body)
        self.assertEqual(payload["code"], RET.OK.code)
        self.assertEqual(payload["data"]["sales_synced"], 1)

    def test_default_and_equivalent_region_use_the_same_updated_facts(self):
        SopSnapshotService(self.db).create_spu_snapshot("C416", date(2026, 9, 17))
        self.sale.outbound_qty = 20
        self.db.commit()
        auth = SimpleNamespace(user=SimpleNamespace(username="audit"))
        all_report = json.loads(get_first_phase_report(auth, self.db, "C416", date(2026, 9, 17), "", "").body)["data"]
        global_report = json.loads(get_first_phase_report(auth, self.db, "C416", date(2026, 9, 17), "全球", "").body)["data"]
        self.assertEqual(sum(x["outbound_qty"] for x in all_report["monthly_actuals"]), 20)
        self.assertEqual(all_report["monthly_actuals"], global_report["monthly_actuals"])

    def test_explicit_period_returns_old_facts_without_partial_month_cutoff(self):
        self.sale.business_date = date(2024, 1, 1)
        self.db.commit()
        report = SopService(self.db).build_first_phase_report("C416", date(2026, 9, 17), start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
        self.assertEqual(sum(x.outbound_qty for x in report.monthly_actuals), 10)


if __name__ == "__main__":
    unittest.main()
