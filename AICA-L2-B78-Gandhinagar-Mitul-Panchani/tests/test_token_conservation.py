"""Phase 2.5 tests for offline enforcement, caching, and live-call budgets."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest

import check_env
import amg.config as config_module
import amg.providers as provider_registry
import amg.providers.budget as budget_module
import amg.providers.cache as cache_module
from amg.config import get_settings
from amg.models import AssertionType, CandidateFact, SourceType
from amg.providers import (
    ProviderCallResult,
    get_embedding_provider,
    get_llm_provider,
    last_provider_report,
    reset_provider_state,
)
from amg.providers.budget import budget_report
from amg.providers.cache import ResponseCache, cache_entry_count
from amg.providers.llm_base import ProviderUnavailable
from amg.providers.llm_gemini import GeminiProvider
from amg.providers.embed_voyage import VoyageEmbeddingProvider


def _online_fake_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    cap: int = 10,
    cache_mode: str = "off",
) -> None:
    monkeypatch.setenv("AMG_OFFLINE", "0")
    monkeypatch.setenv("AMG_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("AMG_EMBED_PROVIDER", "voyage")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-voyage-key")
    monkeypatch.setenv("AMG_GEMINI_MODEL", "gemini-3.5-flash")
    monkeypatch.setenv("AMG_CACHE_MODE", cache_mode)
    monkeypatch.setenv("AMG_DAILY_LIVE_CALL_CAP", str(cap))
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(budget_module, "USAGE_PATH", tmp_path / "usage.json")
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)


def _fact(text: str) -> CandidateFact:
    return CandidateFact(
        content=text,
        subject_key="employer",
        category="professional",
        assertion_type=AssertionType.DIRECT_SELF_STATEMENT,
        source_type=SourceType.USER_STATED,
    )


class _FakeGemini:
    calls = 0
    constructed_models: list[str] = []

    def __init__(self, model: str, **_: object) -> None:
        self.model_version = model
        type(self).constructed_models.append(model)

    @property
    def name(self) -> str:
        return "gemini"

    def extract_candidates(self, user_text: str) -> list[CandidateFact]:
        type(self).calls += 1
        return [_fact(user_text)]

    def check_candidate(self, *_: object) -> Any:
        raise AssertionError("not used")

    def check_entailment(self, *_: object) -> Any:
        raise AssertionError("not used")


class _FakeVoyage:
    calls = 0

    def __init__(self, model: str, **_: object) -> None:
        self.model_version = model
        self.last_total_tokens = 7

    @property
    def dimensions(self) -> int:
        return 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        type(self).calls += 1
        return [[1.0] + [0.0] * 1023 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        type(self).calls += 1
        return [1.0] + [0.0] * 1023


def test_socket_guard_rejects_deliberate_outbound_connection() -> None:
    with pytest.raises(
        AssertionError, match=r"Test attempted network access to .*example\.com"
    ):
        socket.create_connection(("example.com", 443), timeout=0.01)


@pytest.mark.parametrize("truthy", ["1", "true", "TRUE", "yes", "YeS"])
def test_offline_truthy_values_are_accepted(
    monkeypatch: pytest.MonkeyPatch, truthy: str
) -> None:
    monkeypatch.setenv("AMG_OFFLINE", truthy)
    get_settings.cache_clear()
    assert get_settings().offline is True


def test_offline_defaults_true_without_an_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("AMG_OFFLINE", raising=False)
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    get_settings.cache_clear()
    assert get_settings().offline is True


def test_offline_mode_never_constructs_live_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AMG_OFFLINE", "1")
    monkeypatch.setenv("AMG_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("AMG_EMBED_PROVIDER", "voyage")
    monkeypatch.setenv("GEMINI_API_KEY", "present-but-must-not-be-used")
    monkeypatch.setenv("VOYAGE_API_KEY", "present-but-must-not-be-used")

    def forbidden(*_: object, **__: object) -> Any:
        raise AssertionError("live provider was constructed while offline")

    monkeypatch.setattr(provider_registry, "GeminiProvider", forbidden)
    monkeypatch.setattr(provider_registry, "VoyageEmbeddingProvider", forbidden)
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)

    assert get_llm_provider().extract_candidates("I work at Northwind.")
    assert len(get_embedding_provider().embed_query("Where do I work?")) == 256
    report = last_provider_report()
    assert report["maker"]["served_by"] == "blocked_offline"
    assert report["embedding_query"]["served_by"] == "blocked_offline"


def test_direct_live_provider_construction_is_blocked_by_offline_kill_switch() -> None:
    with pytest.raises(ProviderUnavailable, match="blocked by AMG_OFFLINE"):
        GeminiProvider(api_key="must-not-be-used", offline=False)
    with pytest.raises(ProviderUnavailable, match="blocked by AMG_OFFLINE"):
        VoyageEmbeddingProvider(api_key="must-not-be-used", offline=False)


def test_response_cache_modes_and_live_only_rule(tmp_path: Path) -> None:
    inputs = {"text": "same input"}
    writable = ResponseCache("read_write", tmp_path)
    writable.put("gemini", "model-a", "maker", inputs, {"ok": True}, served_by="live")
    assert writable.get("gemini", "model-a", "maker", inputs) == {"ok": True}

    read_only = ResponseCache("read_only", tmp_path)
    assert read_only.get("gemini", "model-a", "maker", inputs) == {"ok": True}
    read_only.put("gemini", "model-b", "maker", inputs, {}, served_by="live")
    assert cache_entry_count(tmp_path) == 1

    assert ResponseCache("off", tmp_path).get(
        "gemini", "model-a", "maker", inputs
    ) is None
    refresh = ResponseCache("refresh", tmp_path)
    assert refresh.get("gemini", "model-a", "maker", inputs) is None
    refresh.put("gemini", "model-a", "maker", inputs, {"ok": "new"}, served_by="live")
    assert writable.get("gemini", "model-a", "maker", inputs) == {"ok": "new"}

    live_first = ResponseCache("live_first", tmp_path)
    assert live_first.get("gemini", "model-a", "maker", inputs) is None
    assert live_first.get_fallback("gemini", "model-a", "maker", inputs) == {"ok": "new"}

    with pytest.raises(ValueError, match="genuine live"):
        writable.put("stub", "stub-rule-v1", "maker", inputs, {}, served_by="stub")


def test_repeated_identical_live_call_uses_cache_without_budget_charge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _online_fake_environment(monkeypatch, tmp_path, cache_mode="read_write")
    _FakeGemini.calls = 0
    _FakeGemini.constructed_models = []
    monkeypatch.setattr(provider_registry, "GeminiProvider", _FakeGemini)

    text = "I work at Northwind Textiles."
    assert get_llm_provider().extract_candidates(text)
    assert last_provider_report()["maker"]["served_by"] == "live"
    assert get_llm_provider().extract_candidates(text)

    assert _FakeGemini.calls == 1
    assert budget_report()["calls_used"] == 1
    assert cache_entry_count(tmp_path / "cache") == 1
    cache_document = json.loads(next((tmp_path / "cache").glob("*.json")).read_text())
    assert cache_document["served_by"] == "live"
    assert last_provider_report()["maker"]["served_by"] == "cache"


def test_repeated_identical_voyage_call_uses_cache_and_records_tokens(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _online_fake_environment(monkeypatch, tmp_path, cache_mode="read_write")
    _FakeVoyage.calls = 0
    monkeypatch.setattr(provider_registry, "VoyageEmbeddingProvider", _FakeVoyage)

    assert len(get_embedding_provider().embed_query("Where do I work?")) == 1024
    assert len(get_embedding_provider().embed_query("Where do I work?")) == 1024

    usage = budget_report()
    assert _FakeVoyage.calls == 1
    assert usage["calls_used"] == 1
    assert usage["providers"]["voyage"] == {
        "calls": 1,
        "tokens": 7,
        "models": {"voyage-4-lite": {"calls": 1, "tokens": 7}},
    }
    assert last_provider_report()["embedding_query"]["served_by"] == "cache"


def test_live_first_uses_prewarmed_real_response_only_after_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _online_fake_environment(monkeypatch, tmp_path, cache_mode="live_first")
    text = "I work at Northwind Textiles."
    ResponseCache("refresh", tmp_path / "cache").put(
        "gemini",
        "gemini-3.5-flash",
        "maker",
        {"user_text": text},
        [_fact(text).model_dump(mode="json")],
        served_by="live",
    )

    class FailingGemini(_FakeGemini):
        def extract_candidates(self, user_text: str) -> list[CandidateFact]:
            type(self).calls += 1
            raise ProviderUnavailable("simulated wifi drop")

    FailingGemini.calls = 0
    monkeypatch.setattr(provider_registry, "GeminiProvider", FailingGemini)

    candidates = get_llm_provider().extract_candidates(text)

    assert candidates == [_fact(text)]
    assert FailingGemini.calls == 1
    assert budget_report()["calls_used"] == 1
    assert last_provider_report()["maker"] == {
        "provider_name": "gemini",
        "model": "gemini-3.5-flash",
        "served_by": "cache_after_error",
        "was_fallback": False,
    }


def test_budget_cap_blocks_n_plus_one_and_registry_falls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _online_fake_environment(monkeypatch, tmp_path, cap=1, cache_mode="live_first")
    _FakeGemini.calls = 0
    _FakeGemini.constructed_models = []
    monkeypatch.setattr(provider_registry, "GeminiProvider", _FakeGemini)
    second_text = "I work at Silverline Logistics."
    ResponseCache("refresh", tmp_path / "cache").put(
        "gemini",
        "gemini-3.5-flash",
        "maker",
        {"user_text": second_text},
        [_fact(second_text).model_dump(mode="json")],
        served_by="live",
    )

    first = get_llm_provider().extract_candidates("I work at Northwind Textiles.")
    second = get_llm_provider().extract_candidates(second_text)

    assert first and second
    assert _FakeGemini.calls == 1
    assert budget_report()["calls_used"] == 1
    report = last_provider_report()["maker"]
    assert report == {
        "provider_name": "stub",
        "model": "stub-rule-v1",
        "served_by": "blocked_by_cap",
        "was_fallback": True,
    }


def test_genuine_provider_error_uses_stub_and_reports_error_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _online_fake_environment(monkeypatch, tmp_path, cache_mode="off")

    class FailingGemini(_FakeGemini):
        def extract_candidates(self, user_text: str) -> list[CandidateFact]:
            type(self).calls += 1
            raise ProviderUnavailable("simulated provider failure")

    FailingGemini.calls = 0
    monkeypatch.setattr(provider_registry, "GeminiProvider", FailingGemini)

    assert get_llm_provider().extract_candidates("I work at Northwind Textiles.")
    assert FailingGemini.calls == 1
    assert budget_report()["calls_used"] == 1
    assert last_provider_report()["maker"] == {
        "provider_name": "stub",
        "model": "stub-rule-v1",
        "served_by": "fallback_after_error",
        "was_fallback": True,
    }


@pytest.mark.parametrize(
    "served_by",
    [
        "live",
        "cache",
        "cache_after_error",
        "stub",
        "fallback_after_error",
        "blocked_by_cap",
        "blocked_offline",
    ],
)
def test_provider_call_result_accepts_every_honest_state(served_by: str) -> None:
    result = ProviderCallResult(
        provider_name="test",
        model="test-model",
        served_by=served_by,
        was_fallback=False,
    )

    assert result.served_by == served_by


def test_gemini_model_chain_skips_known_ineligible_model_and_remembers_winner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _online_fake_environment(monkeypatch, tmp_path, cap=10, cache_mode="off")
    monkeypatch.setenv("AMG_GEMINI_MODEL", "gemini-3.7-flash")

    class FallbackFake(_FakeGemini):
        def extract_candidates(self, user_text: str) -> list[CandidateFact]:
            type(self).calls += 1
            if self.model_version == "gemini-3.5-flash":
                error = ProviderUnavailable("rate limited")
                error.status_code = 429  # type: ignore[attr-defined]
                raise error
            return [_fact(user_text)]

    FallbackFake.calls = 0
    FallbackFake.constructed_models = []
    monkeypatch.setattr(provider_registry, "GeminiProvider", FallbackFake)
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)

    provider = get_llm_provider()
    assert provider.extract_candidates("I work at Northwind Textiles.")
    assert provider.extract_candidates("I work at Silverline Logistics.")

    assert FallbackFake.constructed_models == [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash-lite",
    ]
    assert "gemini-3.7-flash" not in FallbackFake.constructed_models


def test_repo_root_env_load_is_independent_of_current_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    elsewhere = tmp_path / "elsewhere"
    repo.mkdir()
    elsewhere.mkdir()
    (repo / ".env").write_text(
        "GEMINI_API_KEY=repo-root-test-key\nAMG_OFFLINE=1\n", encoding="utf-8"
    )
    monkeypatch.setattr(config_module, "REPO_ROOT", repo)
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    captured: dict[str, object] = {}

    def fake_load_dotenv(*, dotenv_path: Path, override: bool) -> bool:
        captured["dotenv_path"] = dotenv_path
        captured["override"] = override
        monkeypatch.setenv("GEMINI_API_KEY", "repo-root-test-key")
        return True

    monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)
    get_settings.cache_clear()

    assert get_settings().gemini_api_key == "repo-root-test-key"
    assert captured == {"dotenv_path": repo / ".env", "override": False}


def test_check_env_reports_required_state_without_provider_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(budget_module, "USAGE_PATH", tmp_path / "usage.json")
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)

    check_env.main()

    output = capsys.readouterr().out
    assert "Offline mode: ON" in output
    assert "Resolved LLM provider: stub" in output
    assert "Resolved embedding provider: local" in output
    assert "GEMINI_API_KEY present: no" in output
    assert "VOYAGE_API_KEY present: no" in output
    assert "Cache mode:" in output
    assert "Cache entries: 0" in output
    assert "Budget today (UTC):" in output
    assert provider_registry.last_provider_report() == {}
