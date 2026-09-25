"""Accounting + banking: chart of accounts, ledger entries, bank accounts.

This is the common internal schema the Tally adapter normalises into, so
adding Zoho Books later means writing one adapter, not touching anything
downstream.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import Provenance


class CostNature:
    FIXED = "Fixed"
    VARIABLE = "Variable"
    DISCRETIONARY = "Discretionary"
    ALL = [FIXED, VARIABLE, DISCRETIONARY]


class BurnCategory:
    """SPEC 2B — the nine top-level categories, not buried."""
    PEOPLE = "People"
    STATUTORY = "Statutory & Taxes"
    TECH = "Technology & Cloud"
    DELIVERY = "Client Delivery / Cost of Sales"
    FACILITIES = "Rent & Facilities"
    MARKETING = "Marketing"
    PROFESSIONAL = "Professional Fees"
    FINANCE_COST = "Finance Costs"
    OTHER = "Other"
    ALL = [PEOPLE, STATUTORY, TECH, DELIVERY, FACILITIES,
           MARKETING, PROFESSIONAL, FINANCE_COST, OTHER]


class Account(Base):
    """Normalised chart of accounts."""
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)  # Tally GUID
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_group: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # asset | liability | equity | income | expense
    classification: Mapped[str] = mapped_column(String(24), nullable=False)
    # cash | bank | receivable | payable | statutory | loan | other
    sub_type: Mapped[str] = mapped_column(String(24), default="other", nullable=False)
    burn_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cost_nature: Mapped[str | None] = mapped_column(String(24), nullable=True)
    is_cash: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opening_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    closing_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (Index("ix_accounts_entity_name", "entity_id", "name"),)


class LedgerEntry(Base):
    """One cash-relevant movement. Drill-down (design principle 3) resolves here."""
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=True)
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    txn_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    voucher_type: Mapped[str] = mapped_column(String(60), default="Payment", nullable=False)
    voucher_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    party: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    debit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    credit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Cash-flow view: positive = money in, negative = money out. 0 = non-cash.
    cash_amount: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    burn_category: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)
    cost_nature: Mapped[str | None] = mapped_column(String(24), nullable=True)

    # SPEC 2B — recurring vs one-off, with who classified it
    is_one_off: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    one_off_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    classified_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    external_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="seed", nullable=False)

    __table_args__ = (Index("ix_ledger_entity_date", "entity_id", "txn_date"),)


class BankAccount(Base, Provenance):
    """SPEC 3A — where the money actually is, and whether it is actually available."""
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    institution: Mapped[str] = mapped_column(String(160), nullable=False)
    account_name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_masked: Mapped[str | None] = mapped_column(String(40), nullable=True)   # last 4 only
    # Operating | Collection | Payroll | Statutory | Deposit
    purpose: Mapped[str] = mapped_column(String(40), default="Operating", nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    books_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    restriction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    signatory: Mapped[str | None] = mapped_column(String(160), nullable=True)
    approval_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    as_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class BankBalanceHistory(Base):
    """Daily/period closing balances — feeds the 12-month cash line."""
    __tablename__ = "bank_balance_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    as_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    books_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
