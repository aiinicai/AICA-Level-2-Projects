"""
Transaction — Blueprint Section 2.10 (hybrid model, Ambiguity #2 /
Correction #8). Common ledger-style fields as real columns; genuinely
one-off fields stay in extra_json; GST/TDS/Fixed-Asset specifics get
their own structured tables (app/models/structured_datasets.py), not
buried in JSON.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # engagement_id is on nearly every query (Blueprint Section E —
        # every screen is engagement-scoped); dataset_type is the second
        # most common filter (rules pull "just the JE rows", etc.).
        Index("ix_transactions_engagement_dataset", "engagement_id", "dataset_type"),
    )

    transaction_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_files.file_id"), default=None)
    # Enum: TB / GL / JE / SALES / PURCHASE / BANK / AR / AP / FIXED_ASSETS / GST / TDS
    dataset_type: Mapped[str] = mapped_column()
    transaction_date: Mapped[str | None] = mapped_column(default=None)
    account_name: Mapped[str | None] = mapped_column(default=None)
    party_name: Mapped[str | None] = mapped_column(default=None)
    description: Mapped[str | None] = mapped_column(default=None)
    debit_amount: Mapped[int | None] = mapped_column(default=None)  # paise
    credit_amount: Mapped[int | None] = mapped_column(default=None)  # paise
    reference_number: Mapped[str | None] = mapped_column(default=None)
    is_manual_entry: Mapped[bool | None] = mapped_column(default=None)
    # Promoted out of extra_json (Correction #8) — read by multiple tax
    # rules (40A(3), 269SS/269T, 269ST) and bank-data checks.
    # Enum: CASH / CHEQUE / NEFT_RTGS / UPI / DD / OTHER / UNKNOWN
    payment_mode: Mapped[str | None] = mapped_column(default=None)
    extra_json: Mapped[str | None] = mapped_column(default=None)  # genuinely one-off fields only
    created_at: Mapped[str] = mapped_column()

    # gst_line_items / tds_line_items reference transactions.transaction_id
    # (Blueprint Section 2.8/2.9); fixed_assets does NOT — it links to
    # engagement_id/file_id only, since an asset register row isn't itself
    # a ledger transaction. No back-relationship declared here to avoid
    # a spurious FK assumption; query structured_datasets by
    # transaction_id/engagement_id directly where needed.
