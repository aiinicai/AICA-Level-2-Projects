"""Tests for app/ai/document_analysis.py. No live LLM calls."""

from __future__ import annotations

import pytest

from app.core.enums import ConfidenceLevel, InsightLevel
from app.core.exceptions import LLMProviderError
from app.core.models import DocumentEvidence
from app.ai.document_analysis import (
    analyze_evidence,
    analyze_evidence_batch,
    compute_management_commentary_summary,
)
from app.ai.llm_client import FakeLLMClient


def _evidence(text="Some annual report text.", page=1):
    return DocumentEvidence(source_document="test.pdf", page_number=page, raw_text=text)


class TestAnalyzeEvidence:
    def test_valid_response_produces_ai_interpretation(self):
        fake = FakeLLMClient(fixed_response='{"claim": "Revenue grew due to new orders", "confidence": "high"}')
        result = analyze_evidence(_evidence(), fake)
        assert result is not None
        assert result.claim == "Revenue grew due to new orders"
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.level == InsightLevel.LEVEL_2_AI_INTERPRETATION

    def test_evidence_id_linked_correctly(self):
        ev = _evidence()
        fake = FakeLLMClient(fixed_response='{"claim": "test claim", "confidence": "medium"}')
        result = analyze_evidence(ev, fake)
        assert result.based_on_evidence_ids == [ev.evidence_id]

    def test_null_claim_returns_none_not_error(self):
        fake = FakeLLMClient(fixed_response='{"claim": null, "confidence": "low"}')
        result = analyze_evidence(_evidence(), fake, focus="dividend policy")
        assert result is None

    def test_malformed_json_raises_llm_provider_error(self):
        fake = FakeLLMClient(fixed_response="not valid json at all")
        with pytest.raises(LLMProviderError):
            analyze_evidence(_evidence(), fake)

    def test_json_wrapped_in_markdown_fence_still_parses(self):
        fake = FakeLLMClient(fixed_response='```json\n{"claim": "fenced claim", "confidence": "high"}\n```')
        result = analyze_evidence(_evidence(), fake)
        assert result.claim == "fenced claim"

    def test_unrecognized_confidence_defaults_to_low_not_crash(self):
        fake = FakeLLMClient(fixed_response='{"claim": "a claim", "confidence": "very-extremely-high"}')
        result = analyze_evidence(_evidence(), fake)
        assert result.confidence == ConfidenceLevel.LOW

    def test_model_name_recorded_from_response(self):
        fake = FakeLLMClient(fixed_response='{"claim": "x", "confidence": "high"}', model_name="test-model-v1")
        result = analyze_evidence(_evidence(), fake)
        assert result.model_name == "test-model-v1"


class TestAnalyzeEvidenceBatch:
    def test_batch_processes_all_evidence(self):
        pages = [_evidence(f"page {i} text", page=i) for i in range(1, 4)]
        fake = FakeLLMClient(fixed_response='{"claim": "consistent claim", "confidence": "medium"}')
        results = analyze_evidence_batch(pages, fake)
        assert len(results) == 3

    def test_batch_skips_failed_pages_without_crashing_whole_batch(self):
        pages = [_evidence("page 1"), _evidence("page 2"), _evidence("page 3")]
        fake = FakeLLMClient(responses=[
            "garbage not json",
            '{"claim": "valid claim 2", "confidence": "high"}',
            '{"claim": "valid claim 3", "confidence": "medium"}',
        ])
        results = analyze_evidence_batch(pages, fake)
        assert len(results) == 2

    def test_batch_skips_pages_with_no_relevant_claim(self):
        pages = [_evidence("page 1"), _evidence("page 2")]
        fake = FakeLLMClient(responses=[
            '{"claim": null, "confidence": "low"}',
            '{"claim": "found something", "confidence": "high"}',
        ])
        results = analyze_evidence_batch(pages, fake)
        assert len(results) == 1


class TestManagementCommentarySummary:
    def test_summary_counts_and_distributes_confidence(self):
        from app.core.models import AIInterpretation

        interps = [
            AIInterpretation(claim="a", confidence=ConfidenceLevel.HIGH, model_name="m", based_on_evidence_ids=["e1"]),
            AIInterpretation(claim="b", confidence=ConfidenceLevel.HIGH, model_name="m", based_on_evidence_ids=["e2"]),
            AIInterpretation(claim="c", confidence=ConfidenceLevel.LOW, model_name="m", based_on_evidence_ids=["e3"]),
        ]
        summary = compute_management_commentary_summary(interps)
        assert summary["total_claims_extracted"] == 3
        assert summary["confidence_distribution"]["high"] == 2
        assert summary["confidence_distribution"]["low"] == 1
        assert "not a numeric management-quality score" in summary["note"]

    def test_summary_handles_empty_list(self):
        summary = compute_management_commentary_summary([])
        assert summary["total_claims_extracted"] == 0
