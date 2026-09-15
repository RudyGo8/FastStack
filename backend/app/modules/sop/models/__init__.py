"""
Ensure all SQLAlchemy models are imported so relationship() targets resolve
before the first mapper configuration or metadata initialization.
"""

from app.modules.sop.models.db_chat_message import ChatMessage
from app.modules.sop.models.db_chat_session import ChatSession
from app.modules.sop.models.db_parent_chunk import ParentChunk
from app.modules.sop.models.db_sop import (
    SopActivationDaily,
    SopAuditLog,
    SopDataQualityIssue,
    SopForecastMonthly,
    SopForecastValidation,
    SopReportSnapshot,
    SopSalesDaily,
    SopSourceSnapshot,
    SopSpu,
    SopSpuMapping,
)

__all__ = [
    "ChatSession",
    "ChatMessage",
    "ParentChunk",
    "SopSpu",
    "SopSpuMapping",
    "SopSalesDaily",
    "SopActivationDaily",
    "SopForecastMonthly",
    "SopSourceSnapshot",
    "SopDataQualityIssue",
    "SopForecastValidation",
    "SopReportSnapshot",
    "SopAuditLog",
]
