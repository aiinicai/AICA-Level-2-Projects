"""Connector configuration: ledger mapping, schedules, import batches.

Connecting to Tally is the easy half. The hard half is that every Tally company
has its own chart of accounts, written by whoever was there at the time —
"Sundry Debtors - BLR", "SD-Old", "Misc Exp 2". A connector that guesses and
moves on is how the numbers quietly go wrong, so the guess is shown to a human
once, corrected, stored, and re-checked on every later sync.
"""
from __future__ import annotations

from datetime import datetime
from datetime import date as _date

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import utcnow


class LedgerMapping(Base):
    """How one Tally ledger maps into the common internal schema.

    `confirmed` is the important column. An unconfirmed row is the app's guess;
    a confirmed row is a person's decision. Only the second is trusted, and the
    sync reports how many of the first are still outstanding.
    """

    __tablename__ = "ledger_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="tally", nullable=False)

    ledger_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    parent_group: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    classification: Mapped[str | None] = mapped_column(String(24), nullable=True)  # asset|liability|income|expense|equity
    sub_type: Mapped[str | None] = mapped_column(String(32), nullable=True)        # bank|cash|receivable|payable|statutory|loan|other
    is_cash: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    burn_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cost_nature: Mapped[str | None] = mapped_column(String(24), nullable=True)

    guessed_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    guess_matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    confirmed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class SyncSchedule(Base):
    """When to pull, and the honest caveat that goes with it.

    Tally cannot push. There is no webhook and no callback, so a daily sync is
    the app polling at a set time — which only happens if the app is running
    then. That constraint is stated in Setup rather than hidden behind a
    promise of freshness the architecture cannot keep.
    """

    __tablename__ = "sync_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="tally", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hour: Mapped[int] = mapped_column(Integer, default=8, nullable=False)      # local 24h
    minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    stale_after_hours: Mapped[int] = mapped_column(Integer, default=36, nullable=False)
    last_attempt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ImportBatch(Base):
    """One upload of a filled-in workbook: what went in, what was rejected."""

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sheets: Mapped[str | None] = mapped_column(Text, nullable=True)            # JSON summary
    rows_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)            # JSON rows
    committed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class OnboardingState(Base):
    """How far setup has got, so screens can say what they still need.

    Deliberately not a single "setup complete" flag. The stages exist because
    each one buys something: stage 1 produces a defensible runway number, and a
    tool that gets you to a real number in ten minutes is one you come back to.
    """

    __tablename__ = "onboarding_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), unique=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(24), default="own", nullable=False)   # demo|own
    stage1_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stage2_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stage3_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
