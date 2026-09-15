import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.sop.database import Base
from app.modules.sop.domain.ingestion import SopIngestionService
from app.modules.sop.models.db_sop import SopDataQualityIssue, SopSalesDaily, SopSpuMapping
from app.modules.sop.schemas.sop import (
    SopImportMeta,
    SopSalesImportRequest,
    SopSalesImportRow,
    SopSpuImportRequest,
    SopSpuImportRow,
)


class SopIngestionTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.service = SopIngestionService(self.db)

    def tearDown(self):
        self.db.close()

    @staticmethod
    def meta(batch_id: str) -> SopImportMeta:
        return SopImportMeta(
            source_system="test_dw",
            source_table="approved_sales_view",
            batch_id=batch_id,
            snapshot_at=datetime(2026, 9, 9, 2, 0),
        )

    def test_unknown_spu_is_rejected_and_recorded(self):
        self.service.import_spus(
            SopSpuImportRequest(
                meta=self.meta("spu-1"),
                rows=[SopSpuImportRow(spu_code="C706", spu_name="样例")],
            )
        )
        response = self.service.import_sales(
            SopSalesImportRequest(
                meta=self.meta("sales-1"),
                rows=[
                    SopSalesImportRow(
                        spu_code="C706",
                        business_date=date(2026, 8, 1),
                        outbound_qty=100,
                    ),
                    SopSalesImportRow(
                        spu_code="UNKNOWN",
                        business_date=date(2026, 8, 1),
                        outbound_qty=50,
                    ),
                ],
            )
        )

        self.assertEqual(response.accepted, 1)
        self.assertEqual(response.rejected, 1)
        self.assertEqual(response.status, "partial")
        self.assertEqual(self.db.query(SopSpuMapping).count(), 1)
        self.assertEqual(self.db.query(SopSalesDaily).count(), 1)
        issue = self.db.query(SopDataQualityIssue).one()
        self.assertEqual(issue.issue_type, "unmapped_spu")
        self.assertEqual(issue.spu_code, "UNKNOWN")

    def test_new_snapshot_updates_same_business_grain(self):
        self.service.import_spus(
            SopSpuImportRequest(
                meta=self.meta("spu-1"),
                rows=[SopSpuImportRow(spu_code="606")],
            )
        )
        for batch, quantity in (("sales-1", 100), ("sales-2", 120)):
            self.service.import_sales(
                SopSalesImportRequest(
                    meta=self.meta(batch),
                    rows=[
                        SopSalesImportRow(
                            spu_code="606",
                            business_date=date(2026, 8, 1),
                            outbound_qty=quantity,
                        )
                    ],
                )
            )

        rows = self.db.query(SopSalesDaily).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0].outbound_qty), 120)
        self.assertEqual(rows[0].batch_id, "sales-2")


if __name__ == "__main__":
    unittest.main()
