from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class SopSpuInfo(BaseModel):
    spu_code: str
    spu_name: str = ""
    product_line: str = ""
    brand: str = ""
    category: str = ""
    lifecycle_stage: str = "unknown"


class SopSpuListResponse(BaseModel):
    items: list[SopSpuInfo]
    total: int


class SopDimensionOptionsResponse(BaseModel):
    regions: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)


class SopReportFilters(BaseModel):
    region: str = ""
    channel: str = ""


class SopSourceStatus(BaseModel):
    domain: str
    label: str
    source_objects: list[str]
    phase_scope: Literal["phase_one_core", "phase_one_extension", "connection_only"]
    contract_status: str
    ingestion_status: str
    latest_snapshot_at: datetime | None = None
    max_business_date: date | None = None
    record_count: int = 0
    note: str = ""


class SopDataStatusResponse(BaseModel):
    overall_status: Literal["not_started", "partial", "ready"]
    source_connection_configured: bool = False
    sources: list[SopSourceStatus]
    open_quality_issues: int = 0


class SopMonthlyActual(BaseModel):
    period: str
    outbound_qty: float = 0
    activation_qty: float = 0


class SopChannelMonthlyActual(BaseModel):
    period: str
    region: str
    channel: str
    outbound_qty: float = 0
    activation_qty: float = 0


class SopForecastPoint(BaseModel):
    forecast_month: date
    region: str
    channel: str
    forecast_type: str
    forecast_qty: float
    version: str
    source_table: str
    snapshot_at: datetime


class SopRuleFinding(BaseModel):
    code: str
    severity: str
    message: str


class SopForecastCheck(BaseModel):
    forecast_month: date
    region: str
    channel: str
    forecast_qty: float
    evaluable: bool
    score: int | None = None
    level: str
    rule_version: str
    baseline_qty: float | None = None
    deviation_ratio: float | None = None
    findings: list[SopRuleFinding]


class SopProvenance(BaseModel):
    domain: str
    source_system: str
    source_table: str
    batch_id: str
    snapshot_at: datetime


class SopMonthlyEventInfo(BaseModel):
    event_month: date
    event: str


class SopFirstPhaseReportResponse(BaseModel):
    report_version: str = "sop-first-phase.v0.1"
    spu: SopSpuInfo
    as_of_date: date
    source_synced_at: datetime | None = None
    filters: SopReportFilters = Field(default_factory=SopReportFilters)
    completeness_status: Literal["complete", "partial", "not_ready"]
    missing_domains: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    monthly_actuals: list[SopMonthlyActual] = Field(default_factory=list)
    channel_actuals: list[SopChannelMonthlyActual] = Field(default_factory=list)
    events: list[SopMonthlyEventInfo] = Field(default_factory=list)
    forecasts: list[SopForecastPoint] = Field(default_factory=list)
    forecast_checks: list[SopForecastCheck] = Field(default_factory=list)
    provenance: list[SopProvenance] = Field(default_factory=list)


class SopImportMeta(BaseModel):
    source_system: str = Field(min_length=1, max_length=64)
    source_table: str = Field(min_length=1, max_length=255)
    batch_id: str = Field(min_length=1, max_length=128)
    snapshot_at: datetime


class SopSpuImportRow(BaseModel):
    spu_code: str = Field(min_length=1, max_length=128)
    source_spu_code: str | None = Field(default=None, max_length=128)
    mapping_type: str = "direct"
    mapping_version: str = "draft"
    spu_name: str = ""
    product_line: str = ""
    brand: str = ""
    category: str = ""
    lifecycle_stage: str = "unknown"
    predecessor_spu_code: str | None = None
    successor_spu_code: str | None = None


class SopSpuImportRequest(BaseModel):
    meta: SopImportMeta
    rows: list[SopSpuImportRow] = Field(min_length=1)


class SopSalesImportRow(BaseModel):
    spu_code: str = Field(min_length=1, max_length=128)
    business_date: date
    region: str = "ALL"
    channel: str = "ALL"
    order_qty: float = Field(default=0, ge=0)
    outbound_qty: float = Field(default=0, ge=0)


class SopSalesImportRequest(BaseModel):
    meta: SopImportMeta
    rows: list[SopSalesImportRow] = Field(min_length=1)


class SopActivationImportRow(BaseModel):
    spu_code: str = Field(min_length=1, max_length=128)
    business_date: date
    region: str = "ALL"
    channel: str = "ALL"
    activation_qty: float = Field(ge=0)


class SopActivationImportRequest(BaseModel):
    meta: SopImportMeta
    rows: list[SopActivationImportRow] = Field(min_length=1)


class SopForecastImportRow(BaseModel):
    spu_code: str = Field(min_length=1, max_length=128)
    forecast_month: date
    region: str = "ALL"
    channel: str = "ALL"
    forecast_type: str = "sales_submission"
    forecast_qty: float = Field(ge=0)
    version: str = "current"


class SopForecastImportRequest(BaseModel):
    meta: SopImportMeta
    rows: list[SopForecastImportRow] = Field(min_length=1)


class SopEventImportRow(BaseModel):
    spu_code: str = Field(min_length=1, max_length=128)
    event_month: date
    event: str = Field(min_length=1, max_length=500)


class SopEventImportRequest(BaseModel):
    meta: SopImportMeta
    rows: list[SopEventImportRow] = Field(min_length=1)


class SopImportResponse(BaseModel):
    domain: str
    batch_id: str
    accepted: int
    rejected: int
    status: Literal["completed", "partial", "failed"]
    quality_issue_ids: list[int] = Field(default_factory=list)


class SopReportSnapshotSummary(BaseModel):
    id: int
    spu_code: str
    as_of_date: date
    report_version: str
    completeness_status: str
    generated_at: datetime
    record_count: int = 0


class SopReportSnapshotDetail(BaseModel):
    id: int
    spu_code: str
    as_of_date: date
    report_version: str
    completeness_status: str
    generated_at: datetime
    payload: dict


class SopSnapshotGenerateRequest(BaseModel):
    spu_code: str | None = None
    as_of_date: date | None = None
    report_version: str | None = None


class SopSnapshotGenerateResponse(BaseModel):
    status: str = "success"
    message: str
    as_of_date: date
    report_version: str
    generated_count: int
    spu_codes: list[str]
