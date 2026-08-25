"""Source tracking - Module 4/11.

Wraps a RawPage (pdf_parser.py) into a DocumentEvidence object, running
it through quarantine (quarantine.py) first. This is the boundary
between "raw extracted text" and "text that is safe to eventually pass
into an LLM prompt" - every DocumentEvidence produced here has already
been through the quarantine pass, and no other code path in this
codebase is permitted to construct DocumentEvidence directly from
un-quarantined text.
"""

from __future__ import annotations

from app.core.enums import DocumentSectionType, DocumentType
from app.core.models import DocumentEvidence
from app.documents.pdf_parser import RawPage
from app.documents.quarantine import scan_and_quarantine


def build_evidence(
    page: RawPage,
    *,
    source_document: str,
    section: DocumentSectionType = DocumentSectionType.UNKNOWN,
    document_type: DocumentType = DocumentType.OTHER,
) -> DocumentEvidence:
    """Build one DocumentEvidence from a single extracted page, quarantined."""
    result = scan_and_quarantine(page.text)
    return DocumentEvidence(
        source_document=source_document,
        document_type=document_type,
        page_number=page.page_number,
        section=section,
        raw_text=result.sanitized_text,
        quarantine_flagged=result.flagged,
    )


def build_evidence_batch(
    pages: list[RawPage],
    *,
    source_document: str,
    sections: dict[int, DocumentSectionType] | None = None,
    document_type: DocumentType = DocumentType.OTHER,
) -> list[DocumentEvidence]:
    """Build DocumentEvidence for a batch of pages.

    Args:
        pages: output of pdf_parser.extract_pages().
        source_document: filename/identifier stamped on every evidence record.
        sections: optional page_number -> DocumentSectionType mapping
            (typically produced by extractor.classify_pages()). Pages not
            present in this mapping default to UNKNOWN rather than a guess.
        document_type: what kind of document this batch came from (Module 4's
            named categories) - stamped on every resulting evidence record.
    """
    sections = sections or {}
    return [
        build_evidence(
            page, source_document=source_document,
            section=sections.get(page.page_number, DocumentSectionType.UNKNOWN),
            document_type=document_type,
        )
        for page in pages
    ]
