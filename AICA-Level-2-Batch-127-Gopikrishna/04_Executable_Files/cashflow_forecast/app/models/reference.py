"""Reference data: settings, bank accounts and balances, facilities, categories."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.types import ExactDecimal, Money
from app.models.base import Base, Direction, TimestampMixin, Treatment, str_enum, utcnow


class AppSetting(Base):
    """Key/value business settings (lot scheme, horizon, approver switch...). Admin-editable."""
    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[object] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))


class BankAccount(TimestampMixin, Base):
    __tablename__ = "bank_account"
    __table_args__ = (UniqueConstraint("bank_name", "account_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_name: Mapped[str] = mapped_column(String(80), nullable=False)
    account_name: Mapped[str] = mapped_column(String(80), nullable=False)
    account_no_masked: Mapped[str] = mapped_column(String(40), default="")  # last 4 digits only
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="OMR")
    erp_gl_code: Mapped[str] = mapped_column(String(40), default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    balances: Mapped[list[BankBalance]] = relationship(back_populates="account")


class BankBalance(Base):
    """ERP bank-ledger balance per account and as-of date (manual entry)."""
    __tablename__ = "bank_balance"
    __table_args__ = (
        UniqueConstraint("account_id", "as_of_date"),
        CheckConstraint("CAST(fx_rate_to_base AS REAL) > 0", name="fx_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("bank_account.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    balance: Mapped[Decimal] = mapped_column(Money(), nullable=False)          # in account currency
    fx_rate_to_base: Mapped[Decimal] = mapped_column(ExactDecimal(), nullable=False, default=Decimal(1))
    entered_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    entered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    account: Mapped[BankAccount] = relationship(back_populates="balances")


class BankFacility(Base):
    """Facility available per bank, entered manually per as-of date."""
    __tablename__ = "bank_facility"
    __table_args__ = (UniqueConstraint("bank_name", "facility_type", "as_of_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_name: Mapped[str] = mapped_column(String(80), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(60), default="Overdraft / working capital")
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    limit_amount: Mapped[Decimal | None] = mapped_column(Money())
    utilised_amount: Mapped[Decimal | None] = mapped_column(Money())
    available_amount: Mapped[Decimal] = mapped_column(Money(), nullable=False)  # used by the engine
    entered_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    entered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Category(TimestampMixin, Base):
    """Forecast category. Never hard-coded: loaded from the uploaded category list."""
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    direction: Mapped[Direction] = mapped_column(str_enum(Direction), nullable=False)
    summary_group: Mapped[str] = mapped_column(String(80), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    default_treatment: Mapped[Treatment] = mapped_column(str_enum(Treatment), default=Treatment.FIXED)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    aliases: Mapped[list[CategoryAlias]] = relationship(back_populates="category", cascade="all, delete-orphan")


class CategoryAlias(TimestampMixin, Base):
    """Remembered mapping 'header text as seen in a file' -> category, so it is asked only once."""
    __tablename__ = "category_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias_normalised: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    alias_original: Mapped[str] = mapped_column(String(120), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"), nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    category: Mapped[Category] = relationship(back_populates="aliases")


class SourceDefaultCategory(Base):
    """Default category for each import source (e.g. vendor_pdc -> 'Vendor PDCs')."""
    __tablename__ = "source_default_category"

    source_type: Mapped[str] = mapped_column(String(24), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=False)
