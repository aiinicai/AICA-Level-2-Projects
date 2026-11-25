"""User changes (overrides), scenarios, daily snapshots and export log."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text,
                        UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Money
from app.models.base import (ApprovalStatus, Base, ExportCheck, OverrideAction, SourceType,
                             TimestampMixin, str_enum, utcnow)


class Override(TimestampMixin, Base):
    """A user change to an imported item, keyed by (source_type, source_key) - NOT by line_item.id.

    Because the key is the voucher / invoice number, a daily re-upload creates new line_item rows
    but the overrides still apply. At most one *active* override per key and action.
    Revoking sets is_active = False (history is kept, never deleted).
    """
    __tablename__ = "override"
    __table_args__ = (
        Index("uq_override_active", "source_type", "source_key", "action", unique=True,
              sqlite_where=text("is_active = 1")),
        CheckConstraint(
            "(action != 'defer' OR target_lot_start IS NOT NULL) AND "
            "(action != 'redate' OR new_date IS NOT NULL) AND "
            "(action != 'reduce' OR new_amount IS NOT NULL) AND "
            "(action != 'recategorise' OR new_category_id IS NOT NULL)",
            name="action_fields",
        ),
        CheckConstraint("new_amount IS NULL OR new_amount >= 0", name="amount_non_negative"),
        CheckConstraint("action != 'hold' OR new_amount IS NULL OR new_amount > 0", name="hold_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[SourceType] = mapped_column(str_enum(SourceType), nullable=False)
    source_key: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[OverrideAction] = mapped_column(str_enum(OverrideAction), nullable=False)

    new_date: Mapped[date | None] = mapped_column(Date)            # redate; hold: next honouring date
    target_lot_start: Mapped[date | None] = mapped_column(Date)    # defer: first day of the target lot
    new_amount: Mapped[Decimal | None] = mapped_column(Money())    # reduce; hold: amount held (partial)
    new_category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    reason: Mapped[str] = mapped_column(Text, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    revoked_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)

    approval_status: Mapped[ApprovalStatus] = mapped_column(
        str_enum(ApprovalStatus), default=ApprovalStatus.NOT_REQUIRED, nullable=False)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)


class Scenario(TimestampMixin, Base):
    __tablename__ = "scenario"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    exclude_risk_adjusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    use_delay_model: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # advisory
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))


class Snapshot(Base):
    """Frozen copy of the grid. One per day and scenario (re-saving the same day replaces it)."""
    __tablename__ = "snapshot"
    __table_args__ = (UniqueConstraint("snapshot_date", "scenario_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"), nullable=False)
    grid: Mapped[dict] = mapped_column(JSON, nullable=False)       # lots, rows, totals (strings, 3 dp)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExportLog(Base):
    __tablename__ = "export_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    scenario_id: Mapped[int | None] = mapped_column(ForeignKey("scenario.id"))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    check_status: Mapped[ExportCheck] = mapped_column(str_enum(ExportCheck), default=ExportCheck.NOT_RUN)
    differences: Mapped[list | None] = mapped_column(JSON)         # cells where LibreOffice != engine
    released: Mapped[bool] = mapped_column(Boolean, default=False)  # False -> download blocked
    note: Mapped[str] = mapped_column(Text, default="")
