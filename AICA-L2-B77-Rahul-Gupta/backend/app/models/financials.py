"""Canonical financial data: periods, line items, ratios, normalisation adjustments."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .core import now, uid


class FinancialPeriod(Base):
    __tablename__ = "financial_periods"
    __table_args__ = (UniqueConstraint("case_id", "label"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    label: Mapped[str] = mapped_column(String(20))  # FY2024-25
    end_date: Mapped[str] = mapped_column(String(20), default="")  # ISO
    order_index: Mapped[int] = mapped_column(Integer, default=0)  # 0 oldest


class FinancialLineItem(Base):
    """One canonical metric value for one period — fully auditable."""

    __tablename__ = "financial_line_items"
    __table_args__ = (UniqueConstraint("case_id", "period_label", "metric"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    period_label: Mapped[str] = mapped_column(String(20))
    statement: Mapped[str] = mapped_column(String(30))  # pnl | balance_sheet | cash_flow
    metric: Mapped[str] = mapped_column(String(60))  # canonical name e.g. revenue

    # audit trail values (absolute INR)
    python_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_visual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    original_label: Mapped[str] = mapped_column(String(300), default="")
    original_display: Mapped[str] = mapped_column(String(80), default="")
    unit: Mapped[str] = mapped_column(String(20), default="INR")

    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    source_page: Mapped[int] = mapped_column(Integer, default=0)

    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    # verified | needs_review | low_confidence | missing | unverified
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    review_note: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Ratio(Base):
    __tablename__ = "ratios"
    __table_args__ = (UniqueConstraint("case_id", "period_label", "name"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    period_label: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(60))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    display: Mapped[str] = mapped_column(String(40), default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class NormalisationAdjustment(Base):
    __tablename__ = "normalisation_adjustments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    period_label: Mapped[str] = mapped_column(String(20))
    metric: Mapped[str] = mapped_column(String(60))  # e.g. revenue, ebitda
    kind: Mapped[str] = mapped_column(String(60), default="one_time_revenue")
    reported_value: Mapped[float] = mapped_column(Float, default=0.0)
    adjustment: Mapped[float] = mapped_column(Float, default=0.0)  # signed
    reason: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(120), default="interview")
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed | approved | rejected
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
