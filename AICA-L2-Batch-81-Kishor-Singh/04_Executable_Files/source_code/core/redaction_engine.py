"""Permanent redaction: finds sensitive values, removes them from the actual
content stream (not a black rectangle painted over live text).

Uses PyMuPDF's native redaction annotations (``add_redact_annot`` +
``apply_redactions``), which genuinely delete the underlying text/image
content within the marked area -- unlike a plain overlay, the redacted
value cannot be recovered by copy-pasting or text extraction afterwards.
This is verified automatically by :func:`verify_redaction`, which reopens
the saved output and confirms the target values are actually gone.

Detection is regex-based and always produces *candidates for human review*
-- nothing is redacted until :func:`apply_redactions` is called on an
explicitly confirmed candidate list. Patterns are intentionally broad
(especially the generic account-number heuristic) since a false positive
here only means "shown for review," while a false negative means a real
value leaks -- the safer direction to err in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from core.pdf_engine import open_pdf
from utils.validation import ValidationError


class RedactionPatternKind:
    PAN = "PAN (Income Tax)"
    AADHAAR_LIKE = "Aadhaar-like Number"
    GSTIN = "GSTIN"
    EMAIL = "Email Address"
    PHONE = "Phone Number (India)"
    BANK_ACCOUNT_LIKE = "Bank Account Number (heuristic)"


_PATTERNS: dict[str, re.Pattern] = {
    RedactionPatternKind.PAN: re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    RedactionPatternKind.GSTIN: re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}\b"),
    RedactionPatternKind.AADHAAR_LIKE: re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    RedactionPatternKind.EMAIL: re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    RedactionPatternKind.PHONE: re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b"),
    # Deliberately broad (9-18 digit run) -- a heuristic, off by default in the UI,
    # meant only to catch bank/loan account numbers that don't match a stricter pattern.
    RedactionPatternKind.BANK_ACCOUNT_LIKE: re.compile(r"\b\d{9,18}\b"),
}

DEFAULT_ENABLED_PATTERNS = [
    RedactionPatternKind.PAN,
    RedactionPatternKind.GSTIN,
    RedactionPatternKind.AADHAAR_LIKE,
    RedactionPatternKind.EMAIL,
    RedactionPatternKind.PHONE,
]


@dataclass
class RedactionCandidate:
    page_index: int  # 0-based
    matched_text: str
    pattern_name: str
    # All on-page occurrences of matched_text, filled in by locate_candidate_rects.
    # A value can legitimately appear more than once on a page (e.g. repeated in a
    # header and a signature block) -- every occurrence must be redacted, not just
    # the first, or the "removed" value remains trivially recoverable elsewhere on
    # the same page. Note this does NOT catch a value embedded as a *substring* of
    # a different, unapproved field -- e.g. an Indian GSTIN literally contains the
    # entity's PAN as characters 3-12 of its 15-character format, so redacting a
    # PAN candidate alone leaves it readable inside any un-redacted GSTIN nearby.
    rects: list[tuple[float, float, float, float]] = field(default_factory=list)
    approved: bool = False  # UI sets this after user review; apply_redactions only acts on approved ones


def find_redaction_candidates(source_path: str | Path, pattern_names: list[str] | None = None) -> list[RedactionCandidate]:
    """Scan every page's extractable text for sensitive-looking values.

    Only finds values in text that PyMuPDF can already extract -- run OCR
    first (see :mod:`core.ocr_engine`) if the document is a scan with no
    text layer, otherwise nothing will be found.
    """
    pattern_names = pattern_names or DEFAULT_ENABLED_PATTERNS
    candidates: list[RedactionCandidate] = []
    with open_pdf(source_path) as doc:
        for page_index in range(doc.page_count):
            text = doc[page_index].get_text()
            seen_on_page: set[str] = set()
            for name in pattern_names:
                pattern = _PATTERNS[name]
                for match in pattern.finditer(text):
                    value = match.group(0)
                    if value in seen_on_page:
                        continue
                    seen_on_page.add(value)
                    candidates.append(RedactionCandidate(page_index=page_index, matched_text=value, pattern_name=name))
    return candidates


def locate_candidate_rects(doc: fitz.Document, candidates: list[RedactionCandidate]) -> None:
    """Fill in each candidate's on-page rectangle(s) via text search, in place.

    Finds and stores *every* occurrence of the matched text on its page, not
    just the first -- see the note on :attr:`RedactionCandidate.rects`.
    """
    by_page: dict[int, list[RedactionCandidate]] = {}
    for c in candidates:
        by_page.setdefault(c.page_index, []).append(c)
    for page_index, page_candidates in by_page.items():
        page = doc[page_index]
        for c in page_candidates:
            hits = page.search_for(c.matched_text)
            c.rects = [(r.x0, r.y0, r.x1, r.y1) for r in hits]


def apply_redactions(source_path: str | Path, output_path: str | Path, candidates: list[RedactionCandidate]) -> int:
    """Permanently remove every *approved* candidate's content, saved as a new file.

    Returns the number of redaction boxes actually applied (a candidate with
    multiple on-page occurrences counts once per occurrence). Candidates
    without ``approved=True`` or with no located occurrences are skipped.
    """
    approved = [c for c in candidates if c.approved]
    if not approved:
        raise ValidationError("No redaction candidates were approved. Nothing was changed.")

    with open_pdf(source_path) as doc:
        if any(not c.rects for c in approved):
            locate_candidate_rects(doc, approved)

        applied = 0
        pages_touched: set[int] = set()
        for c in approved:
            if not c.rects:
                continue  # value moved/changed since detection; skip rather than guess
            page = doc[c.page_index]
            for rect in c.rects:
                page.add_redact_annot(fitz.Rect(*rect), fill=(0, 0, 0))
                applied += 1
            pages_touched.add(c.page_index)

        for page_index in pages_touched:
            # images=REMOVE strips any image overlapping the redaction box too,
            # not only text -- required for a scanned page's OCR text layer plus
            # its underlying picture to both be genuinely removed.
            doc[page_index].apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

        # Metadata can carry sensitive content (author, subject, custom fields) --
        # clear it as part of a redaction pass rather than leaving it behind.
        doc.set_metadata({})

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=4, deflate=True)

    return applied


def verify_redaction(output_path: str | Path, values_that_should_be_gone: list[str]) -> list[str]:
    """Reopen the redacted file and confirm none of the given values are still extractable.

    Returns the (hopefully empty) list of values that are still found --
    callers should treat any non-empty result as a failed redaction, not
    a warning to ignore.
    """
    still_present = []
    with open_pdf(output_path) as doc:
        full_text = "\n".join(doc[i].get_text() for i in range(doc.page_count))
    for value in values_that_should_be_gone:
        if value in full_text:
            still_present.append(value)
    return still_present
