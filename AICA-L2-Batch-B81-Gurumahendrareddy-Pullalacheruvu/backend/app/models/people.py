"""TAB 2C — People Cost. Largest line and the one the CFO controls most directly."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import Provenance


class HeadcountMonth(Base, Provenance):
    """One row per entity per month."""
    __tablename__ = "headcount_months"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    month: Mapped[date] = mapped_column(Date, index=True, nullable=False)      # first of month
    funded_headcount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_headcount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_unfilled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    offers_accepted_not_joined: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    people_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attrition: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FunctionCost(Base, Provenance):
    """Fully-loaded cost per head, by function."""
    __tablename__ = "function_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    month: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    function: Mapped[str] = mapped_column(String(80), nullable=False)   # Engineering, Sales, ...
    headcount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fully_loaded_cost_per_head: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class HiringPlanItem(Base, Provenance):
    """SPEC 2C — hiring plan cash impact over the next 6 months, and its effect
    on the cash-out date."""
    __tablename__ = "hiring_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(160), nullable=False)
    function: Mapped[str] = mapped_column(String(80), nullable=False)
    positions: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    planned_start: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    monthly_cost_each: Mapped[float] = mapped_column(Float, nullable=False)
    one_time_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # recruiter fee etc.
    # planned | offer-out | accepted | joined | on-hold | cancelled
    status: Mapped[str] = mapped_column(String(24), default="planned", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmployeeLiability(Base, Provenance):
    """Gratuity / leave-encashment accrual — cash that will eventually leave."""
    __tablename__ = "employee_liabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    as_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    gratuity_accrued: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    leave_encashment_accrued: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bonus_accrued: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    funded_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
