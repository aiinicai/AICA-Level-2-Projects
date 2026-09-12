"""Core: users, entities, settings, definitions, activity log, sync runs."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import Provenance, utcnow


class Role:
    ADMIN = "Admin"
    CFO = "CFO"
    FINANCE = "Finance"
    BOARD = "Board Read-Only"
    ALL = [ADMIN, CFO, FINANCE, BOARD]
    # Who may change things. Board Read-Only never writes.
    WRITERS = [ADMIN, CFO, FINANCE]
    APPROVERS = [ADMIN, CFO]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=Role.FINANCE, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(24), nullable=True)   # E.164, for SMS
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    @property
    def can_write(self) -> bool:
        return self.role in Role.WRITERS

    @property
    def can_approve(self) -> bool:
        return self.role in Role.APPROVERS


class Entity(Base):
    """India / Singapore / Consolidated, per the top-strip dropdown."""
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    fx_to_inr: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_consolidated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tally_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    min_cash_floor: Mapped[float] = mapped_column(Float, default=4000000.0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Books/bank close state shown in the top strip
    books_closed_upto: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_data_update: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Setting(Base):
    """Free-form key/value config editable from Setup, with an audit trail."""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    key: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), default="string")   # string|number|bool|json
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Definition(Base):
    """SPEC 12D — the glossary. Every argument about a number ends here."""
    __tablename__ = "definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    plain_english: Mapped[str] = mapped_column(Text, nullable=False)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    basis_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="General")
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ActivityLog(Base):
    """SPEC 12D — who changed a threshold, uploaded a plan, reclassified a
    one-off, or exported a pack."""
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)        # created|updated|deleted|approved|exported|synced
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)


class SyncRun(Base):
    """SPEC 12A — accounting connection status, last sync, failure history."""
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="tally", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="running")     # running|success|failed|partial
    records: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(120), nullable=True)


class BankStatementImport(Base):
    """SPEC 12A — bank statement upload, used for the books-vs-bank check."""
    __tablename__ = "bank_statement_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    as_on: Mapped[date] = mapped_column(Date, nullable=False)
    closing_balance: Mapped[float] = mapped_column(Float, nullable=False)
    rows_accepted: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
