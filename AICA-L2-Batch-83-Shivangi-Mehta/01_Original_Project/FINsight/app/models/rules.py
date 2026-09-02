"""
Standard + the four rule packs (AccountingRule, AuditRule, TaxRule,
SebiRule) + AuditAssertion/AuditRuleAssertion.

Mirrors Blueprint Section 2, D.6-D.10 plus the v0.2 revisions (2.2-2.6).
SCHEMA ONLY — this file defines the table shape that will hold rule
metadata; it contains zero rule content/rows and zero rule execution
logic. Populating actual rules (AS10-FA-001 etc.) is Stage 8-11, per
Stage 3 condition #5.

Implementation clarification (flagged, not a schema change): the v0.1
prose described audit_rules/tax_rules/sebi_rules loosely as "same shape
as accounting_rules." Taken literally that would give every rule table a
`framework` (AS/IND_AS) column, which is meaningless outside Accounting.
`framework` is kept ONLY on AccountingRule, where it is the approved hard
enum (Ambiguity #4); audit/tax/sebi already have their own equivalent
categorical fields (related_sa, legislative_act, lodr_regulation_ref).
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Shared enum reminder for every *_rules table's risk_level_default and
# verification_status columns (enforced at service layer, not DB level):
#   risk_level_default:   LOW / MEDIUM / HIGH / CRITICAL
#   verification_status:  VERIFIED / SOURCE_VERIFICATION_REQUIRED


class Standard(Base):
    __tablename__ = "standards"

    standard_id: Mapped[int] = mapped_column(primary_key=True)
    # Enum: AS / IND_AS / SA / IT_ACT_1961 / IT_ACT_2025 / SEBI_LODR
    framework: Mapped[str] = mapped_column()
    code: Mapped[str] = mapped_column(unique=True)  # e.g. "AS 10", "Ind AS 16", "SA 240" — one row per code
    title: Mapped[str] = mapped_column()
    source_reference: Mapped[str | None] = mapped_column(default=None)  # marked SVR in content where unverified
    effective_date: Mapped[str | None] = mapped_column(default=None)


class AccountingRule(Base):
    """Blueprint Section 2.5 / Section 3 (G.1). Framework-treatment
    questions only — never an audit-style risk indicator."""

    __tablename__ = "accounting_rules"

    rule_id: Mapped[str] = mapped_column(primary_key=True)  # e.g. "AS10-FA-001"
    standard_id: Mapped[int | None] = mapped_column(ForeignKey("standards.standard_id"), default=None)
    framework: Mapped[str] = mapped_column()  # AS / IND_AS — hard enum, Ambiguity #4
    topic: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    data_required: Mapped[str | None] = mapped_column(default=None)  # JSON list of dataset_types
    logic_summary: Mapped[str | None] = mapped_column(default=None)  # plain-English mirror for the UI
    risk_level_default: Mapped[str] = mapped_column(default="MEDIUM")
    suggested_action: Mapped[str | None] = mapped_column(default=None)
    suggested_query_template: Mapped[str | None] = mapped_column(default=None)
    version: Mapped[str | None] = mapped_column(default=None)
    effective_date: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=False)  # never True until rule content + tests exist (Stage 8)
    # --- Correction #4 fields ---
    applicability_preconditions: Mapped[str | None] = mapped_column(default=None)
    analytical_test: Mapped[str | None] = mapped_column(default=None)
    expected_result: Mapped[str | None] = mapped_column(default=None)
    knowledge_base_version: Mapped[str | None] = mapped_column(default=None)
    verification_status: Mapped[str] = mapped_column(default="VERIFIED")  # topic-level AS/Ind AS names are stable


class AuditRule(Base):
    """Blueprint Section 2.4 / Section 4 (G.2). Assertion-tagged risk
    indicators only — never a framework-treatment conclusion."""

    __tablename__ = "audit_rules"

    rule_id: Mapped[str] = mapped_column(primary_key=True)  # e.g. "AUD-JE-001"
    standard_id: Mapped[int | None] = mapped_column(ForeignKey("standards.standard_id"), default=None)
    topic: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    data_required: Mapped[str | None] = mapped_column(default=None)
    logic_summary: Mapped[str | None] = mapped_column(default=None)
    risk_level_default: Mapped[str] = mapped_column(default="MEDIUM")
    suggested_action: Mapped[str | None] = mapped_column(default=None)
    suggested_query_template: Mapped[str | None] = mapped_column(default=None)
    version: Mapped[str | None] = mapped_column(default=None)
    effective_date: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=False)
    related_sa: Mapped[str | None] = mapped_column(default=None)  # e.g. "SA 240"
    audit_area: Mapped[str | None] = mapped_column(default=None)  # e.g. "Journal Entry Testing"
    # --- Correction #3 field — always UI-prefixed "Suggested audit consideration:" ---
    suggested_audit_procedure: Mapped[str | None] = mapped_column(default=None)
    # --- Stage 9 Decision A (approved) — catalogue-level "Suggested Evidence"
    # text, e.g. "Approval workflow record, supporting voucher". Nullable,
    # same pattern as suggested_audit_procedure/suggested_query_template.
    # See database/migrations/versions/0002_audit_rules_suggested_evidence.py.
    suggested_evidence: Mapped[str | None] = mapped_column(default=None)
    verification_status: Mapped[str] = mapped_column(default="VERIFIED")

    assertion_links: Mapped[list["AuditRuleAssertion"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class TaxRule(Base):
    """Blueprint Section 2.6 / Section 5. GATED: verification_status
    defaults to SOURCE_VERIFICATION_REQUIRED — rule_runner_service (Stage
    10+) must refuse to execute any row that isn't VERIFIED."""

    __tablename__ = "tax_rules"
    # Lets rule_runner_service (Stage 10+) cheaply find "everything still
    # SOURCE_VERIFICATION_REQUIRED" without a full table scan.
    __table_args__ = (Index("ix_tax_rules_verification_status", "verification_status"),)

    rule_id: Mapped[str] = mapped_column(primary_key=True)  # e.g. "TAX-CASH-001"
    standard_id: Mapped[int | None] = mapped_column(ForeignKey("standards.standard_id"), default=None)
    topic: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    data_required: Mapped[str | None] = mapped_column(default=None)
    logic_summary: Mapped[str | None] = mapped_column(default=None)
    risk_level_default: Mapped[str] = mapped_column(default="MEDIUM")
    suggested_action: Mapped[str | None] = mapped_column(default=None)
    suggested_query_template: Mapped[str | None] = mapped_column(default=None)
    version: Mapped[str | None] = mapped_column(default=None)
    effective_date: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=False)
    legislative_act: Mapped[str | None] = mapped_column(default=None)  # IT_ACT_1961 / IT_ACT_2025
    provision_reference: Mapped[str | None] = mapped_column(default=None)  # e.g. "Section 40A(3)"
    applicable_from_ay: Mapped[str | None] = mapped_column(default=None)
    applicable_to_ay: Mapped[str | None] = mapped_column(default=None)  # nullable = still current
    verification_status: Mapped[str] = mapped_column(default="SOURCE_VERIFICATION_REQUIRED")
    verified_source: Mapped[str | None] = mapped_column(default=None)
    verified_on: Mapped[str | None] = mapped_column(default=None)
    verified_by: Mapped[str | None] = mapped_column(default=None)


class SebiRule(Base):
    """Blueprint Section 2.6 / Section 6. Same gating as TaxRule."""

    __tablename__ = "sebi_rules"
    __table_args__ = (Index("ix_sebi_rules_verification_status", "verification_status"),)

    rule_id: Mapped[str] = mapped_column(primary_key=True)  # e.g. "SEBI-FR-001"
    standard_id: Mapped[int | None] = mapped_column(ForeignKey("standards.standard_id"), default=None)
    topic: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    data_required: Mapped[str | None] = mapped_column(default=None)
    logic_summary: Mapped[str | None] = mapped_column(default=None)
    risk_level_default: Mapped[str] = mapped_column(default="MEDIUM")
    suggested_action: Mapped[str | None] = mapped_column(default=None)
    suggested_query_template: Mapped[str | None] = mapped_column(default=None)
    version: Mapped[str | None] = mapped_column(default=None)
    effective_date: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=False)
    lodr_regulation_ref: Mapped[str | None] = mapped_column(default=None)
    limitation: Mapped[str | None] = mapped_column(default=None)  # what this check does NOT cover (Correction #6)
    verification_status: Mapped[str] = mapped_column(default="SOURCE_VERIFICATION_REQUIRED")
    verified_source: Mapped[str | None] = mapped_column(default=None)
    verified_on: Mapped[str | None] = mapped_column(default=None)
    verified_by: Mapped[str | None] = mapped_column(default=None)


class AuditAssertion(Base):
    """Fixed audit-assertion vocabulary (Blueprint Section 2.2). Seeded
    once at install with the 9 approved values; not user-editable."""

    __tablename__ = "audit_assertions"

    assertion_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    label: Mapped[str] = mapped_column()

    rule_links: Mapped[list["AuditRuleAssertion"]] = relationship(
        back_populates="assertion", cascade="all, delete-orphan"
    )


class AuditRuleAssertion(Base):
    """Junction: one audit rule -> one or more assertions (Blueprint
    Section 2.3)."""

    __tablename__ = "audit_rule_assertions"

    rule_id: Mapped[str] = mapped_column(ForeignKey("audit_rules.rule_id"), primary_key=True)
    assertion_id: Mapped[int] = mapped_column(ForeignKey("audit_assertions.assertion_id"), primary_key=True)

    rule: Mapped["AuditRule"] = relationship(back_populates="assertion_links")
    assertion: Mapped["AuditAssertion"] = relationship(back_populates="rule_links")
