"""Explicitly opted-in smoke test for real providers and their disk cache."""

from __future__ import annotations

import os

import pytest

from amg.config import get_settings
from amg.providers import (
    get_embedding_provider,
    get_llm_provider,
    last_provider_report,
    reset_provider_state,
)
from amg.providers.budget import budget_report


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not (
            os.getenv("AMG_RUN_LIVE_TESTS") == "1"
            and os.getenv("AMG_OFFLINE") == "0"
        ),
        reason="requires AMG_RUN_LIVE_TESTS=1 and AMG_OFFLINE=0",
    ),
]


def test_real_providers_increment_budget_and_repeat_from_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = int(budget_report()["calls_used"])
    monkeypatch.setenv("AMG_CACHE_MODE", "refresh")
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)

    text = "I completed my CA qualification in 2019."
    assert get_llm_provider().extract_candidates(text)
    assert len(get_embedding_provider().embed_query("CA qualification")) == 1024
    after_live = int(budget_report()["calls_used"])

    monkeypatch.setenv("AMG_CACHE_MODE", "read_write")
    get_settings.cache_clear()
    reset_provider_state()
    assert get_llm_provider().extract_candidates(text)

    after_cache = int(budget_report()["calls_used"])
    assert 2 <= after_live - before <= 3
    assert after_cache == after_live
    assert last_provider_report()["maker"]["served_by"] == "cache"

