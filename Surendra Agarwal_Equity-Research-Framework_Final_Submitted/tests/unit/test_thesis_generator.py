"""Tests for app/ai/thesis_generator.py. No live LLM calls."""

from __future__ import annotations

import json

import pytest

from app.core.enums import Recommendation
from app.core.exceptions import LLMProviderError
from app.ai.llm_client import FakeLLMClient
from app.ai.thesis_generator import (
    BANNED_PHRASES,
    generate_investment_thesis,
    lint_text,
    sanitize_text,
)


def _valid_response(**overrides) -> str:
    data = {
        "recommendation": "hold",
        "core_thesis": "The company shows solid revenue growth with moderate valuation risk.",
        "counterarguments": ["Valuation is elevated versus historical average"],
        "catalysts": ["New product launch expected next quarter"],
        "invalidation_triggers": [
            {"condition": "Revenue growth below 8% for 2 consecutive years",
             "threshold_basis": "explicit_assumption", "metric_reference": "Revenue CAGR"},
            {"condition": "Debt/Equity above 1.0", "threshold_basis": "industry_context",
             "metric_reference": "Debt/Equity"},
        ],
        "data_limitations": ["Peer set multiples not independently audited"],
    }
    data.update(overrides)
    return json.dumps(data)


class TestLintText:
    def test_detects_banned_phrase(self):
        assert "guaranteed return" in lint_text("This offers a guaranteed return to investors.")

    def test_case_insensitive_detection(self):
        assert "guaranteed return" in lint_text("GUARANTEED RETURN for everyone!")

    def test_clean_text_returns_empty_list(self):
        assert lint_text("Revenue grew 15% with stable margins and moderate leverage.") == []

    def test_multiple_banned_phrases_all_detected(self):
        hits = lint_text("This is a risk-free, guaranteed profit, sure shot investment.")
        assert "risk-free" in hits
        assert "guaranteed profit" in hits
        assert "sure shot" in hits


class TestSanitizeText:
    def test_banned_phrase_replaced_with_marker(self):
        sanitized, modified = sanitize_text("This is a guaranteed return opportunity.")
        assert modified is True
        assert "guaranteed return" not in sanitized.lower()
        assert "LANGUAGE ADJUSTED" in sanitized

    def test_clean_text_unmodified(self):
        original = "Revenue grew 15% year over year."
        sanitized, modified = sanitize_text(original)
        assert modified is False
        assert sanitized == original

    def test_all_occurrences_replaced_not_just_first(self):
        text = "guaranteed return today, guaranteed return tomorrow"
        sanitized, modified = sanitize_text(text)
        assert modified is True
        assert "guaranteed return" not in sanitized.lower()
        assert sanitized.count("LANGUAGE ADJUSTED") == 2


class TestGenerateInvestmentThesis:
    def test_valid_response_produces_thesis(self):
        fake = FakeLLMClient(fixed_response=_valid_response())
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[],
            interpretation_claims=[("id1", "claim text")], llm_client=fake,
        )
        assert thesis.recommendation == Recommendation.HOLD
        assert len(thesis.invalidation_triggers) == 2
        assert thesis.requires_human_review is True

    def test_banned_phrase_in_core_thesis_gets_neutralized(self):
        bad = _valid_response(core_thesis="This stock is a guaranteed return opportunity with certain multibagger potential.")
        fake = FakeLLMClient(fixed_response=bad)
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
        )
        assert "guaranteed return" not in thesis.core_thesis.lower()
        assert "certain multibagger" not in thesis.core_thesis.lower()
        assert any("overconfident phrase" in note for note in thesis.data_limitations)

    def test_banned_phrase_in_catalyst_gets_neutralized(self):
        bad = _valid_response(catalysts=["This is a risk-free catalyst for guaranteed upside"])
        fake = FakeLLMClient(fixed_response=bad)
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
        )
        assert "risk-free" not in thesis.catalysts[0].lower()

    def test_banned_phrase_in_counterargument_gets_neutralized(self):
        bad = _valid_response(counterarguments=["Even bears agree this is a sure shot"])
        fake = FakeLLMClient(fixed_response=bad)
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
        )
        assert "sure shot" not in thesis.counterarguments[0].lower()

    def test_fewer_than_two_invalidation_triggers_flagged_in_limitations(self):
        bad = _valid_response(invalidation_triggers=[
            {"condition": "Only one trigger", "threshold_basis": "explicit_assumption", "metric_reference": None}
        ])
        fake = FakeLLMClient(fixed_response=bad)
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
        )
        assert len(thesis.invalidation_triggers) == 1
        assert any("Fewer than 2 thesis invalidation triggers" in note for note in thesis.data_limitations)

    def test_zero_invalidation_triggers_also_flagged(self):
        bad = _valid_response(invalidation_triggers=[])
        fake = FakeLLMClient(fixed_response=bad)
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
        )
        assert thesis.invalidation_triggers == []
        assert any("Fewer than 2" in note for note in thesis.data_limitations)

    def test_invalid_recommendation_value_raises(self):
        bad = _valid_response(recommendation="strong_buy_definitely")
        fake = FakeLLMClient(fixed_response=bad)
        with pytest.raises(LLMProviderError):
            generate_investment_thesis(
                company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
            )

    def test_missing_recommendation_field_raises(self):
        data = json.loads(_valid_response())
        del data["recommendation"]
        fake = FakeLLMClient(fixed_response=json.dumps(data))
        with pytest.raises(LLMProviderError):
            generate_investment_thesis(
                company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
            )

    def test_malformed_json_raises(self):
        fake = FakeLLMClient(fixed_response="this is not json")
        with pytest.raises(LLMProviderError):
            generate_investment_thesis(
                company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
            )

    def test_requires_human_review_always_true_even_for_clean_thesis(self):
        fake = FakeLLMClient(fixed_response=_valid_response())
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
        )
        assert thesis.requires_human_review is True

    def test_supporting_evidence_ids_populated_from_interpretation_claims(self):
        fake = FakeLLMClient(fixed_response=_valid_response())
        thesis = generate_investment_thesis(
            company_name="Test Co", metrics=[], trends=[],
            interpretation_claims=[("interp_a", "claim a"), ("interp_b", "claim b")],
            llm_client=fake,
        )
        assert thesis.supporting_evidence_ids == ["interp_a", "interp_b"]

    def test_buy_and_avoid_recommendations_also_parse_correctly(self):
        for rec in ("buy", "avoid"):
            fake = FakeLLMClient(fixed_response=_valid_response(recommendation=rec))
            thesis = generate_investment_thesis(
                company_name="Test Co", metrics=[], trends=[], interpretation_claims=[], llm_client=fake,
            )
            assert thesis.recommendation == Recommendation(rec)


class TestBannedPhrasesListIntegrity:
    def test_no_duplicate_entries(self):
        assert len(BANNED_PHRASES) == len(set(BANNED_PHRASES))

    def test_all_lowercase_for_consistent_matching(self):
        assert all(p == p.lower() for p in BANNED_PHRASES)

    def test_covers_spec_examples(self):
        spec_examples = ["guaranteed return", "certain multibagger", "risk-free"]
        for example in spec_examples:
            assert any(example in phrase or phrase in example for phrase in BANNED_PHRASES)
