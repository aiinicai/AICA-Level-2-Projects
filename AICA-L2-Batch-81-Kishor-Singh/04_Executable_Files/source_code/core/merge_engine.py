"""PDF merge engine: combine multiple PDFs (optionally with per-file page ranges)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from core.page_selection import pages_to_ranges, resolve_pages
from core.pdf_engine import get_page_count, open_pdf
from utils.validation import ValidationError, validate_pdf_path


@dataclass
class MergeItem:
    """One input file plus which of its pages to include, in merge order."""

    file_path: str
    page_expression: str = "all"  # e.g. "all", "1-5", "2,4,6-8"
    password: str | None = None


@dataclass
class MergeResult:
    output_path: str
    total_pages: int
    source_count: int


def merge_pdfs(items: list[MergeItem], output_path: str | Path) -> MergeResult:
    """Merge PDFs in the given order, each contributing its resolved pages.

    Bookmarks/outlines from source files are intentionally not carried over
    (avoids duplicate/ambiguous outline trees); page content, including
    forms and annotations, is preserved via PyMuPDF's ``insert_pdf``.
    """
    if not items:
        raise ValidationError("No files selected to merge.")

    output = fitz.open()
    total_pages = 0
    try:
        for item in items:
            validate_pdf_path(item.file_path)
            with open_pdf(item.file_path, item.password) as src:
                page_count = src.page_count
                expr = item.page_expression.strip() or "all"
                pages_1indexed = resolve_pages(expr, page_count)
                # insert_pdf takes 0-based, inclusive from_page/to_page and
                # can't take an arbitrary sparse page list in one call, so we
                # merge contiguous runs to minimise the number of calls
                # while still supporting "1,3,5-8" style selections exactly.
                for start, end in pages_to_ranges(pages_1indexed):
                    output.insert_pdf(src, from_page=start - 1, to_page=end - 1)
                total_pages += len(pages_1indexed)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output.save(str(output_path), garbage=3, deflate=True)
    finally:
        output.close()

    return MergeResult(output_path=str(output_path), total_pages=total_pages, source_count=len(items))


def quick_page_count(path: str | Path) -> int:
    return get_page_count(path)
