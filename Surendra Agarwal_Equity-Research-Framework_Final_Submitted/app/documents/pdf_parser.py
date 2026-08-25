"""PDF text extraction — Module 4.

Extracts page-level text with page numbers preserved, which is the
foundation everything in source_tracker.py / extractor.py depends on
for citing "source_document, page N" against any claim later derived
from a document.

This module does NOT classify content, detect injection attempts, or
interpret anything — it only turns a PDF into (page_number, raw_text)
pairs. Everything else lives downstream, keeping this file trivially
testable and swappable (e.g. for a pdfplumber fallback) without
touching classification or quarantine logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import PDFParsingError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawPage:
    """One page's extracted text, before any classification or quarantine."""

    page_number: int  # 1-indexed, matching how a human would cite "page 42"
    text: str
    char_count: int


def extract_pages(pdf_path: Path) -> list[RawPage]:
    """Extract text from every page of a PDF, preserving page numbers.

    Raises:
        PDFParsingError: if the file doesn't exist, isn't a valid PDF,
            or is encrypted without a supplied password. A partial
            failure on an individual page does not abort the whole
            document — that page is returned with empty text and a
            logged warning, since a scanned/image-only page is a
            legitimate (if lower-value) outcome, not necessarily a bug.
    """
    if not pdf_path.exists():
        raise PDFParsingError(f"PDF not found: {pdf_path}")

    try:
        import pymupdf
    except ImportError as exc:
        raise PDFParsingError(
            "PyMuPDF (pymupdf) is not installed. Run: pip install pymupdf"
        ) from exc

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:
        raise PDFParsingError(f"Could not open {pdf_path.name}: {exc}") from exc

    if doc.is_encrypted:
        # Attempt an empty-password unlock (common for "restricted but not
        # password-protected" PDFs); if that fails, this is a hard stop —
        # guessing a password would be inappropriate.
        if not doc.authenticate(""):
            doc.close()
            raise PDFParsingError(
                f"{pdf_path.name} is encrypted and requires a password. "
                "Decrypt it first, or supply the password via a future "
                "extract_pages(password=...) parameter if this becomes common."
            )

    pages: list[RawPage] = []
    for i in range(doc.page_count):
        try:
            page = doc[i]
            text = page.get_text()
        except Exception as exc:
            logger.warning("Failed to extract text from page %d of %s: %s", i + 1, pdf_path.name, exc)
            text = ""
        pages.append(RawPage(page_number=i + 1, text=text, char_count=len(text)))

    doc.close()
    logger.info("Extracted %d pages from %s", len(pages), pdf_path.name)

    empty_pages = sum(1 for p in pages if p.char_count == 0)
    if empty_pages:
        logger.info(
            "%d of %d pages had no extractable text (likely scanned images) — "
            "OCR is not implemented; these pages will not contribute evidence.",
            empty_pages, len(pages),
        )

    return pages
