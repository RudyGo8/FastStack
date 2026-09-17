"""Normalized ingestion boundary for approved upstream ETL jobs.

The raw warehouse schemas are intentionally kept outside the application. An
approved adapter maps each source into these contracts before calling this
service. Unknown SPUs are rejected into the quality issue table, never dropped.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.modules.sop.models.db_sop import (
    SopActivationDaily,
    SopDataQualityIssue,
    SopForecastMonthly,
    SopMonthlyEvent,
    SopSalesDaily,
    SopSourceSnapshot,
    SopSpu,
    SopSpuMapping,
)
from app.modules.sop.schemas.sop import (
    SopActivationImportRequest,
    SopEventImportRequest,
    SopForecastImportRequest,
    SopImportMeta,
    SopImportResponse,
    SopSalesImportRequest,
    SopSpuImportRequest,
)


def _clean_dimension(value: str) -> str:
    return value.strip() or "ALL"


class SopIngestionService:
    def __init__(self, db: Session, *, autocommit: bool = True):
        self.db = db
        self.autocommit = autocommit

    def import_spus(self, payload: SopSpuImportRequest) -> SopImportResponse:
        try:
            for item in payload.rows:
                code = item.spu_code.strip()
                existing = self.db.query(SopSpu).filter(SopSpu.spu_code == code).first()
                values = {
                    "spu_name": item.spu_name.strip(),
                    "product_line": item.product_line.strip(),
                    "brand": item.brand.strip(),
                    "category": item.category.strip(),
                    "lifecycle_stage": item.lifecycle_stage.strip() or "unknown",
                    "predecessor_spu_code": item.predecessor_spu_code,
                    "successor_spu_code": item.successor_spu_code,
                    "source_system": payload.meta.source_system,
                    "source_updated_at": payload.meta.snapshot_at,
                    "is_active": True,
                }
                if existing:
                    for key, value in values.items():
                        setattr(existing, key, value)
                else:
                    self.db.add(SopSpu(spu_code=code, **values))

                source_code = (item.source_spu_code or code).strip()
                mapping = (
                    self.db.query(SopSpuMapping)
                    .filter(
                        SopSpuMapping.source_system == payload.meta.source_system,
                        SopSpuMapping.source_spu_code == source_code,
                    )
                    .first()
                )
                mapping_values = {
                    "canonical_spu_code": code,
                    "mapping_type": item.mapping_type.strip() or "direct",
                    "mapping_version": item.mapping_version.strip() or "draft",
                }
                if mapping:
                    for key, value in mapping_values.items():
                        setattr(mapping, key, value)
                else:
                    self.db.add(
                        SopSpuMapping(
                            source_system=payload.meta.source_system,
                            source_spu_code=source_code,
                            **mapping_values,
                        )
                    )

            self._record_snapshot(
                domain="spu_mapping",
                meta=payload.meta,
                record_count=len(payload.rows),
                status="completed",
            )
            self.db.commit() if self.autocommit else self.db.flush()
            return SopImportResponse(
                domain="spu_mapping",
                batch_id=payload.meta.batch_id,
                accepted=len(payload.rows),
                rejected=0,
                status="completed",
            )
        except Exception:
            self.db.rollback()
            raise

    def import_sales(self, payload: SopSalesImportRequest) -> SopImportResponse:
        known = self._known_spus(item.spu_code for item in payload.rows)
        accepted = 0
        issue_ids: list[int] = []
        try:
            for item in payload.rows:
                code = item.spu_code.strip()
                if code not in known:
                    issue_ids.append(self._unknown_spu_issue("historical_sales", payload.meta, code))
                    continue
                filters = {
                    "spu_code": code,
                    "business_date": item.business_date,
                    "region": _clean_dimension(item.region),
                    "channel": _clean_dimension(item.channel),
                    "source_table": payload.meta.source_table,
                }
                existing = self.db.query(SopSalesDaily).filter_by(**filters).first()
                values = {
                    **filters,
                    "order_qty": item.order_qty,
                    "outbound_qty": item.outbound_qty,
                    "source_system": payload.meta.source_system,
                    "batch_id": payload.meta.batch_id,
                    "snapshot_at": payload.meta.snapshot_at,
                }
                if existing:
                    for key, value in values.items():
                        setattr(existing, key, value)
                else:
                    self.db.add(SopSalesDaily(**values))
                accepted += 1
            return self._finish_fact_import(
                "historical_sales",
                payload.meta,
                accepted,
                len(payload.rows),
                issue_ids,
                max((item.business_date for item in payload.rows), default=None),
            )
        except Exception:
            self.db.rollback()
            raise

    def import_activations(self, payload: SopActivationImportRequest) -> SopImportResponse:
        known = self._known_spus(item.spu_code for item in payload.rows)
        accepted = 0
        issue_ids: list[int] = []
        try:
            for item in payload.rows:
                code = item.spu_code.strip()
                if code not in known:
                    issue_ids.append(self._unknown_spu_issue("activation", payload.meta, code))
                    continue
                filters = {
                    "spu_code": code,
                    "business_date": item.business_date,
                    "region": _clean_dimension(item.region),
                    "channel": _clean_dimension(item.channel),
                    "source_table": payload.meta.source_table,
                }
                existing = self.db.query(SopActivationDaily).filter_by(**filters).first()
                values = {
                    **filters,
                    "activation_qty": item.activation_qty,
                    "source_system": payload.meta.source_system,
                    "batch_id": payload.meta.batch_id,
                    "snapshot_at": payload.meta.snapshot_at,
                }
                if existing:
                    for key, value in values.items():
                        setattr(existing, key, value)
                else:
                    self.db.add(SopActivationDaily(**values))
                accepted += 1
            return self._finish_fact_import(
                "activation",
                payload.meta,
                accepted,
                len(payload.rows),
                issue_ids,
                max((item.business_date for item in payload.rows), default=None),
            )
        except Exception:
            self.db.rollback()
            raise

    def import_forecasts(self, payload: SopForecastImportRequest) -> SopImportResponse:
        known = self._known_spus(item.spu_code for item in payload.rows)
        accepted = 0
        issue_ids: list[int] = []
        try:
            for item in payload.rows:
                code = item.spu_code.strip()
                if code not in known:
                    issue_ids.append(self._unknown_spu_issue("forecast", payload.meta, code))
                    continue
                month = item.forecast_month.replace(day=1)
                filters = {
                    "spu_code": code,
                    "forecast_month": month,
                    "region": _clean_dimension(item.region),
                    "channel": _clean_dimension(item.channel),
                    "forecast_type": item.forecast_type.strip() or "sales_submission",
                    "version": item.version.strip() or "current",
                }
                existing = self.db.query(SopForecastMonthly).filter_by(**filters).first()
                values = {
                    **filters,
                    "forecast_qty": item.forecast_qty,
                    "source_system": payload.meta.source_system,
                    "source_table": payload.meta.source_table,
                    "batch_id": payload.meta.batch_id,
                    "snapshot_at": payload.meta.snapshot_at,
                }
                if existing:
                    for key, value in values.items():
                        setattr(existing, key, value)
                else:
                    self.db.add(SopForecastMonthly(**values))
                accepted += 1
            return self._finish_fact_import(
                "forecast",
                payload.meta,
                accepted,
                len(payload.rows),
                issue_ids,
                max((item.forecast_month for item in payload.rows), default=None),
            )
        except Exception:
            self.db.rollback()
            raise

    def import_events(self, payload: SopEventImportRequest) -> SopImportResponse:
        """按 (spu_code, event_month) 粒度 upsert 月度发生事件。"""
        known = self._known_spus(item.spu_code for item in payload.rows)
        accepted = 0
        issue_ids: list[int] = []
        try:
            for item in payload.rows:
                code = item.spu_code.strip()
                if code not in known:
                    issue_ids.append(self._unknown_spu_issue("event", payload.meta, code))
                    continue
                month = item.event_month.replace(day=1)
                existing = self.db.query(SopMonthlyEvent).filter_by(spu_code=code, event_month=month).first()
                values = {
                    "spu_code": code,
                    "event_month": month,
                    "event_text": item.event.strip(),
                    "source_system": payload.meta.source_system,
                    "source_table": payload.meta.source_table,
                    "batch_id": payload.meta.batch_id,
                    "snapshot_at": payload.meta.snapshot_at,
                }
                if existing:
                    for key, value in values.items():
                        setattr(existing, key, value)
                else:
                    self.db.add(SopMonthlyEvent(**values))
                accepted += 1
            return self._finish_fact_import(
                "event",
                payload.meta,
                accepted,
                len(payload.rows),
                issue_ids,
                max((item.event_month for item in payload.rows), default=None),
            )
        except Exception:
            self.db.rollback()
            raise

    def _known_spus(self, codes) -> set[str]:
        normalized = {code.strip() for code in codes}
        if not normalized:
            return set()
        return {row[0] for row in self.db.query(SopSpu.spu_code).filter(SopSpu.spu_code.in_(normalized)).all()}

    def _unknown_spu_issue(self, domain: str, meta: SopImportMeta, spu_code: str) -> int:
        issue = SopDataQualityIssue(
            domain=domain,
            source_table=meta.source_table,
            batch_id=meta.batch_id,
            issue_type="unmapped_spu",
            severity="high",
            spu_code=spu_code,
            details="来源记录无法映射到 sop_spu_master，已拒绝进入事实表。",
        )
        self.db.add(issue)
        self.db.flush()
        return issue.id

    def _finish_fact_import(
        self,
        domain: str,
        meta: SopImportMeta,
        accepted: int,
        total: int,
        issue_ids: list[int],
        max_business_date: date | None,
    ) -> SopImportResponse:
        rejected = total - accepted
        status = "completed" if rejected == 0 else "partial" if accepted else "failed"
        self._record_snapshot(
            domain=domain,
            meta=meta,
            record_count=accepted,
            status=status,
            max_business_date=max_business_date,
            details={"rejected": rejected, "quality_issue_ids": issue_ids},
        )
        self.db.commit() if self.autocommit else self.db.flush()
        return SopImportResponse(
            domain=domain,
            batch_id=meta.batch_id,
            accepted=accepted,
            rejected=rejected,
            status=status,
            quality_issue_ids=issue_ids,
        )

    def _record_snapshot(
        self,
        domain: str,
        meta: SopImportMeta,
        record_count: int,
        status: str,
        max_business_date: date | None = None,
        details: dict | None = None,
    ) -> None:
        filters = {
            "domain": domain,
            "source_table": meta.source_table,
            "batch_id": meta.batch_id,
        }
        snapshot = self.db.query(SopSourceSnapshot).filter_by(**filters).first()
        values = {
            **filters,
            "source_system": meta.source_system,
            "snapshot_at": meta.snapshot_at,
            "max_business_date": max_business_date,
            "record_count": record_count,
            "status": status,
            "details_json": details or {},
        }
        if snapshot:
            for key, value in values.items():
                setattr(snapshot, key, value)
        else:
            self.db.add(SopSourceSnapshot(**values))
