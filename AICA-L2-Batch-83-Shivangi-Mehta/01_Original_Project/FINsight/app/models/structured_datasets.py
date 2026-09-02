"""
FixedAsset, GstLineItem, TdsLineItem — Blueprint Section 2.7/2.8/2.9
(Correction #8: structured tables instead of JSON for fields that need
repeated numeric comparison — depreciation variance, GST reconciliation,
TDS rate consistency).

Implementation note (flagged, not a schema change): Blueprint Section C
predates these v0.2 tables and did not name a models file for them. Kept
in one new file rather than three, and rather than folding them into
transactions.py, to keep that file focused on the generic ledger shape.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FixedAsset(Base):
    __tablename__ = "fixed_assets"
    __table_args__ = (Index("ix_fixed_assets_engagement", "engagement_id"),)

    asset_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_files.file_id"), default=None)
    asset_description: Mapped[str | None] = mapped_column(default=None)
    # e.g. Plant & Machinery, Building, CWIP, Intangible — CWIP tag drives
    # AS16-BC-006 (Blueprint Section 3); absence -> "insufficient data",
    # never a guessed answer.
    asset_class: Mapped[str | None] = mapped_column(default=None)
    date_put_to_use: Mapped[str | None] = mapped_column(default=None)  # absence is itself a data-quality flag
    original_cost_paise: Mapped[int | None] = mapped_column(default=None)
    opening_wdv_paise: Mapped[int | None] = mapped_column(default=None)
    additions_paise: Mapped[int | None] = mapped_column(default=None)
    deletions_paise: Mapped[int | None] = mapped_column(default=None)
    book_depreciation_rate: Mapped[float | None] = mapped_column(default=None)  # percentage, not money
    book_depreciation_amount_paise: Mapped[int | None] = mapped_column(default=None)
    tax_block_of_asset: Mapped[str | None] = mapped_column(default=None)  # drives TAX-DEP-005
    tax_depreciation_rate: Mapped[float | None] = mapped_column(default=None)
    closing_wdv_paise: Mapped[int | None] = mapped_column(default=None)


class GstLineItem(Base):
    __tablename__ = "gst_line_items"
    __table_args__ = (
        Index("ix_gst_line_items_engagement", "engagement_id"),
        # TAX-GST-009 reconciles the SAME invoice_number across
        # SALES/PURCHASE/GST source_dataset rows — this is the join key.
        Index("ix_gst_line_items_invoice", "engagement_id", "invoice_number"),
    )

    gst_line_id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.transaction_id"), default=None)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    gstin: Mapped[str | None] = mapped_column(default=None)
    invoice_number: Mapped[str | None] = mapped_column(default=None)
    invoice_date: Mapped[str | None] = mapped_column(default=None)
    taxable_value_paise: Mapped[int | None] = mapped_column(default=None)
    cgst_paise: Mapped[int | None] = mapped_column(default=None)
    sgst_paise: Mapped[int | None] = mapped_column(default=None)
    igst_paise: Mapped[int | None] = mapped_column(default=None)
    tax_rate: Mapped[float | None] = mapped_column(default=None)
    # SALES / PURCHASE / GST — which file this line came from; reconciliation
    # (TAX-GST-009) compares the same invoice across multiple source_dataset values.
    source_dataset: Mapped[str | None] = mapped_column(default=None)


class TdsLineItem(Base):
    __tablename__ = "tds_line_items"
    __table_args__ = (Index("ix_tds_line_items_engagement", "engagement_id"),)

    tds_line_id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.transaction_id"), default=None)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    section_code: Mapped[str | None] = mapped_column(default=None)  # e.g. "194C"
    deductee_pan: Mapped[str | None] = mapped_column(default=None)
    rate_applied: Mapped[float | None] = mapped_column(default=None)
    amount_deducted_paise: Mapped[int | None] = mapped_column(default=None)
    challan_number: Mapped[str | None] = mapped_column(default=None)
    deposit_date: Mapped[str | None] = mapped_column(default=None)
