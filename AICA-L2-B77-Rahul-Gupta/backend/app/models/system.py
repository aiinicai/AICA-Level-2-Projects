"""AI insights, reports, AI call logs, app settings, audit log."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .core import now, uid


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    section: Mapped[str] = mapped_column(String(60))
    # key_insight | positive_driver | risk_flag | earnings_quality | strength
    # | assumption_review | next_action | business_quality
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20), default="info")
    # info | positive | moderate | high | low
    source: Mapped[str] = mapped_column(String(20), default="engine")  # engine | ai
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    template: Mapped[str] = mapped_column(String(60), default="comprehensive")
    title: Mapped[str] = mapped_column(String(200), default="")
    language: Mapped[str] = mapped_column(String(30), default="English")
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    html_path: Mapped[str] = mapped_column(String(400), default="")
    pdf_path: Mapped[str] = mapped_column(String(400), default="")
    status: Mapped[str] = mapped_column(String(20), default="generated")  # generating | generated | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AICallLog(Base):
    __tablename__ = "ai_call_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("valuation_cases.id"), nullable=True)
    task: Mapped[str] = mapped_column(String(60))
    # verify_document | generate_question | interpret_answer | insights | report
    model: Mapped[str] = mapped_column(String(60), default="")
    success: Mapped[int] = mapped_column(Integer, default=1)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("valuation_cases.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
