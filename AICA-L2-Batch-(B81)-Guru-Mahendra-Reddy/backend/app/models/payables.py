"""TAB 5 — Money Going Out: vendors, bills, statutory dues, commitments."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import Provenance


class Criticality:
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    ALL = [HIGH, MEDIUM, LOW]


class StatutoryHead:
    GST = "GST"
    TDS = "TDS"
    PF = "PF"
    ESI = "ESI"
    PT = "Professional Tax"
    ADVANCE_TAX = "Advance Tax"
    OTHER = "Others"
    ALL = [GST, TDS, PF, ESI, PT, ADVANCE_TAX, OTHER]


class CommitmentType:
    PO = "Purchase Order"
    CLOUD = "Cloud & Software Contract"
    OFFER = "Offer Letter Issued"
    LEASE = "Lease"
    RETAINER = "Retainer"
    OTHER = "Other"
    ALL = [PO, CLOUD, OFFER, LEASE, RETAINER, OTHER]


class Vendor(Base, Provenance):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    credit_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    criticality: Mapped[str] = mapped_column(String(16), default=Criticality.MEDIUM, nullable=False)
    on_hold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    burn_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Bill(Base, Provenance):
    """A payable. Deferrability and penalty are what make Tab 5A sortable in
    the order the CFO asked for: non-deferrable first, then by date."""
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), index=True, nullable=True)
    bill_no: Mapped[str] = mapped_column(String(60), nullable=False)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    outstanding: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    burn_category: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)
    cost_nature: Mapped[str | None] = mapped_column(String(24), nullable=True)

    deferrable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deferral_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    penalty_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approver: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # unpaid | approved | scheduled | paid | on-hold
    status: Mapped[str] = mapped_column(String(24), default="unpaid", index=True, nullable=False)
    paid_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    __table_args__ = (Index("ix_bill_entity_due", "entity_id", "due_date"),)


class StatutoryDue(Base, Provenance):
    """SPEC 5B — first-charge, penal interest, never negotiable. Its own layer."""
    __tablename__ = "statutory_dues"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    head: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(40), nullable=False)          # "Aug-26" / "Q2 FY26-27"
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    funded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    earmarked_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # pending | funded | paid | overdue
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True, nullable=False)
    paid_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    interest_penalty_paid: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Commitment(Base, Provenance):
    """SPEC 5C — money already spent that no invoice has arrived for.
    'The most commonly missed number in any cash tool.'"""
    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    commitment_type: Mapped[str] = mapped_column(String(48), nullable=False)
    counterparty: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    consumed_to_date: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cancellable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    monthly_runrate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    burn_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)

    @property
    def remaining(self) -> float:
        return max(self.total_value - self.consumed_to_date, 0.0)
