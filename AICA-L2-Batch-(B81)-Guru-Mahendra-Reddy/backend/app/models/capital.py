"""TAB 9 — Capital & Debt: facilities, repayments, covenants, funding."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import Provenance


class Facility(Base, Provenance):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    lender: Mapped[str] = mapped_column(String(200), nullable=False)
    # Term Loan | Working Capital | Overdraft | Venture Debt | Invoice Discounting | Lease
    facility_type: Mapped[str] = mapped_column(String(60), nullable=False)
    sanctioned: Mapped[float] = mapped_column(Float, nullable=False)
    drawn: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interest_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)   # % p.a.
    tenure_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_repayment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_repayment_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    security_given: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def available_to_draw(self) -> float:
        return max(self.sanctioned - self.drawn, 0.0)


class RepaymentScheduleItem(Base, Provenance):
    __tablename__ = "repayment_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    principal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interest: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Covenant(Base, Provenance):
    """SPEC 9 — 'Amber before breach, not after.'"""
    __tablename__ = "covenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(60), nullable=False)  # current_ratio, dscr, ...
    operator: Mapped[str] = mapped_column(String(8), default=">=", nullable=False)   # >= | <= | >
    required_value: Mapped[float] = mapped_column(Float, nullable=False)
    amber_buffer_pct: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    test_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    test_frequency: Mapped[str] = mapped_column(String(24), default="Quarterly", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FundingRound(Base, Provenance):
    __tablename__ = "funding_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    round_name: Mapped[str] = mapped_column(String(80), nullable=False)
    closed_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    instrument: Mapped[str] = mapped_column(String(80), default="Equity", nullable=False)
    investor: Mapped[str | None] = mapped_column(String(300), nullable=True)
    post_money_valuation: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash_remaining: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class NextRaise(Base, Provenance):
    """SPEC 9 — target, trigger date, days until trigger."""
    __tablename__ = "next_raise"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    target_close_date: Mapped[date] = mapped_column(Date, nullable=False)
    lead_time_months: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    instrument: Mapped[str] = mapped_column(String(80), default="Equity", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="Not started", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
