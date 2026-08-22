"""Tests for app/ai/pricing.py, app/ai/llm_client.py's
UsageTrackingLLMClient, and the sidebar cost-estimate display.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.ai.llm_client import (
    FakeLLMClient,
    FallbackLLMClient,
    UsageTrackingLLMClient,
    infer_provider_label,
)
from app.ai.pricing import estimate_cost_usd, is_known_model
from app.core.enums import ExchangeCode
from app.core.exceptions import LLMProviderError
from app.core.models import Company

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestEstimateCostUsd:
    def test_gpt4o_known_rate_calculated_correctly(self):
        cost = estimate_cost_usd("gpt-4o", 1000, 500)
        assert cost == pytest.approx(1000 / 1e6 * 2.50 + 500 / 1e6 * 10.00)

    def test_gemini_flash_lite_known_rate_calculated_correctly(self):
        cost = estimate_cost_usd("gemini-3.5-flash-lite", 1000, 500)
        assert cost == pytest.approx(1000 / 1e6 * 0.30 + 500 / 1e6 * 2.50)

    def test_unknown_model_returns_none_not_zero(self):
        assert estimate_cost_usd("some-future-model-2027", 1000, 500) is None

    def test_none_prompt_tokens_returns_none(self):
        assert estimate_cost_usd("gpt-4o", None, 500) is None

    def test_none_completion_tokens_returns_none(self):
        assert estimate_cost_usd("gpt-4o", 1000, None) is None

    def test_none_model_returns_none(self):
        assert estimate_cost_usd(None, 1000, 500) is None

    def test_zero_tokens_returns_zero_cost_not_none(self):
        assert estimate_cost_usd("gpt-4o", 0, 0) == 0.0


class TestIsKnownModel:
    def test_known_models(self):
        assert is_known_model("gpt-4o") is True
        assert is_known_model("gemini-3.5-flash-lite") is True

    def test_unknown_model(self):
        assert is_known_model("made-up-model") is False

    def test_none_model(self):
        assert is_known_model(None) is False


class TestInferProviderLabel:
    def test_gemini_models(self):
        assert infer_provider_label("gemini-3.5-flash-lite") == "Gemini"
        assert infer_provider_label("gemini-2.5-pro") == "Gemini"

    def test_openai_models(self):
        assert infer_provider_label("gpt-4o") == "OpenAI"
        assert infer_provider_label("gpt-4o-mini") == "OpenAI"
        assert infer_provider_label("o3-mini") == "OpenAI"

    def test_unrecognized_model(self):
        assert infer_provider_label("claude-opus-4") == "Unknown"

    def test_none_model(self):
        assert infer_provider_label(None) == "Unknown"


class TestUsageTrackingLlmClient:
    def test_records_one_entry_per_call(self):
        usage_log = []
        inner = FakeLLMClient(fixed_response="x", model_name="gpt-4o", prompt_tokens=100, completion_tokens=50)
        tracked = UsageTrackingLLMClient(inner, usage_log)

        tracked.complete(system="s", user="u")
        tracked.complete(system="s", user="u")

        assert len(usage_log) == 2

    def test_entry_contains_correct_fields(self):
        usage_log = []
        inner = FakeLLMClient(fixed_response="x", model_name="gpt-4o", prompt_tokens=1000, completion_tokens=500)
        tracked = UsageTrackingLLMClient(inner, usage_log)
        tracked.complete(system="s", user="u")

        entry = usage_log[0]
        assert entry["provider"] == "OpenAI"
        assert entry["model"] == "gpt-4o"
        assert entry["prompt_tokens"] == 1000
        assert entry["completion_tokens"] == 500
        assert entry["estimated_cost_usd"] == pytest.approx(1000 / 1e6 * 2.50 + 500 / 1e6 * 10.00)
        assert "timestamp" in entry

    def test_gemini_entry_correctly_labeled(self):
        usage_log = []
        inner = FakeLLMClient(fixed_response="x", model_name="gemini-3.5-flash-lite", prompt_tokens=2000, completion_tokens=300)
        tracked = UsageTrackingLLMClient(inner, usage_log)
        tracked.complete(system="s", user="u")

        assert usage_log[0]["provider"] == "Gemini"

    def test_unpriced_model_records_none_cost_not_excluded(self):
        usage_log = []
        inner = FakeLLMClient(fixed_response="x", model_name="future-model", prompt_tokens=1000, completion_tokens=500)
        tracked = UsageTrackingLLMClient(inner, usage_log)
        tracked.complete(system="s", user="u")

        assert len(usage_log) == 1
        assert usage_log[0]["estimated_cost_usd"] is None

    def test_response_passed_through_unchanged(self):
        usage_log = []
        inner = FakeLLMClient(fixed_response="the actual response text", model_name="gpt-4o")
        tracked = UsageTrackingLLMClient(inner, usage_log)
        response = tracked.complete(system="s", user="u")
        assert response.text == "the actual response text"

    def test_provider_correctly_attributed_through_fallback(self):
        usage_log = []

        class AlwaysFails:
            def complete(self, **kwargs):
                raise LLMProviderError("simulated Gemini failure")

        secondary = FakeLLMClient(fixed_response="fallback response", model_name="gpt-4o",
                                   prompt_tokens=800, completion_tokens=200)
        fallback = FallbackLLMClient(AlwaysFails(), secondary)
        tracked = UsageTrackingLLMClient(fallback, usage_log)
        tracked.complete(system="s", user="u")

        assert len(usage_log) == 1
        assert usage_log[0]["provider"] == "OpenAI"

    def test_shared_log_accumulates_across_multiple_wrapped_clients(self):
        usage_log = []
        client_a = UsageTrackingLLMClient(
            FakeLLMClient(fixed_response="a", model_name="gpt-4o", prompt_tokens=100, completion_tokens=50),
            usage_log,
        )
        client_b = UsageTrackingLLMClient(
            FakeLLMClient(fixed_response="b", model_name="gemini-3.5-flash-lite", prompt_tokens=200, completion_tokens=100),
            usage_log,
        )
        client_a.complete(system="s", user="u")
        client_b.complete(system="s", user="u")
        assert len(usage_log) == 2
        assert {e["provider"] for e in usage_log} == {"OpenAI", "Gemini"}


class TestSidebarCostDisplay:
    def _app_with_company(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.session_state["company"] = Company(name="Test Co", ticker="TEST", exchange=ExchangeCode.NSE)
        return at

    def test_empty_log_shows_no_calls_message(self):
        at = self._app_with_company()
        at.run()
        assert list(at.exception) == []
        captions = [c.value for c in at.sidebar.caption]
        assert any("No AI-assisted calls made yet" in c for c in captions)

    def test_populated_log_shows_total_and_breakdown(self):
        from datetime import datetime, timezone

        at = self._app_with_company()
        at.session_state["llm_usage_log"] = [
            {"timestamp": datetime.now(timezone.utc), "provider": "Gemini", "model": "gemini-3.5-flash-lite",
             "prompt_tokens": 5000, "completion_tokens": 800, "estimated_cost_usd": 0.0035},
            {"timestamp": datetime.now(timezone.utc), "provider": "OpenAI", "model": "gpt-4o",
             "prompt_tokens": 1000, "completion_tokens": 500, "estimated_cost_usd": 0.0075},
        ]
        at.run()
        assert list(at.exception) == []

        metrics = {m.label: m.value for m in at.sidebar.metric}
        assert metrics["Total (this session)"] == "$0.0110"

        captions = [c.value for c in at.sidebar.caption]
        assert any("Gemini: $0.0035" in c for c in captions)
        assert any("OpenAI: $0.0075" in c for c in captions)

    def test_unpriced_calls_excluded_from_total_but_noted(self):
        from datetime import datetime, timezone

        at = self._app_with_company()
        at.session_state["llm_usage_log"] = [
            {"timestamp": datetime.now(timezone.utc), "provider": "Unknown", "model": "future-model",
             "prompt_tokens": 1000, "completion_tokens": 500, "estimated_cost_usd": None},
        ]
        at.run()
        assert list(at.exception) == []

        metrics = {m.label: m.value for m in at.sidebar.metric}
        assert metrics["Total (this session)"] == "$0.0000"

        captions = [c.value for c in at.sidebar.caption]
        assert any("1 call(s) excluded" in c for c in captions)

    def test_disclaimer_and_dashboard_links_present(self):
        from datetime import datetime, timezone

        at = self._app_with_company()
        at.session_state["llm_usage_log"] = [
            {"timestamp": datetime.now(timezone.utc), "provider": "OpenAI", "model": "gpt-4o",
             "prompt_tokens": 100, "completion_tokens": 50, "estimated_cost_usd": 0.00075},
        ]
        at.run()
        captions = [c.value for c in at.sidebar.caption]
        assert any("Rough estimate only" in c for c in captions)
        assert any("platform.openai.com/account/usage" in c for c in captions)
        assert any("aistudio.google.com/usage" in c for c in captions)
