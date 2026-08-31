"""Users, companies and valuation cases."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def uid() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80), default="Analyst")
    email: Mapped[str] = mapped_column(String(200), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), default="(GMT+05:30) India Standard Time")
    date_format: Mapped[str] = mapped_column(String(32), default="MMM D, YYYY")
    number_format: Mapped[str] = mapped_column(String(32), default="1,234.56")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(120), default="")
    entity_type: Mapped[str] = mapped_column(String(120), default="Private Limited Company")
    country: Mapped[str] = mapped_column(String(80), default="India")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    cases: Mapped[list["ValuationCase"]] = relationship(back_populates="company")


class ValuationCase(Base):
    __tablename__ = "valuation_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    valuation_date: Mapped[str] = mapped_column(String(20))  # ISO date
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    units: Mapped[str] = mapped_column(String(20), default="crore")  # crore | lakh | absolute
    purpose: Mapped[str] = mapped_column(String(120), default="Internal Management Assessment")
    promoter_holding_pct: Mapped[float] = mapped_column(Float, default=100.0)
    total_shares: Mapped[float] = mapped_column(Float, default=0.0)  # fully diluted
    notes: Mapped[str] = mapped_column(Text, default="")

    # workflow
    status: Mapped[str] = mapped_column(String(40), default="draft")
    # draft | documents | review | interview | valuation | completed
    financials_locked: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    company: Mapped[Company] = relationship(back_populates="cases")
