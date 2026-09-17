"""S&OP 会前不可变数据快照服务 (Snapshot Service).

支持提前一天晚上（T-1）对全量活跃 SPU 固化生成不可变会议快照，
确保 S&OP 会议使用的口径一致、事实不可变、可溯源。
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.modules.sop.domain.service import SopService
from app.modules.sop.models.db_sop import SopReportSnapshot, SopSpu
from app.modules.sop.schemas.sop import (
    SopReportSnapshotDetail,
    SopReportSnapshotSummary,
    SopSnapshotGenerateResponse,
)
from app.modules.sop.utils.log import get_logger

logger = get_logger(__name__)


class SopSnapshotService:
    def __init__(self, db: Session, *, autocommit: bool = True):
        self.db = db
        self.autocommit = autocommit
        self.sop_service = SopService(db)

    def create_spu_snapshot(
        self,
        spu_code: str,
        as_of_date: date | None = None,
        report_version: str | None = None,
    ) -> SopReportSnapshot | None:
        """为单个 SPU 生成并持久化会前数据快照."""
        canonical_code = spu_code.strip()
        spu = self.db.query(SopSpu).filter(SopSpu.spu_code == canonical_code).first()
        if not spu:
            logger.warning("snapshot_spu_not_found", spu_code=canonical_code)
            return None

        # 默认截止日期为前一天 (T-1) 业务日期
        target_as_of = as_of_date or (date.today() - timedelta(days=1))
        version = report_version or f"SNAP_{target_as_of.strftime('%Y%m%d')}_T1"

        report = self.sop_service.build_first_phase_report(
            spu_code=canonical_code,
            as_of_date=target_as_of,
        )
        if not report:
            return None

        payload_dict = report.model_dump(mode="json")

        existing = (
            self.db.query(SopReportSnapshot)
            .filter(
                SopReportSnapshot.spu_code == canonical_code,
                SopReportSnapshot.as_of_date == target_as_of,
                SopReportSnapshot.report_version == version,
            )
            .first()
        )

        now = datetime.now()
        if existing:
            existing.completeness_status = report.completeness_status
            existing.payload_json = payload_dict
            existing.generated_at = now
            snapshot_obj = existing
        else:
            snapshot_obj = SopReportSnapshot(
                spu_code=canonical_code,
                as_of_date=target_as_of,
                report_version=version,
                completeness_status=report.completeness_status,
                payload_json=payload_dict,
                generated_at=now,
            )
            self.db.add(snapshot_obj)

        if self.autocommit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(snapshot_obj)
        return snapshot_obj

    def generate_nightly_snapshots(
        self,
        spu_code: str | None = None,
        as_of_date: date | None = None,
        report_version: str | None = None,
    ) -> SopSnapshotGenerateResponse:
        """批量对活跃 SPU 生成提前一天晚上（T-1）的不可变会前快照."""
        target_as_of = as_of_date or (date.today() - timedelta(days=1))
        version = report_version or f"SNAP_{target_as_of.strftime('%Y%m%d')}_T1"

        if spu_code:
            target_spus = [spu_code.strip()]
        else:
            active_rows = self.db.query(SopSpu.spu_code).filter(SopSpu.is_active.is_(True)).order_by(SopSpu.spu_code.asc()).all()
            target_spus = [row[0] for row in active_rows]

        generated_spus: list[str] = []
        for code in target_spus:
            snap = self.create_spu_snapshot(
                spu_code=code,
                as_of_date=target_as_of,
                report_version=version,
            )
            if snap:
                generated_spus.append(code)

        logger.info(
            "nightly_snapshots_generated",
            as_of_date=str(target_as_of),
            report_version=version,
            count=len(generated_spus),
        )

        return SopSnapshotGenerateResponse(
            status="success",
            message=f"已成功生成 {len(generated_spus)} 个 SPU 的会前数据快照（数据截至 {target_as_of}）",
            as_of_date=target_as_of,
            report_version=version,
            generated_count=len(generated_spus),
            spu_codes=generated_spus,
        )

    def list_snapshots(
        self,
        spu_code: str | None = None,
        as_of_date: date | None = None,
        limit: int = 100,
    ) -> list[SopReportSnapshotSummary]:
        """查询快照列表概要."""
        query = self.db.query(SopReportSnapshot)
        if spu_code:
            query = query.filter(SopReportSnapshot.spu_code == spu_code.strip())
        if as_of_date:
            query = query.filter(SopReportSnapshot.as_of_date == as_of_date)

        rows = (
            query.order_by(
                SopReportSnapshot.generated_at.desc(),
                SopReportSnapshot.id.desc(),
            )
            .limit(min(max(limit, 1), 500))
            .all()
        )

        summaries: list[SopReportSnapshotSummary] = []
        for row in rows:
            payload = row.payload_json or {}
            record_count = len(payload.get("monthly_actuals", [])) + len(payload.get("forecasts", []))
            summaries.append(
                SopReportSnapshotSummary(
                    id=row.id,
                    spu_code=row.spu_code,
                    as_of_date=row.as_of_date,
                    report_version=row.report_version,
                    completeness_status=row.completeness_status,
                    generated_at=row.generated_at,
                    record_count=record_count,
                )
            )
        return summaries

    def get_snapshot_by_id(self, snapshot_id: int) -> SopReportSnapshotDetail | None:
        """根据 ID 获取快照详情."""
        row = self.db.query(SopReportSnapshot).filter(SopReportSnapshot.id == snapshot_id).first()
        if not row:
            return None
        return SopReportSnapshotDetail(
            id=row.id,
            spu_code=row.spu_code,
            as_of_date=row.as_of_date,
            report_version=row.report_version,
            completeness_status=row.completeness_status,
            generated_at=row.generated_at,
            payload=row.payload_json or {},
        )

    def get_latest_snapshot(
        self,
        spu_code: str,
        as_of_date: date | None = None,
    ) -> SopReportSnapshotDetail | None:
        """获取指定 SPU 的最新快照详情."""
        query = self.db.query(SopReportSnapshot).filter(SopReportSnapshot.spu_code == spu_code.strip())
        if as_of_date:
            query = query.filter(SopReportSnapshot.as_of_date <= as_of_date)
        row = query.order_by(
            SopReportSnapshot.as_of_date.desc(),
            SopReportSnapshot.generated_at.desc(),
        ).first()
        if not row:
            return None
        return SopReportSnapshotDetail(
            id=row.id,
            spu_code=row.spu_code,
            as_of_date=row.as_of_date,
            report_version=row.report_version,
            completeness_status=row.completeness_status,
            generated_at=row.generated_at,
            payload=row.payload_json or {},
        )
