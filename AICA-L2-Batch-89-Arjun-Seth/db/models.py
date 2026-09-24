# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""SQLAlchemy ORM models for LeaseIQ Pro.

Design rules
------------
* ``LeaseCase`` is the central entity. Its primary key is ``case_id`` and every
  other table (except ``users``) carries a foreign key back to it.
* Amendments never overwrite the original record: an amendment is a NEW
  ``LeaseCase`` row linked to the original through ``parent_case_id`` and
  described by a ``LeaseVersion`` row.
* Money columns use ``Float`` because SQLite has no native decimal type; the
  calculation engine works in floats/pandas and reconciles to within 1 rupee.
* Some field-level columns are extensions added during development.

No Streamlit imports belong in this module.
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --------------------------------------------------------------------------- #
# Allowed values (single source of truth, reused by UI and tests)
# --------------------------------------------------------------------------- #
LEASE_STATUSES = (
    "Draft",
    "Pending Review",
    "Approved",
    "Active",
    "Expired",
    "Terminated",
)
ROU_METHODS = ("gross_accum", "net_direct")
FRAMEWORKS = ("IND_AS_116", "ASC_842")
USER_ROLES = ("Preparer", "Reviewer", "Admin")  # single-role MVP is acceptable
CONFIDENCE_LEVELS = ("High", "Medium", "Low")
ASC842_CLASSIFICATIONS = ("FINANCE LEASE", "OPERATING LEASE")
IND_AS116_EXEMPTIONS = ("EXEMPT", "ON-BALANCE SHEET")
NUMBER_FORMATS = ("indian", "international")  # display grouping: 5,00,000 or 5,000,000


def _in_list(column: str, values: tuple) -> str:
    """Build a SQL ``column IN ('a', 'b')`` expression for CheckConstraints."""
    quoted = ", ".join("'{}'".format(v) for v in values)
    return "{} IN ({})".format(column, quoted)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _case_fk(nullable: bool = False, ondelete: str = "CASCADE"):
    """Foreign key back to the central LeaseCase entity (fresh column per call)."""
    return mapped_column(
        Integer,
        ForeignKey("lease_cases.case_id", ondelete=ondelete),
        nullable=nullable,
        index=True,
    )


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in_list("role", USER_ROLES), name="ck_users_role"),
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # not used in this edition (no sign-in)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="Preparer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    # Multi-user: NULL workspace_id = this account owns its workspace; otherwise it is the Admin who does. access_level
    # (see core.permissions) is what the person may do; NULL = derive it from ``role`` (accounts made before this existed).
    workspace_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.user_id"))
    access_level: Mapped[Optional[str]] = mapped_column(String(20))
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.user_id"))
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    lease_cases: Mapped[list["LeaseCase"]] = relationship(back_populates="owner")


# --------------------------------------------------------------------------- #
# UserPreference - display settings (a separate table so existing databases just gain it)
# --------------------------------------------------------------------------- #
class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint(_in_list("number_format", NUMBER_FORMATS), name="ck_user_preferences_number_format"),
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    number_format: Mapped[str] = mapped_column(String(20), nullable=False, default="indian")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    # Appearance (validated in core.workflow.save_user_preferences / core.themes)
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default="light", server_default="light")
    dashboard_layout: Mapped[str] = mapped_column(String(20), nullable=False, default="classic", server_default="classic")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)


# --------------------------------------------------------------------------- #
# LeaseCase - the central entity
# --------------------------------------------------------------------------- #
class LeaseCase(Base):
    __tablename__ = "lease_cases"
    __table_args__ = (
        CheckConstraint(_in_list("status", LEASE_STATUSES), name="ck_lease_cases_status"),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False, index=True
    )  # tenant isolation: every query filters on this (Section 4)

    # Approval workflow status (Section 4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Draft", index=True)

    # Descriptive / denormalised fields used by the dashboard's Recent Leases table
    lease_ref: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    lessor_name: Mapped[Optional[str]] = mapped_column(String(255))
    lessee_name: Mapped[Optional[str]] = mapped_column(String(255))
    asset_type: Mapped[Optional[str]] = mapped_column(String(100))
    commencement_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    term_months: Mapped[Optional[int]] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    reporting_framework: Mapped[str] = mapped_column(String(20), nullable=False, default="BOTH")
    classification_override: Mapped[Optional[str]] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="upload")  # upload|bulk|manual

    inputs_json: Mapped[Optional[str]] = mapped_column(Text)  # validated inputs used for the calculation
    # Why a Reviewer sent the lease back. A rejected lease is a Draft with this set (shown as "Rejected");
    # it is cleared when the lease is corrected and resubmitted (the audit log keeps the history).
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Amendments: NEW case row pointing at the original (Section 15)
    parent_case_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("lease_cases.case_id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="lease_cases")
    parent: Mapped[Optional["LeaseCase"]] = relationship(
        back_populates="amendments", remote_side=[case_id]
    )
    amendments: Mapped[list["LeaseCase"]] = relationship(back_populates="parent")

    documents: Mapped[list["AgreementDocument"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    extracted_fields: Mapped[list["ExtractedFields"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    classification_results: Mapped[list["ClassificationResult"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    calculation_results: Mapped[list["CalculationResult"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    payment_components: Mapped[list["PaymentComponent"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    amortization_rows: Mapped[list["AmortizationSchedule"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    disclosure_notes: Mapped[list["DisclosureNote"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    technical_memos: Mapped[list["TechnicalMemo"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    comparison_results: Mapped[list["ComparisonResult"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    # AuditLog and LeaseVersion are reached by query: LeaseVersion has two FKs
    # to this table, and audit history should not be silently cascade-deleted.


# --------------------------------------------------------------------------- #
# AgreementDocument
# --------------------------------------------------------------------------- #
class AgreementDocument(Base):
    __tablename__ = "agreement_documents"

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | docx | xlsx
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    raw_llm_json: Mapped[Optional[str]] = mapped_column(Text)  # raw extraction response
    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    case: Mapped["LeaseCase"] = relationship(back_populates="documents")


# --------------------------------------------------------------------------- #
# ExtractedFields (one row per field per case)
# --------------------------------------------------------------------------- #
class ExtractedFields(Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (
        UniqueConstraint("case_id", "field_key", name="uq_extracted_fields_case_field"),
        CheckConstraint(
            "confidence IS NULL OR " + _in_list("confidence", CONFIDENCE_LEVELS),
            name="ck_extracted_fields_confidence",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agreement_documents.document_id"))
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    ai_value: Mapped[Optional[str]] = mapped_column(Text)
    final_value: Mapped[Optional[str]] = mapped_column(Text)  # set on "Confirm & Proceed"
    confidence: Mapped[Optional[str]] = mapped_column(String(10))
    source_snippet: Mapped[Optional[str]] = mapped_column(Text)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    edited_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    case: Mapped["LeaseCase"] = relationship(back_populates="extracted_fields")


# --------------------------------------------------------------------------- #
# ClassificationResult
# --------------------------------------------------------------------------- #
class ClassificationResult(Base):
    __tablename__ = "classification_results"
    __table_args__ = (
        CheckConstraint(
            _in_list("asc842_classification", ASC842_CLASSIFICATIONS),
            name="ck_classification_asc842",
        ),
        CheckConstraint(
            _in_list("ind_as116_exemption", IND_AS116_EXEMPTIONS),
            name="ck_classification_indas116",
        ),
        CheckConstraint(_in_list("rou_method", ROU_METHODS), name="ck_classification_rou_method"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    asc842_classification: Mapped[str] = mapped_column(String(20), nullable=False)
    asc842_test_results_json: Mapped[str] = mapped_column(Text, nullable=False)  # the 5 tests
    ind_as116_exemption: Mapped[str] = mapped_column(String(20), nullable=False)
    ind_as116_rationale: Mapped[Optional[str]] = mapped_column(Text)
    rou_method: Mapped[str] = mapped_column(String(15), nullable=False)  # downstream method flag
    is_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    case: Mapped["LeaseCase"] = relationship(back_populates="classification_results")


# --------------------------------------------------------------------------- #
# CalculationResult (initial measurement summary + totals)
# --------------------------------------------------------------------------- #
class CalculationResult(Base):
    __tablename__ = "calculation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    inputs_json: Mapped[Optional[str]] = mapped_column(Text)
    monthly_rate: Mapped[Optional[float]] = mapped_column(Float)
    lease_liability_initial: Mapped[Optional[float]] = mapped_column(Float)
    security_deposit_pv: Mapped[Optional[float]] = mapped_column(Float)
    security_deposit_discount: Mapped[Optional[float]] = mapped_column(Float)
    rou_asset_gross: Mapped[Optional[float]] = mapped_column(Float)
    total_contractual_rent: Mapped[Optional[float]] = mapped_column(Float)
    other_rou_components: Mapped[Optional[float]] = mapped_column(Float)
    total_straight_line_base: Mapped[Optional[float]] = mapped_column(Float)
    single_lease_cost_per_month: Mapped[Optional[float]] = mapped_column(Float)
    total_interest_expense: Mapped[Optional[float]] = mapped_column(Float)
    total_undiscounted_payments: Mapped[Optional[float]] = mapped_column(Float)
    engine_version: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    case: Mapped["LeaseCase"] = relationship(back_populates="calculation_results")


# --------------------------------------------------------------------------- #
# PaymentComponent
# --------------------------------------------------------------------------- #
class PaymentComponent(Base):
    __tablename__ = "payment_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    # base_rent | escalated_rent | prepaid_rent | security_deposit | idc |
    # restoration_cost | incentive | other
    component_type: Mapped[str] = mapped_column(String(30), nullable=False)
    period_number: Mapped[Optional[int]] = mapped_column(Integer)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    case: Mapped["LeaseCase"] = relationship(back_populates="payment_components")


# --------------------------------------------------------------------------- #
# AmortizationSchedule (one row per period per framework)
# --------------------------------------------------------------------------- #
class AmortizationSchedule(Base):
    __tablename__ = "amortization_schedules"
    __table_args__ = (
        UniqueConstraint("case_id", "framework", "period", name="uq_amortization_case_fw_period"),
        CheckConstraint(_in_list("rou_method", ROU_METHODS), name="ck_amortization_rou_method"),
        CheckConstraint(_in_list("framework", FRAMEWORKS), name="ck_amortization_framework"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    framework: Mapped[str] = mapped_column(String(15), nullable=False)
    rou_method: Mapped[str] = mapped_column(String(15), nullable=False)  # "gross_accum" | "net_direct"

    period: Mapped[int] = mapped_column(Integer, nullable=False)
    period_date: Mapped[Optional[date]] = mapped_column(Date)
    escalated_contractual_rent: Mapped[Optional[float]] = mapped_column(Float)
    net_cash_payment: Mapped[Optional[float]] = mapped_column(Float)
    opening_liability: Mapped[Optional[float]] = mapped_column(Float)
    interest_expense: Mapped[Optional[float]] = mapped_column(Float)
    principal_repayment: Mapped[Optional[float]] = mapped_column(Float)
    closing_liability: Mapped[Optional[float]] = mapped_column(Float)

    # gross_accum only (Ind AS 116 / ASC 842 Finance); NULL for net_direct rows
    rou_gross_cost: Mapped[Optional[float]] = mapped_column(Float)
    accum_amortization_opening: Mapped[Optional[float]] = mapped_column(Float)
    amortization_expense: Mapped[Optional[float]] = mapped_column(Float)
    accum_amortization_closing: Mapped[Optional[float]] = mapped_column(Float)

    # net_direct only (ASC 842 Operating); NULL for gross_accum rows
    single_lease_cost: Mapped[Optional[float]] = mapped_column(Float)
    rou_reduction_plug: Mapped[Optional[float]] = mapped_column(Float)

    rou_net_carrying_value: Mapped[Optional[float]] = mapped_column(Float)  # both methods
    security_deposit_opening: Mapped[Optional[float]] = mapped_column(Float)
    security_deposit_closing: Mapped[Optional[float]] = mapped_column(Float)

    case: Mapped["LeaseCase"] = relationship(back_populates="amortization_rows")


# --------------------------------------------------------------------------- #
# JournalEntry (one row per journal line)
# --------------------------------------------------------------------------- #
class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(_in_list("entry_type", ("DAY1", "PERIODIC")), name="ck_journal_entry_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False)  # DAY1 | PERIODIC
    leg: Mapped[Optional[str]] = mapped_column(String(1))  # A | B | C for Day-1 legs
    framework: Mapped[Optional[str]] = mapped_column(String(15))
    period_number: Mapped[Optional[int]] = mapped_column(Integer)
    entry_date: Mapped[Optional[date]] = mapped_column(Date)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    account: Mapped[str] = mapped_column(String(150), nullable=False)
    debit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    credit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    narration: Mapped[Optional[str]] = mapped_column(String(255))
    is_balanced: Mapped[Optional[bool]] = mapped_column(Boolean)  # leg/entry-level flag

    case: Mapped["LeaseCase"] = relationship(back_populates="journal_entries")


# --------------------------------------------------------------------------- #
# DisclosureNote
# --------------------------------------------------------------------------- #
class DisclosureNote(Base):
    __tablename__ = "disclosure_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    # maturity_analysis | rou_rollforward_finance | rou_rollforward_operating | weighted_averages
    note_type: Mapped[str] = mapped_column(String(40), nullable=False)
    framework: Mapped[Optional[str]] = mapped_column(String(15))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    case: Mapped["LeaseCase"] = relationship(back_populates="disclosure_notes")


# --------------------------------------------------------------------------- #
# TechnicalMemo (versioned)
# --------------------------------------------------------------------------- #
class TechnicalMemo(Base):
    __tablename__ = "technical_memos"
    __table_args__ = (
        UniqueConstraint("case_id", "version_number", name="uq_technical_memos_case_version"),
    )

    memo_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    case: Mapped["LeaseCase"] = relationship(back_populates="technical_memos")


# --------------------------------------------------------------------------- #
# AuditLog
# --------------------------------------------------------------------------- #
class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # case_id is nullable so non-case events (login/logout) can be logged AND so the trail of a DELETED lease
    # survives it: deleting a lease detaches its audit rows (case_id -> NULL, lease_ref keeps its ID) instead of
    # removing them. New databases use ON DELETE SET NULL here; databases created earlier still have CASCADE, which is
    # why ``core.workflow.delete_case`` detaches the rows explicitly first.
    case_id: Mapped[Optional[int]] = _case_fk(nullable=True, ondelete="SET NULL")
    lease_ref: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # set when the lease is deleted
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    field_name: Mapped[Optional[str]] = mapped_column(String(100))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow, index=True)


# --------------------------------------------------------------------------- #
# ComparisonResult (Ind AS 116 vs ASC 842)
# --------------------------------------------------------------------------- #
class ComparisonResult(Base):
    __tablename__ = "comparison_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    ind_as116_classification: Mapped[Optional[str]] = mapped_column(String(20))
    asc842_classification: Mapped[Optional[str]] = mapped_column(String(20))
    ind_as116_lease_liability: Mapped[Optional[float]] = mapped_column(Float)
    asc842_lease_liability: Mapped[Optional[float]] = mapped_column(Float)
    ind_as116_rou_asset: Mapped[Optional[float]] = mapped_column(Float)
    asc842_rou_asset: Mapped[Optional[float]] = mapped_column(Float)
    ind_as116_total_expense: Mapped[Optional[float]] = mapped_column(Float)
    asc842_total_expense: Mapped[Optional[float]] = mapped_column(Float)
    comparison_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    case: Mapped["LeaseCase"] = relationship(back_populates="comparison_results")


# --------------------------------------------------------------------------- #
# LeaseVersion (amendment tracking)
# --------------------------------------------------------------------------- #
class LeaseVersion(Base):
    """Links an amended LeaseCase (``case_id``) to the original (``parent_case_id``).

    Amendments never overwrite the original row: ``case_id`` is the NEW case
    holding the re-measured figures, ``parent_case_id`` is the original.
    """

    __tablename__ = "lease_versions"
    __table_args__ = (
        UniqueConstraint("parent_case_id", "version_number", name="uq_lease_versions_parent_version"),
        CheckConstraint("case_id <> parent_case_id", name="ck_lease_versions_distinct_cases"),
    )

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = _case_fk()
    parent_case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lease_cases.case_id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amendment_type: Mapped[Optional[str]] = mapped_column(String(50))
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    case: Mapped["LeaseCase"] = relationship(foreign_keys=[case_id])
    parent_case: Mapped["LeaseCase"] = relationship(foreign_keys=[parent_case_id])
