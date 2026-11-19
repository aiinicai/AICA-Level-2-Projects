"""Data model. Every synced table carries id (uuid), company_id, updated_at, updated_by.

Tables marked SYNCED travel through the outbox to the LAN PostgreSQL master.
Master caches are NOT synced: each PC re-reads them from Tally.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class SyncMixin:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, index=True)
    updated_by: Mapped[str] = mapped_column(String(80), default="")


# ------------------------------------------------------------------ SYNCED
class Company(SyncMixin, Base):
    __tablename__ = "companies"
    tally_guid: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state: Mapped[str] = mapped_column(String(80), default="")
    tally_host: Mapped[str] = mapped_column(String(120), default="localhost")
    tally_port: Mapped[int] = mapped_column(Integer, default=9000)
    voucher_style: Mapped[str] = mapped_column(String(30), default="purchase_accounting")
    # purchase_item | purchase_accounting | journal
    itc_pending_2b: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)   # narration template, TDS cfg, folders


class Vendor(SyncMixin, Base):
    __tablename__ = "vendors"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    vendor_key: Mapped[str] = mapped_column(String(120), index=True)   # GSTIN | PAN:xxx | BANK:hash | NAME:norm
    gstin: Mapped[str] = mapped_column(String(15), default="")
    pan: Mapped[str] = mapped_column(String(10), default="")
    names: Mapped[list] = mapped_column(JSON, default=list)
    party_ledger: Mapped[str] = mapped_column(String(255), default="")
    tds_section: Mapped[str] = mapped_column(String(30), default="")
    rcm: Mapped[bool] = mapped_column(Boolean, default=False)
    credit_days: Mapped[int] = mapped_column(Integer, default=0)
    voucher_style: Mapped[str] = mapped_column(String(30), default="")      # "" = company default
    tds_ledger: Mapped[str] = mapped_column(String(255), default="")
    tds_rate: Mapped[float] = mapped_column(Float, default=0.0)
    __table_args__ = (UniqueConstraint("company_id", "vendor_key"),)


class MappingRule(SyncMixin, Base):
    __tablename__ = "mapping_rules"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    vendor_key: Mapped[str] = mapped_column(String(120), index=True)
    hsn: Mapped[str] = mapped_column(String(10), default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    target_kind: Mapped[str] = mapped_column(String(10), default="ledger")  # ledger | stock
    target_name: Mapped[str] = mapped_column(String(255))
    blocked_17_5: Mapped[bool] = mapped_column(Boolean, default=False)
    rcm: Mapped[bool] = mapped_column(Boolean, default=False)
    hits: Mapped[int] = mapped_column(Integer, default=0)
    overrides: Mapped[int] = mapped_column(Integer, default=0)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="user")   # user | warm_start
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class JournalTemplate(SyncMixin, Base):
    __tablename__ = "journal_templates"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    voucher_type: Mapped[str] = mapped_column(String(80), default="Journal")
    lines: Mapped[list] = mapped_column(JSON, default=list)   # [{ledger, side, expr}]
    narration: Mapped[str] = mapped_column(Text, default="")
    origin: Mapped[str] = mapped_column(String(20), default="user")  # user | learned


class BankRule(SyncMixin, Base):
    """Learned: narration keywords on a bank line -> counter ledger."""
    __tablename__ = "bank_rules"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    bank_ledger: Mapped[str] = mapped_column(String(255), default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    direction: Mapped[str] = mapped_column(String(4), default="")        # out | in | "" (either)
    ledger: Mapped[str] = mapped_column(String(255))
    hits: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BankLine(SyncMixin, Base):
    __tablename__ = "bank_lines"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    bank_ledger: Mapped[str] = mapped_column(String(255))
    line_hash: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[str] = mapped_column(String(8))
    narration: Mapped[str] = mapped_column(Text, default="")
    reference: Mapped[str] = mapped_column(String(120), default="")
    withdrawal: Mapped[float] = mapped_column(Float, default=0.0)
    deposit: Mapped[float] = mapped_column(Float, default=0.0)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="new")     # new | posted | in_tally | skipped
    __table_args__ = (UniqueConstraint("company_id", "bank_ledger", "line_hash"),)


class Invoice(SyncMixin, Base):
    __tablename__ = "invoices"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    extraction: Mapped[dict] = mapped_column(JSON, default=dict)
    extraction_source: Mapped[str] = mapped_column(String(10), default="")  # qr|text|docx|ocr|gemini
    validation: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status_2b: Mapped[str] = mapped_column(String(20), default="unchecked")
    status: Mapped[str] = mapped_column(String(20), default="new")  # new|review|approved|posted|exception
    __table_args__ = (UniqueConstraint("company_id", "file_hash"),)


class Posting(SyncMixin, Base):
    __tablename__ = "postings"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    voucher_xml: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, default="")
    tally_master_id: Mapped[str] = mapped_column(String(40), default="")
    ok: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(SyncMixin, Base):
    __tablename__ = "audit_log"
    company_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(40), default="")
    entity_id: Mapped[str] = mapped_column(String(32), default="")
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)


class CompanyLock(Base):
    """Lives on the master DB when online (local when offline). One poster per company."""
    __tablename__ = "company_locks"
    company_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    holder: Mapped[str] = mapped_column(String(120))      # user@host#machine
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SupplierLayout(SyncMixin, Base):
    """How one supplier's invoices look, learned from approved invoices, so they can be read offline."""
    __tablename__ = "supplier_layouts"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    vendor_key: Mapped[str] = mapped_column(String(120), index=True)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)     # field -> {"labels": [...], "pattern": str}
    samples: Mapped[int] = mapped_column(Integer, default=0)
    successes: Mapped[int] = mapped_column(Integer, default=0)   # offline reads that passed all checks
    __table_args__ = (UniqueConstraint("company_id", "vendor_key"),)


class BankMapping(SyncMixin, Base):
    """Column mapping of one bank's statement layout, keyed by a fingerprint of its header row."""
    __tablename__ = "bank_mappings"
    signature: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")         # e.g. "IndusInd"
    header: Mapped[list] = mapped_column(JSON, default=list)
    mapping: Mapped[dict] = mapped_column(JSON, default=dict)          # field -> column index
    date_format: Mapped[str] = mapped_column(String(20), default="")   # "" = auto, "dmy" | "mdy"


class RecurringEntry(SyncMixin, Base):
    """Rent, salary, AMC, EMI...: a voucher that falls due on a schedule."""
    __tablename__ = "recurring_entries"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    voucher_type: Mapped[str] = mapped_column(String(80), default="Journal")
    base_type: Mapped[str] = mapped_column(String(20), default="Journal")
    lines: Mapped[list] = mapped_column(JSON, default=list)       # [{ledger, dr, amount}]
    narration: Mapped[str] = mapped_column(Text, default="")      # {month} {year} {period} placeholders
    frequency: Mapped[str] = mapped_column(String(12), default="monthly")   # monthly | quarterly | yearly
    day: Mapped[int] = mapped_column(Integer, default=1)          # 1-28, or 31 = month end
    next_due: Mapped[str] = mapped_column(String(8), default="")  # YYYYMMDD
    last_posted: Mapped[str] = mapped_column(String(8), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RedFlagReview(SyncMixin, Base):
    """Reviewer's decision on a red flag (or on every flag of one rule for one party)."""
    __tablename__ = "red_flag_reviews"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    key: Mapped[str] = mapped_column(String(64), index=True)       # flag key, or "rule:<id>|party:<name>"
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | explained | false_positive
    note: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str] = mapped_column(String(120), default="")
    reviewed_at: Mapped[str] = mapped_column(String(20), default="")
    __table_args__ = (UniqueConstraint("company_id", "key"),)


class ClaimLine(SyncMixin, Base):
    """One bill in an employee reimbursement claim or the petty-cash book (kind: reimb | petty)."""
    __tablename__ = "claim_lines"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="reimb")
    batch: Mapped[str] = mapped_column(String(120), default="", index=True)
    file_path: Mapped[str] = mapped_column(Text, default="")
    file_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    employee: Mapped[str] = mapped_column(String(120), default="")
    date: Mapped[str] = mapped_column(String(8), default="")
    supplier: Mapped[str] = mapped_column(String(255), default="")
    supplier_gstin: Mapped[str] = mapped_column(String(15), default="")
    buyer_gstin: Mapped[str] = mapped_column(String(15), default="")
    bill_no: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[str] = mapped_column(String(24), default="0")          # bill total (Decimal as text)
    taxable: Mapped[str] = mapped_column(String(24), default="0")
    cgst: Mapped[str] = mapped_column(String(24), default="0")
    sgst: Mapped[str] = mapped_column(String(24), default="0")
    igst: Mapped[str] = mapped_column(String(24), default="0")
    gst_claim: Mapped[bool] = mapped_column(Boolean, default=False)
    expense_ledger: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="new")        # new | posted | skipped
    tally_id: Mapped[str] = mapped_column(String(40), default="")
    issues: Mapped[list] = mapped_column(JSON, default=list)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class ExportRecord(SyncMixin, Base):
    """FIRC / e-BRC details and invoice allocation for one foreign-currency receipt (keyed by Tally voucher GUID)."""
    __tablename__ = "export_records"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    voucher_guid: Mapped[str] = mapped_column(String(80), index=True)
    firc_no: Mapped[str] = mapped_column(String(80), default="")
    firc_date: Mapped[str] = mapped_column(String(8), default="")
    ebrc_no: Mapped[str] = mapped_column(String(80), default="")
    ebrc_date: Mapped[str] = mapped_column(String(8), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    allocation: Mapped[dict] = mapped_column(JSON, default=dict)          # invoice key -> foreign amount
    __table_args__ = (UniqueConstraint("company_id", "voucher_guid"),)


SYNCED_MODELS = [Company, Vendor, MappingRule, JournalTemplate, Invoice, Posting, AuditLog, BankRule, BankLine,
                 SupplierLayout, BankMapping, RecurringEntry, RedFlagReview, ClaimLine, ExportRecord]

# ------------------------------------------------------------------ LOCAL ONLY
class MasterCache(Base):
    __tablename__ = "masters_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # ledger|group|stock_item|unit|godown|voucher_type
    guid: Mapped[str] = mapped_column(String(80), default="")
    name: Mapped[str] = mapped_column(String(255), index=True)
    parent: Mapped[str] = mapped_column(String(255), default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VoucherHistory(Base):
    __tablename__ = "voucher_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(String(32), index=True)
    guid: Mapped[str] = mapped_column(String(80), index=True)
    masterid: Mapped[str] = mapped_column(String(40), default="")
    date: Mapped[str] = mapped_column(String(8))          # YYYYMMDD as Tally sends it
    voucher_type: Mapped[str] = mapped_column(String(80), index=True)
    number: Mapped[str] = mapped_column(String(80), default="")
    party: Mapped[str] = mapped_column(String(255), default="")
    reference: Mapped[str] = mapped_column(String(120), default="")
    narration: Mapped[str] = mapped_column(Text, default="")
    entries: Mapped[list] = mapped_column(JSON, default=list)  # [{ledger, amount, dr}]


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table: Mapped[str] = mapped_column(String(40))
    row_id: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SyncState(Base):
    __tablename__ = "sync_state"
    table: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_pull: Mapped[datetime] = mapped_column(DateTime)
