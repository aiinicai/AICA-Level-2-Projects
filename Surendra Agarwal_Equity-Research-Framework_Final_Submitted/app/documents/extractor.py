"""Document section classification and extraction pipeline — Module 4.

HONEST STATUS: classify_page() uses per-page keyword-frequency scoring,
not a table-of-contents-derived or layout-aware chapter boundary
detector. Verified against the real Sona BLW FY2025-26 annual report,
this correctly identifies the dominant section for clearly-worded pages
(e.g. a page headed "GOVERNANCE / BOARD OF DIRECTORS" scores as
GOVERNANCE), but Indian annual reports commonly interleave statutory
sections (Board's Report, MD&A, Corporate Governance Report, BRSR often
share overlapping pages/cross-references), so section boundaries here
are a best-effort signal for filtering/triage, not a precise chapter
index. Treat `section` on any DocumentEvidence as informative, not
authoritative — an analyst should still check the page directly for
anything that matters.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.enums import DocumentSectionType, DocumentType
from app.core.models import DocumentEvidence
from app.documents.pdf_parser import extract_pages
from app.documents.source_tracker import build_evidence_batch

logger = logging.getLogger(__name__)

# Keyword lists per section, weighted by specificity (a highly specific
# phrase like "cash conversion cycle" counts for more than a generic
# word like "risk" that could appear anywhere). Built from and checked
# against the real Sona BLW annual report's actual page content, not
# guessed from scratch — see module docstring.
_SECTION_KEYWORDS: dict[DocumentSectionType, list[tuple[str, int]]] = {
    DocumentSectionType.BUSINESS: [
        ("our business", 3), ("business model", 3), ("revenue mix", 3),
        ("product portfolio", 3), ("geographic", 2), ("competitive position", 3),
        ("industry overview", 3), ("market share", 2),
    ],
    DocumentSectionType.MANAGEMENT_DISCUSSION: [
        ("management discussion and analysis", 5), ("md&a", 4), ("outlook", 2),
        ("capex plan", 3), ("guidance", 2), ("growth expectation", 3),
        ("expansion plan", 3),
    ],
    DocumentSectionType.RISK: [
        ("risk management", 4), ("risk factor", 4), ("regulatory risk", 3),
        ("competitive risk", 3), ("commodity risk", 3), ("foreign exchange risk", 3),
        ("fx risk", 3), ("mitigation", 2), ("risk register", 3), ("enterprise risk", 3),
    ],
    DocumentSectionType.GOVERNANCE: [
        ("corporate governance report", 5), ("board of directors", 3),
        ("independent director", 3), ("audit committee", 3), ("nomination and remuneration committee", 4),
        ("related party transaction", 3), ("shareholding pattern", 2),
        ("board's report", 4), ("prevention of sexual harassment", 3),
    ],
    DocumentSectionType.AUDITOR_REPORT: [
        ("independent auditor", 5), ("auditor's report", 5),
        ("basis for opinion", 3), ("key audit matters", 4), ("emphasis of matter", 3),
    ],
    DocumentSectionType.FINANCIAL_STATEMENTS: [
        ("balance sheet", 3), ("statement of profit and loss", 4), ("cash flow statement", 3),
        ("notes to the", 2), ("material accounting polic", 4), ("contingent liabilit", 3),
        ("statement of changes in equity", 4),
    ],
}

_MIN_SCORE_TO_CLASSIFY = 3


def classify_page_text(text: str) -> DocumentSectionType:
    """Score a single page's text against every section's keyword list
    and return the highest-scoring section, or UNKNOWN if no section
    clears the minimum score threshold."""
    if not text:
        return DocumentSectionType.UNKNOWN

    lowered = text.lower()
    scores: dict[DocumentSectionType, int] = {}
    for section, keywords in _SECTION_KEYWORDS.items():
        score = sum(weight for phrase, weight in keywords if phrase in lowered)
        if score > 0:
            scores[section] = score

    if not scores:
        return DocumentSectionType.UNKNOWN

    best_section, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score < _MIN_SCORE_TO_CLASSIFY:
        return DocumentSectionType.UNKNOWN
    return best_section


def classify_pages(pages) -> dict[int, DocumentSectionType]:
    """Classify a list of RawPage -> {page_number: DocumentSectionType}."""
    return {page.page_number: classify_page_text(page.text) for page in pages}


def extract_document(
    pdf_path: Path, *, source_document: str | None = None,
    document_type: DocumentType = DocumentType.OTHER,
) -> list[DocumentEvidence]:
    """Full Module 4 pipeline: extract -> classify -> quarantine ->
    DocumentEvidence, for one PDF.

    This is the single entry point Milestone 5's callers (and, later,
    Layer 5's document_analysis.py) should use rather than calling
    pdf_parser/extractor/source_tracker individually.

    Args:
        document_type: what kind of document this is (annual report,
            investor presentation, earnings-call transcript, corporate
            announcement, or other). Stamped on every resulting
            DocumentEvidence. The page-level section classifier
            (classify_page_text) is content-based and applies the same
            regardless of document type; it was tuned against a real
            annual report and may be less informative (more UNKNOWN
            results) on other document types with different structure,
            e.g. a slide-deck investor presentation or a transcript -
            that's an honest limitation, not a bug, since those
            documents genuinely don't contain "Corporate Governance
            Report" style section headers.
    """
    name = source_document or pdf_path.name
    pages = extract_pages(pdf_path)
    sections = classify_pages(pages)
    evidence = build_evidence_batch(
        pages, source_document=name, sections=sections, document_type=document_type,
    )

    flagged_count = sum(1 for e in evidence if e.quarantine_flagged)
    if flagged_count:
        logger.warning(
            "%d of %d pages in %s had instruction-like content quarantined.",
            flagged_count, len(evidence), name,
        )

    section_counts: dict[str, int] = {}
    for e in evidence:
        section_counts[e.section.value] = section_counts.get(e.section.value, 0) + 1
    logger.info(
        "Section classification summary for %s (%s): %s",
        name, document_type.value, section_counts,
    )

    return evidence


def filter_by_section(
    evidence: list[DocumentEvidence], section: DocumentSectionType
) -> list[DocumentEvidence]:
    """Convenience: pull out only the evidence classified under one section."""
    return [e for e in evidence if e.section == section]


def filter_by_document_type(
    evidence: list[DocumentEvidence], document_type: DocumentType
) -> list[DocumentEvidence]:
    """Convenience: pull out only the evidence from one document type
    (e.g. only earnings-call transcript pages, ignoring the annual report)."""
    return [e for e in evidence if e.document_type == document_type]
