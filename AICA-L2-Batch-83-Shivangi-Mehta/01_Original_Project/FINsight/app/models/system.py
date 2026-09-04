"""
AuditLog, ApplicationSetting, KnowledgeBaseVersion — Blueprint Section 2
(D.17-D.19). AuditLog is the tool's own meta-audit trail (who changed
what in FinSight), distinct from the accounting/audit content FinSight
reviews.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_engagement", "engagement_id"),)

    log_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int | None] = mapped_column(ForeignKey("engagements.engagement_id"), default=None)
    action: Mapped[str] = mapped_column()  # e.g. "EXCEPTION_STATUS_CHANGED"
    entity_affected: Mapped[str | None] = mapped_column(default=None)  # table/record reference
    performed_by: Mapped[str | None] = mapped_column(default=None)
    timestamp: Mapped[str] = mapped_column()
    detail_json: Mapped[str | None] = mapped_column(default=None)  # before/after values


class ApplicationSetting(Base):
    __tablename__ = "application_settings"

    setting_key: Mapped[str] = mapped_column(primary_key=True)  # e.g. "ai_enabled", "risk_threshold_high"
    setting_value: Mapped[str | None] = mapped_column(default=None)
    updated_at: Mapped[str | None] = mapped_column(default=None)


class KnowledgeBaseVersion(Base):
    __tablename__ = "knowledge_base_versions"

    kb_version_id: Mapped[int] = mapped_column(primary_key=True)
    version_label: Mapped[str] = mapped_column(unique=True)  # e.g. "2026.1" — one row per version label
    released_at: Mapped[str | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(default=None)
    is_current: Mapped[bool] = mapped_column(default=False)
