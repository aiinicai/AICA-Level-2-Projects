"""Tests for app/ai/rate_limiting.py's estimate functions, and the
delay_seconds/progress_callback wiring added to all three batch
extraction functions - the fix for a real multi-minute retry storm a
user hit processing a genuine 194-page document.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.ai.document_analysis import analyze_evidence_batch
from app.ai.llm_client import FakeLLMClient
from app.ai.pledge_extraction import extract_pledge_disclosure_batch
from app.ai.rate_limiting import (
    DEFAULT_REQUEST_DELAY_SECONDS,
    estimate_batch_duration_seconds,
    format_duration_estimate,
)
from app.analysis.risk import extract_risks_batch
from app.config import get_settings
from app.core.enums import DocumentSectionType, DocumentType, ExchangeCode
from app.core.models import Company, DocumentEvidence

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def no_llm_key(monkeypatch):
    """Force BOTH OPENAI_API_KEY and GOOGLE_API_KEY to be absent for a
    test, regardless of whatever real key(s) might be configured in the
    actual environment running this suite (e.g. a developer's own .env
    with real, working keys — which IS the case on this project's real
    target machine, and caused this exact test to silently make a REAL,
    successful API call instead of testing the "no key" error path, a
    real test-isolation bug found via a real run — three times now,
    once for OPENAI_API_KEY alone, again once GOOGLE_API_KEY became a
    second valid way to satisfy require_any_llm_key(), and a third time
    once it became clear that clearing os.environ alone isn't enough:
    Settings reads GOOGLE_API_KEY/OPENAI_API_KEY directly from a real
    .env file on disk via pydantic-settings' env_file config, entirely
    independent of os.environ — so monkeypatch.delenv alone leaves a
    real .env file's keys fully intact. Redirecting
    Settings.model_config["env_file"] to a nonexistent path closes that
    gap completely. get_settings() is cached via @lru_cache, so the
    cache must be cleared both before (to pick up the patched config)
    and after (so real keys aren't left permanently shadowed by a
    cached "no key" Settings object for the rest of the test session)."""
    from app.config import Settings

    monkeypatch.setitem(Settings.model_config, "env_file", "/nonexistent/no-such-file.env")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestEstimateBatchDuration:
    def test_zero_pages_returns_zero(self):
        assert estimate_batch_duration_seconds(0, 0.5) == (0.0, 0.0)

    def test_negative_pages_returns_zero(self):
        assert estimate_batch_duration_seconds(-5, 0.5) == (0.0, 0.0)

    def test_more_pages_means_longer_estimate(self):
        small = estimate_batch_duration_seconds(5, 0.5)
        large = estimate_batch_duration_seconds(50, 0.5)
        assert large[0] > small[0]
        assert large[1] > small[1]

    def test_higher_delay_means_longer_estimate(self):
        low_delay = estimate_batch_duration_seconds(10, 0.1)
        high_delay = estimate_batch_duration_seconds(10, 2.0)
        assert high_delay[0] > low_delay[0]

    def test_max_is_always_at_least_min(self):
        min_s, max_s = estimate_batch_duration_seconds(20, 0.5)
        assert max_s >= min_s

    def test_known_194_page_scenario_produces_a_multi_minute_estimate(self):
        min_s, max_s = estimate_batch_duration_seconds(194, DEFAULT_REQUEST_DELAY_SECONDS)
        assert min_s > 60


class TestFormatDurationEstimate:
    def test_short_duration_says_under_a_minute(self):
        assert format_duration_estimate(5.0, 15.0) == "under a minute"

    def test_longer_duration_formatted_in_minutes(self):
        result = format_duration_estimate(180.0, 450.0)
        assert "minutes" in result
        assert "3.0" in result
        assert "7.5" in result

    def test_boundary_at_exactly_60_seconds(self):
        assert format_duration_estimate(30.0, 59.9) == "under a minute"
        assert "minutes" in format_duration_estimate(30.0, 60.0)


class TestPacingAndProgressAcrossAllThreeBatchFunctions:
    def _pages(self, n=3):
        return [
            DocumentEvidence(source_document="test.pdf", page_number=i, raw_text=f"page {i}")
            for i in range(1, n + 1)
        ]

    def test_analyze_evidence_batch_pacing_and_progress(self):
        pages = self._pages(3)
        fake = FakeLLMClient(fixed_response='{"claim": "test", "confidence": "high"}')
        progress_log = []

        start = time.time()
        results = analyze_evidence_batch(
            pages, fake, delay_seconds=0.2, progress_callback=lambda c, t: progress_log.append((c, t)),
        )
        elapsed = time.time() - start

        assert len(results) == 3
        assert progress_log == [(1, 3), (2, 3), (3, 3)]
        assert elapsed >= 0.35
        assert elapsed < 1.0

    def test_extract_risks_batch_pacing_and_progress(self):
        pages = self._pages(3)
        fake = FakeLLMClient(fixed_response=(
            '{"category": "financial", "description": "test risk", "severity": "low"}'
        ))
        progress_log = []

        results = extract_risks_batch(
            pages, fake, delay_seconds=0.1, progress_callback=lambda c, t: progress_log.append((c, t)),
        )
        assert progress_log == [(1, 3), (2, 3), (3, 3)]
        assert isinstance(results, list)

    def test_extract_pledge_disclosure_batch_pacing_and_progress(self):
        pages = self._pages(3)
        fake = FakeLLMClient(fixed_response=(
            '{"disclosure_found": true, "pledge_pct_of_target_company_shares": 0, '
            '"status": "not_applicable", "as_of_date": "2021-06-24", "summary": "test"}'
        ))
        progress_log = []

        results = extract_pledge_disclosure_batch(
            pages, fake, delay_seconds=0.1, progress_callback=lambda c, t: progress_log.append((c, t)),
        )
        assert progress_log == [(1, 3), (2, 3), (3, 3)]
        assert len(results) == 3

    def test_progress_advances_even_when_a_page_fails(self):
        pages = self._pages(3)
        fake = FakeLLMClient(responses=["not json", "not json", "not json"])
        progress_log = []

        results = analyze_evidence_batch(
            pages, fake, progress_callback=lambda c, t: progress_log.append((c, t)),
        )
        assert results == []
        assert progress_log == [(1, 3), (2, 3), (3, 3)]

    def test_zero_delay_does_not_pause(self):
        pages = self._pages(3)
        fake = FakeLLMClient(fixed_response='{"claim": "test", "confidence": "high"}')
        start = time.time()
        analyze_evidence_batch(pages, fake, delay_seconds=0.0)
        elapsed = time.time() - start
        assert elapsed < 0.3

    def test_default_delay_is_zero_for_backward_compatibility(self):
        pages = self._pages(2)
        fake = FakeLLMClient(fixed_response='{"claim": "test", "confidence": "high"}')
        start = time.time()
        analyze_evidence_batch(pages, fake)
        elapsed = time.time() - start
        assert elapsed < 0.3


class TestRiskDashboardConfirmFlow:
    def _app_with_risk_pages(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.session_state["company"] = Company(
            name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE,
        )
        at.session_state["document_evidence"] = [
            DocumentEvidence(
                source_document="Test AR", page_number=1, section=DocumentSectionType.RISK,
                document_type=DocumentType.ANNUAL_REPORT, raw_text="Some risk-relevant text.",
            ),
        ]
        at.run()
        at.sidebar.radio[0].set_value("Risk Dashboard").run()
        return at

    def test_trigger_shows_estimate_and_confirm_cancel_buttons(self):
        at = self._app_with_risk_pages()
        trigger_btn = next(b for b in at.button if b.label == "Extract Qualitative Risks from Document")
        trigger_btn.click().run()
        assert list(at.exception) == []

        warnings = [w.value for w in at.warning]
        assert any("estimated" in w for w in warnings)
        assert any(b.label == "Confirm and Run" for b in at.button)
        assert any(b.label == "Cancel" for b in at.button)

    def test_cancel_dismisses_the_confirmation(self):
        at = self._app_with_risk_pages()
        trigger_btn = next(b for b in at.button if b.label == "Extract Qualitative Risks from Document")
        trigger_btn.click().run()

        cancel_btn = next(b for b in at.button if b.label == "Cancel")
        cancel_btn.click().run()
        assert list(at.exception) == []
        assert not any(b.label == "Confirm and Run" for b in at.button)

    def test_confirm_without_api_key_errors_gracefully(self, no_llm_key):
        at = self._app_with_risk_pages()
        trigger_btn = next(b for b in at.button if b.label == "Extract Qualitative Risks from Document")
        trigger_btn.click().run()

        confirm_btn = next(b for b in at.button if b.label == "Confirm and Run")
        confirm_btn.click().run()
        assert list(at.exception) == []
        errors = [e.value for e in at.error]
        assert any("OPENAI_API_KEY" in e for e in errors)

    def test_all_three_extraction_sections_use_the_same_confirm_flow(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.session_state["company"] = Company(
            name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE,
        )
        at.session_state["document_evidence"] = [
            DocumentEvidence(source_document="AR", page_number=1, section=DocumentSectionType.RISK,
                              document_type=DocumentType.ANNUAL_REPORT, raw_text="risk text"),
            DocumentEvidence(source_document="AR", page_number=2, section=DocumentSectionType.BUSINESS,
                              document_type=DocumentType.ANNUAL_REPORT, raw_text="business text"),
            DocumentEvidence(source_document="Pledge", page_number=1,
                              document_type=DocumentType.PLEDGE_DISCLOSURE, raw_text="pledge text"),
        ]
        at.run()
        at.sidebar.radio[0].set_value("Risk Dashboard").run()
        assert list(at.exception) == []

        button_labels = {b.label for b in at.button}
        assert "Extract Qualitative Risks from Document" in button_labels
        assert "Extract Business & Management Commentary" in button_labels
        assert "Analyze Pledge Disclosure" in button_labels

    def test_estimate_message_names_gemini_when_configured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-google-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        get_settings.cache_clear()
        try:
            at = self._app_with_risk_pages()
            trigger_btn = next(b for b in at.button if b.label == "Extract Qualitative Risks from Document")
            trigger_btn.click().run()
            warnings = [w.value for w in at.warning]
            assert any("Google Gemini" in w for w in warnings)
        finally:
            get_settings.cache_clear()

    def test_estimate_message_mentions_fallback_when_both_configured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-google-key")
        monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")
        get_settings.cache_clear()
        try:
            at = self._app_with_risk_pages()
            trigger_btn = next(b for b in at.button if b.label == "Extract Qualitative Risks from Document")
            trigger_btn.click().run()
            warnings = [w.value for w in at.warning]
            assert any("automatic fallback" in w for w in warnings)
        finally:
            get_settings.cache_clear()
