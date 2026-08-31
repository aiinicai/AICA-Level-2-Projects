"""Uploaded documents, rendered pages, raw extraction and AI verification results."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .core import now, uid


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    original_filename: Mapped[str] = mapped_column(String(300))
    stored_filename: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64))
    fiscal_year_label: Mapped[str] = mapped_column(String(20), default="")  # e.g. FY2024-25
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    has_native_text: Mapped[int] = mapped_column(Integer, default=1)

    # uploaded | reading | extracting | rendering | ai_verifying | reconciling
    # | awaiting_review | verified | locked | failed
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    error: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    pages: Mapped[list["DocumentPage"]] = relationship(back_populates="document")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    page_number: Mapped[int] = mapped_column(Integer)  # 1-based
    statement_type: Mapped[str] = mapped_column(String(40), default="other")
    # balance_sheet | profit_and_loss | cash_flow | notes | other
    is_candidate: Mapped[int] = mapped_column(Integer, default=0)
    rendered_png: Mapped[str] = mapped_column(String(400), default="")
    dpi: Mapped[int] = mapped_column(Integer, default=0)
    text_chars: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped[Document] = relationship(back_populates="pages")


class ExtractionResult(Base):
    """Raw Python-extracted candidate line items before canonical mapping."""

    __tablename__ = "extraction_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    statement_type: Mapped[str] = mapped_column(String(40), default="other")
    label: Mapped[str] = mapped_column(String(300))
    period_label: Mapped[str] = mapped_column(String(20), default="")
    raw_value: Mapped[str] = mapped_column(String(80), default="")
    normalised_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="INR")
    canonical_metric: Mapped[str] = mapped_column(String(60), default="")
    extraction_method: Mapped[str] = mapped_column(String(40), default="pymupdf")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class VerificationResult(Base):
    """Gemini visual verification output for a page/metric pair."""

    __tablename__ = "verification_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    metric: Mapped[str] = mapped_column(String(60))
    period_label: Mapped[str] = mapped_column(String(20), default="")
    label_seen: Mapped[str] = mapped_column(String(300), default="")
    python_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    visual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="not_visible")
    # verified | difference | not_visible | ambiguous
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    raw_response: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
