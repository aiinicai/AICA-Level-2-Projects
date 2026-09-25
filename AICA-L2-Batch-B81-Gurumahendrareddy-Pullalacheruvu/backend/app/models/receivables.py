"""TAB 4 — Money Coming In."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import Provenance


class Customer(Base, Provenance):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    credit_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)       # who chases them
    last_contact: Mapped[date | None] = mapped_column(Date, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(160), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Invoice(Base, Provenance):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    invoice_no: Mapped[str] = mapped_column(String(60), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    outstanding: Mapped[float] = mapped_column(Float, nullable=False)
    # open | part-paid | paid | disputed | written-off
    status: Mapped[str] = mapped_column(String(24), default="open", index=True, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # SPEC 4 — disputed items live in their own table view, never mixed into ageing
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispute_raised_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    dispute_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expected_resolution: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Weighted collectible — probability is either set manually or derived from
    # the client's actual payment behaviour (see services/receivables.py).
    collection_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    promised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    promised_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("ix_invoice_entity_due", "entity_id", "due_date"),)


class Receipt(Base, Provenance):
    """Actual money received. Drives 'average days taken to pay' — their real
    behaviour, not their stated terms."""
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True, nullable=True)
    received_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(80), nullable=True)


class UnbilledWork(Base, Provenance):
    """SPEC 4 — Invoicing Gap. Cash we are sitting on by our own delay."""
    __tablename__ = "unbilled_work"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    delivered_on: Mapped[date] = mapped_column(Date, nullable=False)
    expected_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    blocker: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)


class CollectionPerformance(Base):
    """SPEC 4 — Promised vs Actually Received, last 6 months. Calibrates how
    much the weighted figure should be believed."""
    __tablename__ = "collection_performance"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    month: Mapped[date] = mapped_column(Date, index=True, nullable=False)   # first of month
    promised: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    received: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class ExpectedInflow(Base, Provenance):
    """Non-AR money in: funding tranches, grants, refunds, deposits released.
    Manual-entry register item (SPEC 12A)."""
    __tablename__ = "expected_inflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    # Funding | Grant | Refund | Deposit Release | Other
    inflow_type: Mapped[str] = mapped_column(String(40), default="Other", nullable=False)
    expected_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
