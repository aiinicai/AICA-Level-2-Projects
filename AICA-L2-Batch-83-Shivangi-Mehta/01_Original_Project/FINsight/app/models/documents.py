"""
Document — Blueprint Section 2 (D.16), revised per Stage 3 review round 2.

Document is now the SOLE owner of the Document<->Exception/Query
relationship: related_exception_id and related_query_id are the only
links, both nullable (a document can be general engagement-level
evidence tied to neither), and — critically — many Document rows can
share the same related_exception_id, giving the intended one-exception-
to-many-documents workflow for free from a plain FK, with no join table
needed. See documentation/db_constraints.md for the full before/after.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_related_exception", "related_exception_id"),
        Index("ix_documents_related_query", "related_query_id"),
    )

    document_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    related_exception_id: Mapped[int | None] = mapped_column(ForeignKey("exceptions.exception_id"), default=None)
    related_query_id: Mapped[int | None] = mapped_column(ForeignKey("queries.query_id"), default=None)
    file_name: Mapped[str] = mapped_column()
    stored_path: Mapped[str] = mapped_column()
    uploaded_at: Mapped[str] = mapped_column()
