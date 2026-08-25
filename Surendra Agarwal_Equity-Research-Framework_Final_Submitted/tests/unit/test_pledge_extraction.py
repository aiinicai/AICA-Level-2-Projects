"""Tests for app/ai/pledge_extraction.py and app/ai/prompts.py's
pledge-disclosure prompt, against the real Sona BLW SEBI Regulation 31
pledge/encumbrance disclosure filing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.enums import DocumentType
from app.core.exceptions import LLMProviderError
from app.core.models import DocumentEvidence
from app.ai.llm_client import FakeLLMClient
from app.ai.pledge_extraction import (
    extract_pledge_disclosure_batch,
    extract_pledge_disclosure_from_evidence,
    summarize_pledge_status,
)
from app.ai.prompts import build_pledge_disclosure_prompt
from app.documents.extractor import extract_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_PLEDGE_PDF = PROJECT_ROOT / "data" / "sample" / "SONACOMS_pledge_disclosure_2021.pdf"


class TestPledgeDisclosurePrompt:
    def test_document_text_wrapped_as_data(self):
        ev = DocumentEvidence(source_document="test.pdf", page_number=1, raw_text="Pledge details here.")
        system, user = build_pledge_disclosure_prompt(ev)
        assert "<document_excerpt" in user
        assert "Pledge details here." in user

    def test_upstream_vs_target_distinction_present_in_system_prompt(self):
        ev = DocumentEvidence(source_document="test.pdf", page_number=1, raw_text="text")
        system, _ = build_pledge_disclosure_prompt(ev)
        assert "upstream" in system.lower()
        assert "target" in system.lower()

    def test_schema_includes_pledge_pct_field(self):
        ev = DocumentEvidence(source_document="test.pdf", page_number=1, raw_text="text")
        system, _ = build_pledge_disclosure_prompt(ev)
        assert "pledge_pct_of_target_company_shares" in system


class TestExtractPledgeDisclosureFromEvidence:
    def _evidence(self, text="Some pledge disclosure text.", page=1):
        return DocumentEvidence(
            source_document="test.pdf", page_number=page, raw_text=text,
            document_type=DocumentType.PLEDGE_DISCLOSURE,
        )

    def test_disclosure_found_produces_result(self):
        fake = FakeLLMClient(fixed_response=(
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 0, '
            '"status": "not_applicable", "as_of_date": "2021-06-24", '
            '"summary": "No target company shares pledged."}'
        ))
        result = extract_pledge_disclosure_from_evidence(self._evidence(), fake)
        assert result is not None
        assert result["pledge_pct"] == 0
        assert result["as_of_date"] == "2021-06-24"

    def test_no_disclosure_returns_none(self):
        fake = FakeLLMClient(fixed_response='{"disclosure_found": false}')
        result = extract_pledge_disclosure_from_evidence(self._evidence(), fake)
        assert result is None

    def test_evidence_id_and_page_number_recorded(self):
        ev = self._evidence(page=4)
        fake = FakeLLMClient(fixed_response=(
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 5.0, '
            '"status": "created", "as_of_date": "2023-01-01", "summary": "test"}'
        ))
        result = extract_pledge_disclosure_from_evidence(ev, fake)
        assert result["evidence_id"] == ev.evidence_id
        assert result["page_number"] == 4

    def test_nonzero_pledge_extracted_correctly(self):
        fake = FakeLLMClient(fixed_response=(
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 12.5, '
            '"status": "created", "as_of_date": "2024-03-15", "summary": "12.5% pledged"}'
        ))
        result = extract_pledge_disclosure_from_evidence(self._evidence(), fake)
        assert result["pledge_pct"] == 12.5

    def test_malformed_json_raises(self):
        fake = FakeLLMClient(fixed_response="not json")
        with pytest.raises(LLMProviderError):
            extract_pledge_disclosure_from_evidence(self._evidence(), fake)


class TestExtractPledgeDisclosureBatch:
    def _evidence(self, page):
        return DocumentEvidence(source_document="test.pdf", page_number=page, raw_text=f"text {page}")

    def test_batch_skips_pages_with_no_disclosure(self):
        pages = [self._evidence(1), self._evidence(2)]
        fake = FakeLLMClient(responses=[
            '{"disclosure_found": false}',
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 0, "status": "not_applicable", "as_of_date": "2021-06-24", "summary": "x"}',
        ])
        results = extract_pledge_disclosure_batch(pages, fake)
        assert len(results) == 1

    def test_batch_skips_failed_pages(self):
        pages = [self._evidence(1), self._evidence(2)]
        fake = FakeLLMClient(responses=[
            "garbage",
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 0, "status": "not_applicable", "as_of_date": "2021-06-24", "summary": "x"}',
        ])
        results = extract_pledge_disclosure_batch(pages, fake)
        assert len(results) == 1


class TestSummarizePledgeStatus:
    def test_empty_list_returns_none_not_zero(self):
        summary = summarize_pledge_status([])
        assert summary["latest_pledge_pct"] is None
        assert summary["source_evidence_ids"] == []

    def test_picks_most_recent_dated_disclosure(self):
        disclosures = [
            {"pledge_pct": 10.0, "as_of_date": "2022-01-01", "summary": "old", "evidence_id": "a"},
            {"pledge_pct": 0.0, "as_of_date": "2024-06-01", "summary": "new", "evidence_id": "b"},
        ]
        summary = summarize_pledge_status(disclosures)
        assert summary["latest_pledge_pct"] == 0.0
        assert summary["as_of_date"] == "2024-06-01"

    def test_falls_back_to_last_when_no_dates(self):
        disclosures = [
            {"pledge_pct": 10.0, "as_of_date": None, "summary": "a", "evidence_id": "a"},
            {"pledge_pct": 5.0, "as_of_date": None, "summary": "b", "evidence_id": "b"},
        ]
        summary = summarize_pledge_status(disclosures)
        assert summary["latest_pledge_pct"] == 5.0

    def test_source_evidence_ids_include_all_disclosures(self):
        disclosures = [
            {"pledge_pct": 0.0, "as_of_date": "2021-01-01", "summary": "a", "evidence_id": "a"},
            {"pledge_pct": 0.0, "as_of_date": "2022-01-01", "summary": "b", "evidence_id": "b"},
        ]
        summary = summarize_pledge_status(disclosures)
        assert set(summary["source_evidence_ids"]) == {"a", "b"}


class TestRealSonaBLWPledgeDisclosure:
    def test_real_document_extracts_correctly(self):
        if not SAMPLE_PLEDGE_PDF.exists():
            pytest.skip("Sample pledge disclosure PDF not bundled in this checkout.")

        evidence = extract_document(
            SAMPLE_PLEDGE_PDF, source_document="Sona BLW Pledge Disclosure Jun 2021",
            document_type=DocumentType.PLEDGE_DISCLOSURE,
        )
        assert len(evidence) == 6

        responses = [
            '{"disclosure_found": false}',
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 0, "status": "not_applicable", "as_of_date": "2021-06-24", "summary": "Pledge is on upstream Singapore VII Topco shares, not target company shares."}',
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 0, "status": "not_applicable", "as_of_date": "2021-06-24", "summary": "Note confirms upstream entity encumbrance only."}',
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 0, "status": "not_applicable", "as_of_date": "2021-06-24", "summary": "Explicitly states promoter has not encumbered any shares in the Company."}',
            '{"disclosure_found": false}',
            '{"disclosure_found": false}',
        ]
        fake = FakeLLMClient(responses=responses)
        disclosures = extract_pledge_disclosure_batch(evidence, fake)
        assert len(disclosures) == 3

        summary = summarize_pledge_status(disclosures)
        assert summary["latest_pledge_pct"] == 0
