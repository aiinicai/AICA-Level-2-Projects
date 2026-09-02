"""Valuation assumptions, runs, method results, scenarios."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .core import now, uid


class ValuationAssumption(Base):
    __tablename__ = "valuation_assumptions"
    __table_args__ = (UniqueConstraint("case_id", "key"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    key: Mapped[str] = mapped_column(String(60))  # revenue_growth, ebitda_margin, wacc, ...
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_recommended_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reason: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="default")
    # default | user | ai_accepted | derived
    status: Mapped[str] = mapped_column(String(20), default="accepted")  # proposed | accepted
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class ValuationRun(Base):
    __tablename__ = "valuation_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    run_label: Mapped[str] = mapped_column(String(60), default="Base Case")
    assumptions: Mapped[dict] = mapped_column(JSON, default=dict)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)

    enterprise_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    equity_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    central_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_share_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[str] = mapped_column(String(30), default="")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)

    detail: Mapped[dict] = mapped_column(JSON, default=dict)  # full engine output
    analyst: Mapped[str] = mapped_column(String(120), default="")
    methods_used: Mapped[list] = mapped_column(JSON, default=list)
    is_current: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ValuationMethodResult(Base):
    __tablename__ = "valuation_method_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("valuation_runs.id"))
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    method: Mapped[str] = mapped_column(String(30))  # dcf | market_multiple | adjusted_nav
    enterprise_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    equity_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_share_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    key_driver: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    name: Mapped[str] = mapped_column(String(60))  # Bear Case | Base Case | Bull Case | custom
    assumptions: Mapped[dict] = mapped_column(JSON, default=dict)
    enterprise_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    equity_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    vs_base_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_named: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
