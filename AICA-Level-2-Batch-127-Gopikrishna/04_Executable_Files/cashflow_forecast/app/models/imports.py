"""Imported data: upload batches (with file hash log), line items, mapping exceptions, history."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.types import Money
from app.models.base import (BatchStatus, Base, Direction, ExceptionStatus, SourceType, str_enum,
                             utcnow)


class ImportBatch(Base):
    """One uploaded file. Doubles as the file-hash log (sha256, size, who, when)."""
    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[SourceType] = mapped_column(str_enum(SourceType), nullable=False, index=True)
    # A re-upload replaces the current accepted batch of the same slot. Slot = source type, except
    # 'other' where several files can be current at once (slot = file name stem or a label).
    slot: Mapped[str] = mapped_column(String(80), nullable=False, default="", index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[BatchStatus] = mapped_column(str_enum(BatchStatus), default=BatchStatus.UPLOADED)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_report: Mapped[dict | None] = mapped_column(JSON)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    items: Mapped[list[LineItem]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class LineItem(Base):
    """A row exactly as imported. Never edited by users - changes live in ``override``.

    ``source_key`` is the natural key (voucher no, invoice no, reference). Together with
    ``source_type`` it links the row to its overrides, so re-uploading the same file keeps them.
    """
    __tablename__ = "line_item"
    __table_args__ = (
        UniqueConstraint("batch_id", "source_key"),
        Index("ix_line_item_key", "source_type", "source_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(str_enum(SourceType), nullable=False)
    source_key: Mapped[str] = mapped_column(String(80), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)     # row in the uploaded file

    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))  # None until mapped / ignored
    category_text: Mapped[str] = mapped_column(String(120), default="")         # category as written in the file
    direction: Mapped[Direction] = mapped_column(str_enum(Direction), nullable=False)
    direction_provisional: Mapped[bool] = mapped_column(Boolean, default=False)  # take it from the category
    bill_discounted_imported: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_invoice: Mapped[str] = mapped_column(String(80), default="")         # BD proceeds: invoice financed
    counterparty: Mapped[str] = mapped_column(String(160), default="")   # customer / vendor / bank
    project: Mapped[str] = mapped_column(String(80), default="")
    reference: Mapped[str] = mapped_column(String(80), default="")       # cheque no, bank ref, invoice
    bank_name: Mapped[str] = mapped_column(String(80), default="")
    planned_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # due/cheque/maturity
    amount: Mapped[Decimal] = mapped_column(Money(), nullable=False)     # positive, OMR
    currency: Mapped[str] = mapped_column(String(3), default="OMR")
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_flag_imported: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)               # original cells, untouched

    batch: Mapped[ImportBatch] = relationship(back_populates="items")


class MappingException(Base):
    """Unmatched header / category text waiting for a user decision."""
    __tablename__ = "mapping_exception"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False)
    raw_text: Mapped[str] = mapped_column(String(160), nullable=False)
    context: Mapped[str] = mapped_column(String(24), default="header")   # header | category_column
    suggested_category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    suggestion_score: Mapped[float | None] = mapped_column(Float)       # rapidfuzz 0-100
    status: Mapped[ExceptionStatus] = mapped_column(str_enum(ExceptionStatus), default=ExceptionStatus.OPEN)
    resolved_category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class CollectionHistory(Base):
    """Past invoices with their actual payment date (optional; feeds the delay model)."""
    __tablename__ = "collection_history"
    __table_args__ = (UniqueConstraint("invoice_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(80), nullable=False)
    customer: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    project: Mapped[str] = mapped_column(String(80), default="")
    invoice_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id", ondelete="SET NULL"))
