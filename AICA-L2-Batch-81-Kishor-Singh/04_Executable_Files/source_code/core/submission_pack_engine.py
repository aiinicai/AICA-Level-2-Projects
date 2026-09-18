"""Submission Pack Builder: assemble a client's documents into one indexed,
Bates-numbered PDF with a cover letter, table of contents, annexure labels,
and a SHA-256 manifest of every source file -- ready to submit as a GST/
Income-Tax notice reply, audit evidence pack, or client deliverable.

The combined PDF and its manifest are also packaged into a single ZIP so
the whole submission is one file to hand over or upload.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from core.page_selection import pages_to_ranges, resolve_pages
from core.pdf_engine import open_pdf
from core.watermark_engine import BatesNumberingOptions, add_bates_numbering
from utils.validation import ValidationError

_PAGE_WIDTH_PT, _PAGE_HEIGHT_PT = 595.0, 842.0  # A4
_MARGIN_PT = 56.0  # ~20mm
_LINE_HEIGHT_PT = 16.0
_FONT_SIZE = 11.0
_LINES_PER_PAGE = int((_PAGE_HEIGHT_PT - 2 * _MARGIN_PT) / _LINE_HEIGHT_PT)


@dataclass
class SubmissionPackItem:
    file_path: str
    category: str = ""  # e.g. "Invoice", "Bank Statement" -- matched against the checklist
    annexure_label: str = ""  # e.g. "Annexure A"; auto-assigned A, B, C... if left blank
    page_expression: str = "all"


@dataclass
class SubmissionPackConfig:
    client_name: str
    engagement: str  # e.g. "GST Notice Reply - DRC-01"
    financial_year: str = ""
    items: list[SubmissionPackItem] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)  # expected categories; flags any not covered by items
    cover_letter_text: str = ""
    bates_prefix: str = ""
    output_base_name: str = "Submission_Pack"


@dataclass
class ManifestEntry:
    source_file: str
    category: str
    annexure_label: str
    sha256: str
    page_count: int
    start_page_in_pack: int
    end_page_in_pack: int


@dataclass
class SubmissionPackResult:
    combined_pdf_path: str
    manifest_path: str
    zip_path: str
    manifest_entries: list[ManifestEntry]
    missing_from_checklist: list[str]
    total_pages: int


def _sha256_of_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _wrap_lines_to_pages(lines: list[str]) -> list[list[str]]:
    """Split a flat line list into page-sized chunks."""
    if not lines:
        return []
    pages = []
    for i in range(0, len(lines), _LINES_PER_PAGE):
        pages.append(lines[i : i + _LINES_PER_PAGE])
    return pages


def _wrap_paragraph(text: str, chars_per_line: int = 95) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > chars_per_line and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def _render_text_pages(doc: fitz.Document, page_chunks: list[list[str]], heading: str = "") -> None:
    for chunk in page_chunks:
        page = doc.new_page(width=_PAGE_WIDTH_PT, height=_PAGE_HEIGHT_PT)
        y = _MARGIN_PT
        if heading:
            page.insert_text(fitz.Point(_MARGIN_PT, y), heading, fontsize=14, fontname="helv", color=(0, 0, 0))
            y += _LINE_HEIGHT_PT * 1.5
        for line in chunk:
            page.insert_text(fitz.Point(_MARGIN_PT, y), line, fontsize=_FONT_SIZE, fontname="helv", color=(0, 0, 0))
            y += _LINE_HEIGHT_PT


def _annexure_label_for_index(index: int) -> str:
    """A, B, ..., Z, AA, AB, ... -- standard spreadsheet-column-style labelling."""
    label = ""
    n = index
    while True:
        n, remainder = divmod(n, 26)
        label = chr(65 + remainder) + label
        if n == 0:
            break
        n -= 1
    return label


def build_submission_pack(config: SubmissionPackConfig, output_dir: str | Path) -> SubmissionPackResult:
    if not config.items:
        raise ValidationError("Add at least one document to the submission pack.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Auto-assign annexure labels where not explicitly set.
    for i, item in enumerate(config.items):
        if not item.annexure_label:
            item.annexure_label = f"Annexure {_annexure_label_for_index(i)}"

    categories_present = {item.category for item in config.items if item.category}
    missing = [c for c in config.checklist if c not in categories_present]

    # ---- Pass 1: resolve each item's page count without rendering anything yet.
    item_page_counts: list[int] = []
    item_source_pages: list[list[int]] = []
    for item in config.items:
        with open_pdf(item.file_path) as doc:
            pages = resolve_pages(item.page_expression, doc.page_count)
        item_page_counts.append(len(pages))
        item_source_pages.append(pages)

    cover_lines = _wrap_paragraph(config.cover_letter_text) if config.cover_letter_text.strip() else []
    cover_page_chunks = _wrap_lines_to_pages(cover_lines)
    cover_page_count = len(cover_page_chunks)

    toc_lines = [
        f"{item.annexure_label}: {item.category or Path(item.file_path).name} "
        f"({Path(item.file_path).name}, {item_page_counts[i]} page(s))"
        for i, item in enumerate(config.items)
    ]
    toc_page_chunks_dry = _wrap_lines_to_pages(toc_lines)
    toc_page_count = max(1, len(toc_page_chunks_dry))

    # ---- Pass 2: compute each item's actual starting page in the final pack.
    cursor = cover_page_count + toc_page_count + 1
    starts: list[int] = []
    for count in item_page_counts:
        starts.append(cursor)
        cursor += count
    total_pages = cursor - 1

    toc_lines_final = [
        f"{item.annexure_label}: {item.category or Path(item.file_path).name} "
        f"({Path(item.file_path).name}, {item_page_counts[i]} page(s)) -- Page {starts[i]}"
        for i, item in enumerate(config.items)
    ]
    toc_page_chunks = _wrap_lines_to_pages(toc_lines_final)

    # ---- Render the combined document for real.
    out_doc = fitz.open()
    if cover_page_chunks:
        heading = f"{config.client_name} -- {config.engagement}"
        if config.financial_year:
            heading += f" ({config.financial_year})"
        _render_text_pages(out_doc, cover_page_chunks, heading=heading)

    _render_text_pages(out_doc, toc_page_chunks, heading="Table of Contents / Index")

    for item, pages in zip(config.items, item_source_pages):
        with open_pdf(item.file_path) as src:
            for start, end in pages_to_ranges(pages):
                out_doc.insert_pdf(src, from_page=start - 1, to_page=end - 1)

    combined_temp = output_dir / f"{config.output_base_name}_unnumbered.pdf"
    out_doc.save(str(combined_temp), garbage=3, deflate=True)
    out_doc.close()

    combined_path = output_dir / f"{config.output_base_name}.pdf"
    if config.bates_prefix:
        bates_result = add_bates_numbering(
            combined_temp, combined_path, BatesNumberingOptions(prefix=config.bates_prefix, digit_count=6, start_number=1)
        )
        assert bates_result.last_number == total_pages  # sanity check: numbering covers every page exactly once
        combined_temp.unlink(missing_ok=True)
    else:
        combined_temp.replace(combined_path)

    # ---- Manifest: hash the ORIGINAL source files (proof of what went in), not the combined pack.
    manifest_entries = [
        ManifestEntry(
            source_file=str(Path(item.file_path).name),
            category=item.category,
            annexure_label=item.annexure_label,
            sha256=_sha256_of_file(item.file_path),
            page_count=item_page_counts[i],
            start_page_in_pack=starts[i],
            end_page_in_pack=starts[i] + item_page_counts[i] - 1,
        )
        for i, item in enumerate(config.items)
    ]

    manifest_path = output_dir / f"{config.output_base_name}_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "client_name": config.client_name,
                "engagement": config.engagement,
                "financial_year": config.financial_year,
                "combined_pdf": combined_path.name,
                "combined_pdf_sha256": _sha256_of_file(combined_path),
                "total_pages": total_pages,
                "missing_from_checklist": missing,
                "documents": [
                    {
                        "annexure_label": e.annexure_label,
                        "category": e.category,
                        "source_file": e.source_file,
                        "sha256": e.sha256,
                        "page_count": e.page_count,
                        "start_page_in_pack": e.start_page_in_pack,
                        "end_page_in_pack": e.end_page_in_pack,
                    }
                    for e in manifest_entries
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Build the ZIP containing just the combined PDF + manifest (not the whole
    # output_dir, which may hold unrelated files from other runs).
    import zipfile

    zip_path = output_dir / f"{config.output_base_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(combined_path, arcname=combined_path.name)
        zf.write(manifest_path, arcname=manifest_path.name)

    return SubmissionPackResult(
        combined_pdf_path=str(combined_path),
        manifest_path=str(manifest_path),
        zip_path=str(zip_path),
        manifest_entries=manifest_entries,
        missing_from_checklist=missing,
        total_pages=total_pages,
    )
