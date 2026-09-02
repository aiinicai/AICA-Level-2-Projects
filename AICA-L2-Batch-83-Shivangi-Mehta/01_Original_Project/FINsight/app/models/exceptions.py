"""
ExceptionRecord — Blueprint Section 2.12 (Corrections #10 and #11),
revised per the Stage 3 review round 2 (Document relationship fix,
constraints pass).

Naming note (flagged, not a schema change): the table is `exceptions`,
exactly as approved. The Python class is named `ExceptionRecord`, NOT
`Exception`, because shadowing Python's builtin Exception class with an
ORM model is a real footgun (bare `except Exception:` clauses elsewhere
in the codebase would become ambiguous/confusing if this name leaked
into that namespace). Table name and all approved fields are unchanged.

REMOVED in this revision: `supporting_file_id` (a FK to documents).
See documentation/db_constraints.md, "Document <-> Exception/Query
relationship", for the full rationale — in short, it was circular with
documents.related_exception_id and could only ever point at ONE
document, contradicting the intended one-exception-to-many-documents
workflow. documents.related_exception_id is now the sole, one-to-many
relationship.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Status enum (service-layer enforced, Blueprint Section 7):
#   OPEN -> UNDER_REVIEW -> QUERY_RAISED -> RESPONSE_RECEIVED -> RESOLVED
#                        \-> REVIEWED_NO_ISSUE  \-> NOT_APPLICABLE -> CLOSED
# status_reason is REQUIRED (service layer) when status is
# REVIEWED_NO_ISSUE or NOT_APPLICABLE.


class ExceptionRecord(Base):
    __tablename__ = "exceptions"
    __table_args__ = (
        Index("ix_exceptions_engagement_status", "engagement_id", "status"),
        Index("ix_exceptions_engagement_module", "engagement_id", "module"),
    )

    exception_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    module: Mapped[str] = mapped_column()  # ACCOUNTING / AUDIT / TAX / SEBI
    area: Mapped[str | None] = mapped_column(default=None)
    # References accounting_rules/audit_rules/tax_rules/sebi_rules.rule_id
    # depending on `module` — deliberately not a single hard FK, since it
    # spans four different tables (documented ambiguity from Blueprint
    # Section 2, D.12, carried forward as-is, not a new decision).
    # Kept NULLABLE (not tightened to NOT NULL): making every exception
    # mandatorily rule-traceable would forever rule out a possible future
    # "manually flagged by reviewer, no automated rule" exception path,
    # which nothing in the approved blueprint explicitly rules in or out.
    # That's a product-behavior decision, not a structural-integrity one
    # — flagged in documentation/db_constraints.md and the Stage 3
    # response for your call, not decided here.
    rule_id: Mapped[str | None] = mapped_column(default=None)
    standard_reference: Mapped[str | None] = mapped_column(default=None)  # denormalized for report convenience
    description: Mapped[str | None] = mapped_column(default=None)
    related_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.transaction_id"), default=None
    )
    amount: Mapped[int | None] = mapped_column(default=None)  # paise
    risk_score: Mapped[int | None] = mapped_column(default=None)  # denormalized total_score, 0-100
    risk_level: Mapped[str | None] = mapped_column(default=None)  # LOW / MEDIUM / HIGH / CRITICAL
    status: Mapped[str] = mapped_column(default="OPEN")
    assigned_to: Mapped[str | None] = mapped_column(default=None)
    reviewer_notes: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str] = mapped_column()
    resolved_at: Mapped[str | None] = mapped_column(default=None)
    # --- Correction #10: transparent "why flagged" without AI ---
    trigger_condition: Mapped[str | None] = mapped_column(default=None)
    threshold_used_json: Mapped[str | None] = mapped_column(default=None)
    data_sources_json: Mapped[str | None] = mapped_column(default=None)
    assertions_snapshot: Mapped[str | None] = mapped_column(default=None)  # audit-module exceptions only
    # --- Correction #11 ---
    status_reason: Mapped[str | None] = mapped_column(default=None)
