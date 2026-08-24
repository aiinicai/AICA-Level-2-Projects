"""Tests for DocumentType support across core/models.py, source_tracker.py,
and extractor.py - the document intelligence layer's support for
multiple document types (annual reports, investor presentations,
earnings-call transcripts, corporate announcements), not just annual
reports."""

from __future__ import annotations

from pathlib import Path

from app.core.enums import DocumentSectionType, DocumentType
from app.core.models import DocumentEvidence
from app.documents.extractor import extract_document, filter_by_document_type, filter_by_section
from app.documents.pdf_parser import RawPage
from app.documents.source_tracker import build_evidence, build_evidence_batch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_PDF = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_AR_FY_25-26.pdf"


class TestDocumentTypeDefault:
    def test_document_evidence_defaults_to_other(self):
        ev = DocumentEvidence(source_document="test.pdf", page_number=1, raw_text="text")
        assert ev.document_type == DocumentType.OTHER

    def test_document_evidence_accepts_explicit_type(self):
        ev = DocumentEvidence(
            source_document="test.pdf", page_number=1, raw_text="text",
            document_type=DocumentType.EARNINGS_CALL_TRANSCRIPT,
        )
        assert ev.document_type == DocumentType.EARNINGS_CALL_TRANSCRIPT

    def test_all_four_named_types_plus_other_available(self):
        assert DocumentType.ANNUAL_REPORT.value == "annual_report"
        assert DocumentType.INVESTOR_PRESENTATION.value == "investor_presentation"
        assert DocumentType.EARNINGS_CALL_TRANSCRIPT.value == "earnings_call_transcript"
        assert DocumentType.CORPORATE_ANNOUNCEMENT.value == "corporate_announcement"
        assert DocumentType.OTHER.value == "other"

    def test_quarterly_document_types_available_and_distinct_from_annual(self):
        assert DocumentType.QUARTERLY_RESULTS.value == "quarterly_results"
        assert DocumentType.QUARTERLY_INVESTOR_PRESENTATION.value == "quarterly_investor_presentation"
        assert DocumentType.QUARTERLY_MEET_TRANSCRIPT.value == "quarterly_meet_transcript"
        # Quarterly variants are genuinely distinct enum members from their
        # annual-cadence counterparts, not aliases — a report/audit trail
        # must be able to tell them apart.
        assert DocumentType.QUARTERLY_INVESTOR_PRESENTATION != DocumentType.INVESTOR_PRESENTATION
        assert DocumentType.QUARTERLY_MEET_TRANSCRIPT != DocumentType.EARNINGS_CALL_TRANSCRIPT


class TestSourceTrackerDocumentType:
    def test_build_evidence_stamps_document_type(self):
        page = RawPage(page_number=1, text="Some content.", char_count=13)
        ev = build_evidence(page, source_document="test.pdf", document_type=DocumentType.INVESTOR_PRESENTATION)
        assert ev.document_type == DocumentType.INVESTOR_PRESENTATION

    def test_build_evidence_defaults_to_other(self):
        page = RawPage(page_number=1, text="Some content.", char_count=13)
        ev = build_evidence(page, source_document="test.pdf")
        assert ev.document_type == DocumentType.OTHER

    def test_build_evidence_batch_stamps_all_pages_with_same_type(self):
        pages = [RawPage(page_number=i, text=f"text {i}", char_count=6) for i in range(1, 4)]
        evidence = build_evidence_batch(
            pages, source_document="test.pdf", document_type=DocumentType.CORPORATE_ANNOUNCEMENT,
        )
        assert all(e.document_type == DocumentType.CORPORATE_ANNOUNCEMENT for e in evidence)


class TestExtractDocumentWithType:
    def test_default_document_type_is_other(self):
        evidence = extract_document(SAMPLE_PDF)
        assert all(e.document_type == DocumentType.OTHER for e in evidence)

    def test_explicit_document_type_stamped_on_every_page(self):
        evidence = extract_document(
            SAMPLE_PDF, source_document="Sona BLW Annual Report",
            document_type=DocumentType.ANNUAL_REPORT,
        )
        assert len(evidence) == 194
        assert all(e.document_type == DocumentType.ANNUAL_REPORT for e in evidence)

    def test_different_document_type_produces_different_stamp(self):
        evidence = extract_document(
            SAMPLE_PDF, source_document="Some Transcript", document_type=DocumentType.EARNINGS_CALL_TRANSCRIPT,
        )
        assert all(e.document_type == DocumentType.EARNINGS_CALL_TRANSCRIPT for e in evidence)

    def test_quarterly_document_type_stamped_correctly_on_real_pdf(self):
        evidence = extract_document(
            SAMPLE_PDF, source_document="Sona BLW Quarterly Results",
            document_type=DocumentType.QUARTERLY_RESULTS,
        )
        assert len(evidence) == 194
        assert all(e.document_type == DocumentType.QUARTERLY_RESULTS for e in evidence)

    def test_section_classification_still_works_regardless_of_document_type(self):
        evidence = extract_document(
            SAMPLE_PDF, source_document="Sona BLW Annual Report", document_type=DocumentType.ANNUAL_REPORT,
        )
        governance_pages = filter_by_section(evidence, DocumentSectionType.GOVERNANCE)
        assert len(governance_pages) > 0


class TestFilterByDocumentType:
    def test_filters_correctly_with_mixed_types(self):
        evidence = [
            DocumentEvidence(source_document="a.pdf", page_number=1, raw_text="x", document_type=DocumentType.ANNUAL_REPORT),
            DocumentEvidence(source_document="b.pdf", page_number=1, raw_text="y", document_type=DocumentType.EARNINGS_CALL_TRANSCRIPT),
            DocumentEvidence(source_document="a.pdf", page_number=2, raw_text="z", document_type=DocumentType.ANNUAL_REPORT),
        ]
        annual_only = filter_by_document_type(evidence, DocumentType.ANNUAL_REPORT)
        assert len(annual_only) == 2
        transcript_only = filter_by_document_type(evidence, DocumentType.EARNINGS_CALL_TRANSCRIPT)
        assert len(transcript_only) == 1

    def test_no_matches_returns_empty_list(self):
        evidence = [
            DocumentEvidence(source_document="a.pdf", page_number=1, raw_text="x", document_type=DocumentType.ANNUAL_REPORT),
        ]
        result = filter_by_document_type(evidence, DocumentType.CORPORATE_ANNOUNCEMENT)
        assert result == []

    def test_empty_evidence_list_returns_empty(self):
        assert filter_by_document_type([], DocumentType.ANNUAL_REPORT) == []
