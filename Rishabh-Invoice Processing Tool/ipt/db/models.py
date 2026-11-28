"""Phase 1 tables. Later phases ADD tables; existing columns are changed
only through Alembic migrations (introduced in Phase 2) so user data is
never lost on upgrade. Every business table carries company_id + fy_id.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ipt.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(),
                                                 onupdate=func.current_timestamp())


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    gstin: Mapped[str | None] = mapped_column(String(15), unique=True, nullable=True)
    state_code: Mapped[str] = mapped_column(String(2))
    address: Mapped[str] = mapped_column(Text, default="")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    tally_company_name: Mapped[str] = mapped_column(String(200), default="")
    tally_version: Mapped[str] = mapped_column(String(60), default="")
    tally_host: Mapped[str] = mapped_column(String(120), default="localhost")
    tally_port: Mapped[int] = mapped_column(Integer, default=9000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    folder_name: Mapped[str] = mapped_column(String(255))
    financial_years: Mapped[list["FinancialYear"]] = relationship(
        back_populates="company", cascade="all, delete-orphan", order_by="FinancialYear.start_date")


class FinancialYear(TimestampMixin, Base):
    __tablename__ = "financial_years"
    __table_args__ = (UniqueConstraint("company_id", "label", name="uq_fy_company_label"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(7))  # e.g. 2026-27
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    books_begin_date: Mapped[date] = mapped_column(Date)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    company: Mapped[Company] = relationship(back_populates="financial_years")


class AuditLog(Base):
    """Append-only. Services never update or delete rows here."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(60), default="system")
    company_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60), default="")
    before_json: Mapped[str] = mapped_column(Text, default="")
    after_json: Mapped[str] = mapped_column(Text, default="")
    remark: Mapped[str] = mapped_column(Text, default="")


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------- Phase 2
from decimal import Decimal  # noqa: E402

from sqlalchemy import Numeric  # noqa: E402

MONEY = Numeric(18, 2)
RATE = Numeric(6, 3)


class Document(TimestampMixin, Base):
    """An uploaded file. The original is copied, never modified."""
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))  # relative to data folder
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str] = mapped_column(String(60), default="")
    # queued | processing | extracted | needs_review | failed
    status: Mapped[str] = mapped_column(String(20), default="queued")
    method: Mapped[str] = mapped_column(String(20), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    duplicate_of_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ExtractionResult(Base):
    """One row per extraction attempt (history is kept)."""
    __tablename__ = "extraction_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    method: Mapped[str] = mapped_column(String(20))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    fields_json: Mapped[str] = mapped_column(Text, default="")
    confidence_json: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("company_id", "gstin", name="uq_supplier_company_gstin"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    pan: Mapped[str] = mapped_column(String(10), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    state_code: Mapped[str] = mapped_column(String(2), default="")
    tally_ledger_name: Mapped[str] = mapped_column(String(200), default="")


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    # extracted | needs_review | validated | approved | rejected
    status: Mapped[str] = mapped_column(String(20), default="extracted", index=True)
    doc_type: Mapped[str] = mapped_column(String(20), default="tax_invoice")
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    supplier_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    supplier_pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    supplier_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    buyer_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    buyer_state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    invoice_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    invoice_no_normalized: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    po_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    original_invoice_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)
    eway_bill_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    irn: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ack_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    place_of_supply: Mapped[str | None] = mapped_column(String(2), nullable=True)
    reverse_charge: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    taxable_total: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    sgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    igst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cess: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    freight: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    packing: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    other_charges: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    round_off: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    tds: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    tcs: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    invoice_total: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    amount_in_words: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_confidence_json: Mapped[str] = mapped_column(Text, default="{}")
    remarks: Mapped[str] = mapped_column(Text, default="")
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1-based page range inside the document
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.line_no")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hsn_sac: Mapped[str | None] = mapped_column(String(10), nullable=True)
    qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    discount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    taxable_value: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    gst_rate: Mapped[Decimal | None] = mapped_column(RATE, nullable=True)
    cgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    sgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    igst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cess: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    total: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    invoice: Mapped[Invoice] = relationship(back_populates="items")


class ValidationResult(Base):
    __tablename__ = "validation_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    check_code: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))  # error | warning | ok
    field: Mapped[str] = mapped_column(String(40), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    expected: Mapped[str] = mapped_column(String(60), default="")
    found: Mapped[str] = mapped_column(String(60), default="")


# ---------------------------------------------------------------- Phase 3
class TallyMaster(Base):
    """Read-only copy of Tally masters for one IPT company (refreshed by Sync)."""
    __tablename__ = "tally_masters"
    __table_args__ = (UniqueConstraint("company_id", "master_type", "name", name="uq_tally_master"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    master_type: Mapped[str] = mapped_column(String(30), index=True)  # ledger, group, stock_item, unit, ...
    name: Mapped[str] = mapped_column(String(200))
    parent: Mapped[str] = mapped_column(String(200), default="")
    primary_group: Mapped[str] = mapped_column(String(200), default="")
    guid: Mapped[str] = mapped_column(String(100), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    hsn: Mapped[str] = mapped_column(String(10), default="")
    gst_rate: Mapped[Decimal | None] = mapped_column(RATE, nullable=True)
    base_unit: Mapped[str] = mapped_column(String(30), default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())


class MappingRule(TimestampMixin, Base):
    """Remembered mapping: entity + source key -> Tally master name."""
    __tablename__ = "mapping_rules"
    __table_args__ = (UniqueConstraint("company_id", "entity", "source_key", name="uq_mapping_rule"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    entity: Mapped[str] = mapped_column(String(30))       # party, stock_item, purchase_ledger, tax_ledger, ...
    source_key: Mapped[str] = mapped_column(String(200))  # GSTIN, normalised description, 'intra', 'CGST' ...
    tally_name: Mapped[str] = mapped_column(String(200))
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    approved_by: Mapped[str] = mapped_column(String(60), default="")


class TallyImport(Base):
    """Append-only log of every voucher sent to Tally and Tally's exact answer."""
    __tablename__ = "tally_imports"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    username: Mapped[str] = mapped_column(String(60), default="")
    tally_company: Mapped[str] = mapped_column(String(200), default="")
    request_xml_path: Mapped[str] = mapped_column(String(500), default="")
    response_xml: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[int] = mapped_column(Integer, default=0)
    altered: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    line_errors: Mapped[str] = mapped_column(Text, default="")
    tally_master_id: Mapped[str] = mapped_column(String(30), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="")  # success | failed | unverified
    remark: Mapped[str] = mapped_column(Text, default="")


# ============================================================== Phase 4 – GST reconciliation
class Gstr2bUpload(Base):
    """One GSTR-2B file for a return period. Only one upload per period is current; replaced ones
    stay as history."""
    __tablename__ = "gstr2b_uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7))            # YYYY-MM (return period)
    file_name: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64))
    stored_path: Mapped[str] = mapped_column(String(500), default="")
    source_format: Mapped[str] = mapped_column(String(10))    # json | excel
    return_gstin: Mapped[str] = mapped_column(String(15), default="")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    counts_json: Mapped[str] = mapped_column(Text, default="{}")
    skipped_json: Mapped[str] = mapped_column(Text, default="[]")
    uploaded_by: Mapped[str] = mapped_column(String(60), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())


class Gstr2bRecord(Base):
    __tablename__ = "gstr2b_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("gstr2b_uploads.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    section: Mapped[str] = mapped_column(String(12))           # B2B, B2BA, CDNR, CDNRA, ISD, ISDA, IMPG, IMPGSEZ
    supplier_gstin: Mapped[str] = mapped_column(String(15), default="", index=True)
    supplier_name: Mapped[str] = mapped_column(String(200), default="")
    doc_type: Mapped[str] = mapped_column(String(5), default="INV")   # INV | CRN | DBN | BOE | ISD
    doc_no: Mapped[str] = mapped_column(String(60), default="")
    doc_no_normalized: Mapped[str] = mapped_column(String(60), default="", index=True)
    doc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_doc_no: Mapped[str] = mapped_column(String(60), default="")
    original_doc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pos: Mapped[str] = mapped_column(String(2), default="")
    reverse_charge: Mapped[bool] = mapped_column(Boolean, default=False)
    invoice_value: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    taxable_value: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    igst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    sgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cess: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    itc_available: Mapped[str] = mapped_column(String(10), default="")   # Yes | No | Temporary
    itc_reason: Mapped[str] = mapped_column(String(200), default="")
    supplier_period: Mapped[str] = mapped_column(String(10), default="")
    supplier_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_ref: Mapped[str] = mapped_column(String(40), default="")      # sheet/row or JSON path


class PurchaseRegisterUpload(Base):
    """A purchase register loaded from an Excel export or fetched straight from Tally."""
    __tablename__ = "purchase_register_uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(10))            # excel | tally
    file_name: Mapped[str] = mapped_column(String(255), default="")
    file_sha256: Mapped[str] = mapped_column(String(64), default="")
    period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    rows_ok: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(60), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())


class PurchaseRegisterRecord(Base):
    __tablename__ = "purchase_register_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("purchase_register_uploads.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    row_no: Mapped[int] = mapped_column(Integer, default=0)
    voucher_no: Mapped[str] = mapped_column(String(60), default="")
    voucher_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    voucher_type: Mapped[str] = mapped_column(String(60), default="")
    doc_type: Mapped[str] = mapped_column(String(5), default="INV")
    party_name: Mapped[str] = mapped_column(String(200), default="")
    supplier_gstin: Mapped[str] = mapped_column(String(15), default="", index=True)
    supplier_invoice_no: Mapped[str] = mapped_column(String(60), default="")
    invoice_no_normalized: Mapped[str] = mapped_column(String(60), default="", index=True)
    supplier_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_ledger: Mapped[str] = mapped_column(String(200), default="")
    taxable_value: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    igst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    sgst: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cess: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    invoice_total: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    narration: Mapped[str] = mapped_column(Text, default="")
    tally_master_id: Mapped[str] = mapped_column(String(30), default="")


class PurchaseRegisterReject(Base):
    __tablename__ = "purchase_register_rejects"
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("purchase_register_uploads.id", ondelete="CASCADE"), index=True)
    row_no: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(Text, default="")
    raw_json: Mapped[str] = mapped_column(Text, default="")


class PrTemplate(TimestampMixin, Base):
    """Saved column mapping for a purchase register Excel layout."""
    __tablename__ = "pr_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    sheet: Mapped[str] = mapped_column(String(100), default="")
    header_row: Mapped[int] = mapped_column(Integer, default=1)
    mapping_json: Mapped[str] = mapped_column(Text, default="{}")


class ReconSetting(TimestampMixin, Base):
    __tablename__ = "recon_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), unique=True)
    taxable_tol: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("1.00"))
    tax_tol: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("1.00"))
    total_tol: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("1.00"))
    date_tol_days: Mapped[int] = mapped_column(Integer, default=0)
    similarity: Mapped[int] = mapped_column(Integer, default=90)


class ReconRun(Base):
    __tablename__ = "recon_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(20))               # ipt_tally | ipt_2b | tally_2b | three_way
    period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    counts_json: Mapped[str] = mapped_column(Text, default="{}")
    run_by: Mapped[str] = mapped_column(String(60), default="")
    run_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)


class ReconRow(Base):
    __tablename__ = "recon_rows"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("recon_runs.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    ipt_invoice_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gstr2b_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supplier_gstin: Mapped[str] = mapped_column(String(15), default="")
    supplier_name: Mapped[str] = mapped_column(String(200), default="")
    doc_no: Mapped[str] = mapped_column(String(60), default="")
    doc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    match_stage: Mapped[str] = mapped_column(String(20), default="")
    confidence: Mapped[Decimal | None] = mapped_column(RATE, nullable=True)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    differences_json: Mapped[str] = mapped_column(Text, default="{}")
    suggested_action: Mapped[str] = mapped_column(Text, default="")
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    action_status: Mapped[str] = mapped_column(String(20), default="Pending")
    remarks: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String(60), default="")


class ItcAnalysis(Base):
    """The user's ITC review of a reconciliation row. Eligibility is never decided automatically."""
    __tablename__ = "itc_analysis"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fy_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id", ondelete="CASCADE"), index=True)
    supplier_gstin: Mapped[str] = mapped_column(String(15), default="")
    doc_no_normalized: Mapped[str] = mapped_column(String(60), default="")
    doc_type: Mapped[str] = mapped_column(String(5), default="INV")
    itc_in_books: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    itc_in_2b: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    difference: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    eligibility: Mapped[str] = mapped_column(String(20), default="Pending review")
    reason: Mapped[str] = mapped_column(Text, default="")
    remarks: Mapped[str] = mapped_column(Text, default="")
    action_taken: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(60), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("company_id", "fy_id", "supplier_gstin", "doc_no_normalized", "doc_type"),)


# ============================================================== Phase 6 – backups
class Backup(Base):
    __tablename__ = "backups"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(20), default="manual")   # manual | scheduled | pre-restore
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_message: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())


# ============================================================== learned supplier layouts
class SupplierLayout(Base):
    """Where a supplier prints a field on its bills (page coordinates, 595 pt wide), learned from approved
    scanned invoices. Used only to read fields OCR could not place, never to override a confident reading."""
    __tablename__ = "supplier_layouts"
    __table_args__ = (UniqueConstraint("company_id", "supplier_gstin", "field", name="uq_supplier_layout"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    supplier_gstin: Mapped[str] = mapped_column(String(15), index=True)
    field: Mapped[str] = mapped_column(String(40))
    x0: Mapped[float] = mapped_column(Float)
    y0: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    samples: Mapped[int] = mapped_column(Integer, default=1)
    # the printed label next to the value ('Invoice No', 'Total') and the value's offset from it: scans of
    # the same supplier shift by several points, the label moves with the value
    anchor: Mapped[str] = mapped_column(String(80), default="")
    dx: Mapped[float] = mapped_column(Float, default=0.0)
    dy: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(),
                                                 onupdate=func.current_timestamp())
