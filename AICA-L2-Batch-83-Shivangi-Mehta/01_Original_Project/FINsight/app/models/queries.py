"""
QueryRecord, QueryResponse — Blueprint Section 2 (D.14/D.15) / Section I.

Naming note (flagged, not a schema change): table is `queries`, exactly
as approved. Python class is `QueryRecord`, not `Query`, to avoid
shadowing/confusion with SQLAlchemy's own historical `Query` object
(session.query(...)) when both are in scope in the same module.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Status enum (Blueprint Section I, unchanged by v0.2): OPEN -> UNDER_REVIEW
# -> QUERY_SENT -> RESPONSE_RECEIVED -> RESOLVED -> CLOSED (or OPEN -> CLOSED
# directly if withdrawn). Linked to, but independent of, ExceptionRecord.status
# (Blueprint Section 7).


class QueryRecord(Base):
    __tablename__ = "queries"
    __table_args__ = (Index("ix_queries_engagement_status", "engagement_id", "status"),)

    query_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    exception_id: Mapped[int | None] = mapped_column(ForeignKey("exceptions.exception_id"), default=None)
    category: Mapped[str] = mapped_column()  # ACCOUNTING / AUDIT / TAX / SEBI
    area: Mapped[str | None] = mapped_column(default=None)
    observation: Mapped[str | None] = mapped_column(default=None)
    question_text: Mapped[str | None] = mapped_column(default=None)
    required_document: Mapped[str | None] = mapped_column(default=None)
    reference: Mapped[str | None] = mapped_column(default=None)
    risk_level: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="OPEN")
    # Rule-based vs AI-assisted distinction (Blueprint Section 20) — must
    # stay a real, queryable flag, not just a UI label.
    is_ai_drafted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column()
    # --- Stage 13 (approved schema addition) ---
    # The reviewer's edited version of `question_text`. NEVER a
    # replacement for it — `question_text` stays the original,
    # FinSight-generated wording, permanently recoverable, per the
    # Stage 13 traceability requirement. NULL means "not yet
    # reviewer-edited"; the UI falls back to displaying `question_text`
    # in that case. See app/services/query_service.py, which is the
    # only place this column is ever written.
    reviewer_query_text: Mapped[str | None] = mapped_column(default=None)


class QueryResponse(Base):
    __tablename__ = "query_responses"

    response_id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("queries.query_id"))
    management_response: Mapped[str | None] = mapped_column(default=None)
    reviewer_comments: Mapped[str | None] = mapped_column(default=None)
    resolution: Mapped[str | None] = mapped_column(default=None)
    responded_at: Mapped[str | None] = mapped_column(default=None)
    # --- Stage 13 (approved schema addition) ---
    # Evidence the reviewer recorded as actually received — distinct
    # from `reviewer_comments` (general commentary) and `resolution`
    # (the free-text outcome narrative). No document-management system:
    # `evidence_reference` is a plain local file name/path/reference
    # number the reviewer types in, never a managed upload.
    evidence_description: Mapped[str | None] = mapped_column(default=None)
    evidence_reference: Mapped[str | None] = mapped_column(default=None)
