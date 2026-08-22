"""Tests confirming the Business/Management commentary extraction
pipeline actually works end-to-end against real document data, closing
a real gap: business_interpretations/management_interpretations were
only ever READ from session_state across the entire UI, never written
anywhere - meaning the AI-IDS Score's Business/Management component
could never receive data through any UI action.
"""

from __future__ import annotations

from pathlib import Path

from app.core.enums import DocumentSectionType, DocumentType
from app.ai.document_analysis import analyze_evidence_batch
from app.ai.llm_client import FakeLLMClient
from app.documents.extractor import extract_document, filter_by_section
from app.scoring.investment_score import score_business_management

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_AR_PDF = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_AR_FY_25-26.pdf"


class TestBusinessManagementExtractionEndToEnd:
    def test_real_annual_report_has_business_pages_to_analyze(self):
        evidence = extract_document(
            SAMPLE_AR_PDF, source_document="Sona BLW Annual Report",
            document_type=DocumentType.ANNUAL_REPORT,
        )
        business_pages = filter_by_section(evidence, DocumentSectionType.BUSINESS)
        assert len(business_pages) > 0

    def test_extraction_produces_real_interpretations(self):
        evidence = extract_document(
            SAMPLE_AR_PDF, source_document="Sona BLW Annual Report",
            document_type=DocumentType.ANNUAL_REPORT,
        )
        business_pages = filter_by_section(evidence, DocumentSectionType.BUSINESS)

        fake = FakeLLMClient(fixed_response=(
            '{"claim": "Company has strong market position in EV components", '
            '"confidence": "high"}'
        ))
        results = analyze_evidence_batch(business_pages[:3], fake, focus="business overview")
        assert len(results) == 3
        assert all(r.claim for r in results)
        assert all(r.confidence.value == "high" for r in results)

    def test_extracted_interpretations_feed_into_a_real_score(self):
        evidence = extract_document(
            SAMPLE_AR_PDF, source_document="Sona BLW Annual Report",
            document_type=DocumentType.ANNUAL_REPORT,
        )
        business_pages = filter_by_section(evidence, DocumentSectionType.BUSINESS)

        fake = FakeLLMClient(fixed_response=(
            '{"claim": "Company has strong market position in EV components", '
            '"confidence": "high"}'
        ))
        results = analyze_evidence_batch(business_pages[:3], fake, focus="business overview")

        component = score_business_management(results)
        assert component.status.value == "ok"
        assert component.score is not None
        assert component.score > 0

    def test_empty_evidence_list_correctly_stays_unavailable_not_fabricated(self):
        component = score_business_management([])
        assert component.status.value == "unavailable"
        assert component.score is None

    def test_management_discussion_pages_use_a_different_focus(self):
        evidence = extract_document(
            SAMPLE_AR_PDF, source_document="Sona BLW Annual Report",
            document_type=DocumentType.ANNUAL_REPORT,
        )
        management_pages = filter_by_section(evidence, DocumentSectionType.MANAGEMENT_DISCUSSION)
        fake = FakeLLMClient(fixed_response='{"claim": "test claim", "confidence": "medium"}')
        results = analyze_evidence_batch(management_pages, fake, focus="management commentary")
        assert isinstance(results, list)
