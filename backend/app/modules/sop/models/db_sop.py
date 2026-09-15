"""SQLAlchemy models for the first S&OP delivery.

Raw warehouse rows are never exposed to the Agent. They are normalized into
these application-owned tables together with source and batch metadata.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.modules.sop.database import Base


class SopSpu(Base):
    __tablename__ = "sop_spu_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spu_code = Column(String(128), unique=True, nullable=False, index=True)
    spu_name = Column(String(255), default="", nullable=False)
    product_line = Column(String(128), default="", nullable=False, index=True)
    brand = Column(String(128), default="", nullable=False)
    category = Column(String(128), default="", nullable=False)
    lifecycle_stage = Column(String(32), default="unknown", nullable=False)
    predecessor_spu_code = Column(String(128), nullable=True)
    successor_spu_code = Column(String(128), nullable=True)
    source_system = Column(String(64), default="", nullable=False)
    source_updated_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class SopSpuMapping(Base):
    __tablename__ = "sop_spu_mapping"
    __table_args__ = (UniqueConstraint("source_system", "source_spu_code", name="uq_sop_spu_mapping_source"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_system = Column(String(64), nullable=False)
    source_spu_code = Column(String(128), nullable=False)
    canonical_spu_code = Column(String(128), nullable=False, index=True)
    mapping_type = Column(String(32), default="direct", nullable=False)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    mapping_version = Column(String(64), default="draft", nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)


class SopSalesDaily(Base):
    __tablename__ = "sop_sales_daily"
    __table_args__ = (
        UniqueConstraint(
            "spu_code",
            "business_date",
            "region",
            "channel",
            "source_table",
            name="uq_sop_sales_daily_grain",
        ),
        Index("ix_sop_sales_spu_date", "spu_code", "business_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    spu_code = Column(String(128), nullable=False)
    business_date = Column(Date, nullable=False)
    region = Column(String(128), default="ALL", nullable=False)
    channel = Column(String(128), default="ALL", nullable=False)
    order_qty = Column(Numeric(18, 4), default=0, nullable=False)
    outbound_qty = Column(Numeric(18, 4), default=0, nullable=False)
    source_system = Column(String(64), nullable=False)
    source_table = Column(String(255), nullable=False)
    batch_id = Column(String(128), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)


class SopActivationDaily(Base):
    __tablename__ = "sop_activation_daily"
    __table_args__ = (
        UniqueConstraint(
            "spu_code",
            "business_date",
            "region",
            "channel",
            "source_table",
            name="uq_sop_activation_daily_grain",
        ),
        Index("ix_sop_activation_spu_date", "spu_code", "business_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    spu_code = Column(String(128), nullable=False)
    business_date = Column(Date, nullable=False)
    region = Column(String(128), default="ALL", nullable=False)
    channel = Column(String(128), default="ALL", nullable=False)
    activation_qty = Column(Numeric(18, 4), default=0, nullable=False)
    source_system = Column(String(64), nullable=False)
    source_table = Column(String(255), nullable=False)
    batch_id = Column(String(128), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)


class SopForecastMonthly(Base):
    __tablename__ = "sop_forecast_monthly"
    __table_args__ = (
        UniqueConstraint(
            "spu_code",
            "forecast_month",
            "region",
            "channel",
            "forecast_type",
            "version",
            name="uq_sop_forecast_monthly_grain",
        ),
        Index("ix_sop_forecast_spu_month", "spu_code", "forecast_month"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    spu_code = Column(String(128), nullable=False)
    forecast_month = Column(Date, nullable=False)
    region = Column(String(128), default="ALL", nullable=False)
    channel = Column(String(128), default="ALL", nullable=False)
    forecast_type = Column(String(32), default="sales_submission", nullable=False)
    forecast_qty = Column(Numeric(18, 4), nullable=False)
    version = Column(String(64), default="current", nullable=False)
    source_system = Column(String(64), nullable=False)
    source_table = Column(String(255), nullable=False)
    batch_id = Column(String(128), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)


class SopMonthlyEvent(Base):
    __tablename__ = "sop_monthly_event"
    __table_args__ = (
        UniqueConstraint("spu_code", "event_month", name="uq_sop_monthly_event_grain"),
        Index("ix_sop_event_spu_month", "spu_code", "event_month"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    spu_code = Column(String(128), nullable=False)
    event_month = Column(Date, nullable=False)
    event_text = Column(String(500), default="", nullable=False)
    source_system = Column(String(64), nullable=False)
    source_table = Column(String(255), nullable=False)
    batch_id = Column(String(128), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)


class SopSourceSnapshot(Base):
    __tablename__ = "sop_source_snapshot"
    __table_args__ = (
        UniqueConstraint("domain", "source_table", "batch_id", name="uq_sop_source_snapshot_batch"),
        Index("ix_sop_source_domain_time", "domain", "snapshot_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(64), nullable=False)
    source_system = Column(String(64), nullable=False)
    source_table = Column(String(255), nullable=False)
    batch_id = Column(String(128), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)
    max_business_date = Column(Date, nullable=True)
    record_count = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="completed", nullable=False)
    details_json = Column(JSON, default=dict, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)


class SopDataQualityIssue(Base):
    __tablename__ = "sop_data_quality_issue"
    __table_args__ = (Index("ix_sop_quality_domain_status", "domain", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(64), nullable=False)
    source_table = Column(String(255), default="", nullable=False)
    batch_id = Column(String(128), default="", nullable=False)
    issue_type = Column(String(64), nullable=False)
    severity = Column(String(16), default="medium", nullable=False)
    spu_code = Column(String(128), nullable=True, index=True)
    details = Column(Text, default="", nullable=False)
    status = Column(String(24), default="open", nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime, nullable=True)


class SopForecastValidation(Base):
    __tablename__ = "sop_forecast_validation"
    __table_args__ = (Index("ix_sop_validation_spu_month", "spu_code", "forecast_month"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    spu_code = Column(String(128), nullable=False)
    forecast_month = Column(Date, nullable=False)
    region = Column(String(128), default="ALL", nullable=False)
    channel = Column(String(128), default="ALL", nullable=False)
    score = Column(Numeric(6, 2), nullable=True)
    risk_level = Column(String(24), nullable=False)
    rule_version = Column(String(64), nullable=False)
    findings_json = Column(JSON, default=list, nullable=False)
    evidence_json = Column(JSON, default=dict, nullable=False)
    review_status = Column(String(24), default="pending", nullable=False)
    reviewed_by = Column(String(128), nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class SopReportSnapshot(Base):
    __tablename__ = "sop_report_snapshot"
    __table_args__ = (Index("ix_sop_report_spu_asof", "spu_code", "as_of_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    spu_code = Column(String(128), nullable=False)
    as_of_date = Column(Date, nullable=False)
    report_version = Column(String(64), nullable=False)
    completeness_status = Column(String(24), nullable=False)
    payload_json = Column(JSON, nullable=False)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class SopAuditLog(Base):
    __tablename__ = "sop_audit_log"
    __table_args__ = (Index("ix_sop_audit_user_time", "username", "create_time"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), nullable=False)
    action = Column(String(64), nullable=False)
    resource = Column(String(255), nullable=False)
    result_status = Column(String(32), nullable=False)
    request_id = Column(String(64), nullable=False)
    details_json = Column(JSON, default=dict, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)
