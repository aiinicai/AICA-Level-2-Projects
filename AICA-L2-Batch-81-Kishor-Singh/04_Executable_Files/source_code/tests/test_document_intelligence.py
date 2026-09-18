"""Tests for core.document_intelligence, using a stub AIProvider (no network calls)."""
from __future__ import annotations

import json

from core.ai_provider import AIProviderKind, AIResponse
from core.document_intelligence import (
    Citation,
    DocumentCategory,
    DocumentChunk,
    ask_document,
    classify_document,
    retrieve_relevant_chunks,
    summarize_document,
)


class StubProvider:
    """A minimal stand-in for AIProvider that returns a pre-programmed JSON response."""

    def __init__(self, response_dict: dict):
        self.response_dict = response_dict
        self.last_request = None

    def complete(self, request):
        self.last_request = request
        return AIResponse(text=json.dumps(self.response_dict), provider=AIProviderKind.ANTHROPIC, model="stub-model")


def test_classify_document_parses_category_and_confidence():
    stub = StubProvider({"category": "Invoice", "confidence": 92, "rationale": "Contains GSTIN and line items"})
    result = classify_document("Invoice text with GSTIN 29ABCDE1234F1Z5", stub)
    assert result.category == DocumentCategory.INVOICE
    assert result.confidence == 92


def test_classify_document_falls_back_to_other_for_unknown_category():
    stub = StubProvider({"category": "Something Weird", "confidence": 10, "rationale": "unsure"})
    result = classify_document("mystery text", stub)
    assert result.category == DocumentCategory.OTHER


def test_classify_document_tolerates_markdown_fenced_json():
    class FencedStub:
        def complete(self, request):
            return AIResponse(
                text='```json\n{"category": "Bank Statement", "confidence": 80, "rationale": "has transactions"}\n```',
                provider=AIProviderKind.ANTHROPIC,
                model="stub",
            )

    result = classify_document("some bank text", FencedStub())
    assert result.category == DocumentCategory.BANK_STATEMENT


def test_summarize_document_extracts_all_fields():
    stub = StubProvider(
        {
            "summary_text": "A GST demand notice.",
            "parties": ["ABC & Co", "GST Department"],
            "key_dates": ["2026-01-15"],
            "amounts": ["Rs. 50000"],
            "issues": ["Mismatch in ITC claimed"],
            "missing_information": ["Supporting invoices"],
            "proposed_next_actions": ["File a reply with evidence"],
            "possible_deadline": "2026-02-01",
        }
    )
    result = summarize_document("notice text", stub)
    assert result.summary_text == "A GST demand notice."
    assert "ABC & Co" in result.parties
    assert result.possible_deadline == "2026-02-01"


def test_summarize_document_never_invents_a_deadline_when_none_stated():
    stub = StubProvider(
        {
            "summary_text": "A routine confirmation letter.",
            "parties": [],
            "key_dates": [],
            "amounts": [],
            "issues": [],
            "missing_information": [],
            "proposed_next_actions": [],
            "possible_deadline": "",
        }
    )
    result = summarize_document("confirmation text", stub)
    assert result.possible_deadline == ""


def test_retrieve_relevant_chunks_ranks_by_keyword_overlap():
    chunks = [
        DocumentChunk("A.pdf", 1, "This page talks about apples and oranges."),
        DocumentChunk("A.pdf", 2, "This page is entirely about GST notice section 74 demand."),
        DocumentChunk("B.pdf", 1, "Unrelated content about weather."),
    ]
    relevant = retrieve_relevant_chunks("What does the GST notice say about the demand?", chunks, top_k=2)
    assert relevant[0].document_name == "A.pdf"
    assert relevant[0].page_number == 2


def test_ask_document_returns_citations_matching_source_numbers():
    chunks = [DocumentChunk("Notice.pdf", 3, "The demand amount is Rs. 50,000 under section 74.")]
    stub = StubProvider(
        {
            "answer": "The demand amount is Rs. 50,000.",
            "is_uncertain": False,
            "citations": [{"source_number": 1, "excerpt": "demand amount is Rs. 50,000"}],
        }
    )
    result = ask_document("What is the demand amount?", chunks, stub)
    assert "50,000" in result.answer
    assert not result.is_uncertain
    assert len(result.citations) == 1
    assert result.citations[0].document_name == "Notice.pdf"
    assert result.citations[0].page_number == 3


def test_ask_document_with_no_chunks_is_uncertain():
    result = ask_document("Any question", [], StubProvider({}))
    assert result.is_uncertain
    assert "No documents" in result.answer


def test_ask_document_marks_uncertain_when_model_says_so():
    stub = StubProvider({"answer": "This is not covered in the provided sources.", "is_uncertain": True, "citations": []})
    chunks = [DocumentChunk("X.pdf", 1, "Unrelated content.")]
    result = ask_document("What is the capital of France?", chunks, stub)
    assert result.is_uncertain
