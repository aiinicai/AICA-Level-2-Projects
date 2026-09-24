"""TABS 7, 8 and the forecast machinery behind TAB 6."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import Provenance, utcnow


class VarianceType:
    """SPEC 7 — fixed dropdown, never free text. A slipped collection and a
    lost deal are different events and the tool must not let them be recorded
    identically."""
    TIMING = "Timing"
    VOLUME = "Volume"
    PRICE = "Price"
    COST_OVERRUN = "Cost Overrun"
    ONE_OFF = "One-Off"
    PERMANENT = "Permanent"
    ALL = [TIMING, VOLUME, PRICE, COST_OVERRUN, ONE_OFF, PERMANENT]
    # Timing variances reverse — shown in a distinct shade on the waterfall.
    REVERSING = [TIMING]


class Plan(Base, Provenance):
    """A version of the plan. Every number on Tab 7 is stamped with one."""
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(24), nullable=False)          # v1, v2, v2.1
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    uploaded_on: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    board_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    seconded_by: Mapped[str | None] = mapped_column(String(120), nullable=True)   # second approver
    approved_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    opening_cash: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supersedes_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)


class PlanLine(Base):
    __tablename__ = "plan_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True, nullable=False)
    month: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    # inflow | outflow | closing
    line_type: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class VarianceNote(Base, Provenance):
    """The typed explanation attached to a month or a line."""
    __tablename__ = "variance_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True, nullable=False)
    month: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)   # null = whole month
    variance_type: Mapped[str] = mapped_column(String(24), nullable=False)
    driver: Mapped[str] = mapped_column(String(300), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # open | explained | actioned | closed
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False)


class ForecastSnapshot(Base):
    """SPEC 6 — forecast accuracy. We store what we forecast for a week so we
    can later say how wrong we were. Without this the grid can't be trusted."""
    __tablename__ = "forecast_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    made_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    forecast_closing: Mapped[float] = mapped_column(Float, nullable=False)
    actual_closing: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str] = mapped_column(String(12), default="Medium", nullable=False)


class Scenario(Base, Provenance):
    """SPEC 8 — saved lever sets. `levers` is JSON so the panel can grow
    without a migration."""
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    levers: Mapped[str] = mapped_column(Text, default="{}", nullable=False)     # JSON
    is_prebuilt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ScoreHistory(Base):
    """SPEC 3B — 12-month liquidity score line with the events that moved it."""
    __tablename__ = "score_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    month: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    band: Mapped[str] = mapped_column(String(16), nullable=False)
    components: Mapped[str] = mapped_column(Text, default="{}", nullable=False)   # JSON breakdown
    event_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
