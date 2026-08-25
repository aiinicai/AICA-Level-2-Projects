"""Tests for the Gemini provider addition: GeminiClient (mocked SDK,
no live call), FallbackLLMClient (real fallback behavior using
FakeLLMClient stand-ins), and get_default_llm_client()'s provider
selection across every key-configuration combination.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.ai.llm_client import (
    FallbackLLMClient,
    FakeLLMClient,
    GeminiClient,
    OpenAIClient,
    get_default_llm_client,
)
from app.config import get_settings
from app.core.exceptions import ConfigurationError, LLMProviderError


@pytest.fixture
def clean_llm_env(monkeypatch):
    """Force BOTH provider keys to be genuinely absent for a test,
    regardless of the ambient environment OR a real .env file on disk.

    Just clearing os.environ (via monkeypatch.delenv) is NOT sufficient
    on its own — Settings is configured with
    `env_file=str(_PROJECT_ROOT / ".env")`, an absolute path, so
    pydantic-settings reads that file DIRECTLY when Settings() is
    constructed, completely independent of os.environ. A real .env file
    on disk (which the project owner's actual machine has, with real
    working keys) would still leak through even after delenv, which is
    exactly the bug this fixture originally had — it worked in a
    sandbox with no real .env file, but failed on the real target
    machine. Redirecting model_config["env_file"] to a nonexistent path
    for the fixture's duration closes that gap completely; monkeypatch
    reverts it automatically after the test.
    """
    from app.config import Settings

    monkeypatch.setitem(Settings.model_config, "env_file", "/nonexistent/no-such-file.env")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


class TestRequireAnyLlmKey:
    def test_raises_when_neither_key_set(self, clean_llm_env):
        with pytest.raises(ConfigurationError, match="Neither GOOGLE_API_KEY nor OPENAI_API_KEY"):
            get_settings().require_any_llm_key()

    def test_does_not_raise_when_only_google_set(self, clean_llm_env):
        clean_llm_env.setenv("GOOGLE_API_KEY", "fake-key")
        get_settings.cache_clear()
        get_settings().require_any_llm_key()

    def test_does_not_raise_when_only_openai_set(self, clean_llm_env):
        clean_llm_env.setenv("OPENAI_API_KEY", "fake-key")
        get_settings.cache_clear()
        get_settings().require_any_llm_key()


class TestRequireGoogleKey:
    def test_raises_when_unset(self, clean_llm_env):
        with pytest.raises(ConfigurationError, match="GOOGLE_API_KEY is not set"):
            get_settings().require_google_key()

    def test_returns_key_when_set(self, clean_llm_env):
        clean_llm_env.setenv("GOOGLE_API_KEY", "fake-key")
        get_settings.cache_clear()
        assert get_settings().require_google_key() == "fake-key"


class TestGetDefaultLlmClientProviderSelection:
    def test_neither_configured_raises(self, clean_llm_env):
        with pytest.raises(ConfigurationError):
            get_default_llm_client()

    def test_only_google_configured_returns_gemini_client(self, clean_llm_env):
        clean_llm_env.setenv("GOOGLE_API_KEY", "fake-key")
        get_settings.cache_clear()
        client = get_default_llm_client()
        assert isinstance(client, GeminiClient)

    def test_only_openai_configured_returns_openai_client(self, clean_llm_env):
        clean_llm_env.setenv("OPENAI_API_KEY", "fake-key")
        get_settings.cache_clear()
        client = get_default_llm_client()
        assert isinstance(client, OpenAIClient)

    def test_both_configured_returns_fallback_with_gemini_primary(self, clean_llm_env):
        clean_llm_env.setenv("GOOGLE_API_KEY", "fake-google-key")
        clean_llm_env.setenv("OPENAI_API_KEY", "fake-openai-key")
        get_settings.cache_clear()
        client = get_default_llm_client()
        assert isinstance(client, FallbackLLMClient)
        assert isinstance(client._primary, GeminiClient)
        assert isinstance(client._secondary, OpenAIClient)


class TestGeminiClientConstruction:
    def test_raises_without_key(self, clean_llm_env):
        with pytest.raises(ConfigurationError):
            GeminiClient()

    def test_constructs_with_key(self, clean_llm_env):
        clean_llm_env.setenv("GOOGLE_API_KEY", "fake-key")
        get_settings.cache_clear()
        client = GeminiClient()
        assert client._model == "gemini-3.5-flash-lite"

    def test_explicit_model_override(self, clean_llm_env):
        clean_llm_env.setenv("GOOGLE_API_KEY", "fake-key")
        get_settings.cache_clear()
        client = GeminiClient(model="gemini-2.5-flash")
        assert client._model == "gemini-2.5-flash"


class TestGeminiClientCompleteMocked:
    def _client_with_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        get_settings.cache_clear()
        return GeminiClient()

    def test_successful_response_parsed_correctly(self, clean_llm_env):
        client = self._client_with_key(clean_llm_env)

        mock_response = MagicMock()
        mock_response.text = "Test response from Gemini"
        mock_response.candidates = []

        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_genai_client):
            result = client.complete(system="You are helpful.", user="Say hi.")

        assert result.text == "Test response from Gemini"
        assert result.model == "gemini-3.5-flash-lite"

    def test_api_failure_wrapped_as_llm_provider_error(self, clean_llm_env):
        client = self._client_with_key(clean_llm_env)

        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = Exception("rate limit exceeded")

        with patch("google.genai.Client", return_value=mock_genai_client):
            with pytest.raises(LLMProviderError, match="Gemini API call failed"):
                client.complete(system="test", user="test")

    def test_system_and_user_passed_through_correctly(self, clean_llm_env):
        client = self._client_with_key(clean_llm_env)

        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_response.candidates = []
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_genai_client):
            client.complete(system="SYSTEM_INSTRUCTIONS", user="USER_CONTENT")

        call_kwargs = mock_genai_client.models.generate_content.call_args.kwargs
        assert call_kwargs["contents"] == "USER_CONTENT"
        assert call_kwargs["config"].system_instruction == "SYSTEM_INSTRUCTIONS"

    def test_sdk_internal_retries_disabled_so_failures_surface_fast(self, clean_llm_env):
        """Regression test for a real bug a user hit: the google-genai
        SDK has its own internal retry-with-backoff hidden inside
        generate_content() (up to 4 attempts, backoff capped at 60s
        EACH). On a rate-limited free-tier account this silently
        absorbed up to ~3 minutes per call before ever raising an
        exception back to our code — confirmed via a real user's logs
        showing consistent ~2m51s gaps between calls. That defeated
        FallbackLLMClient's purpose: it can only fall back to OpenAI
        AFTER Gemini's own internal retry loop gives up. Fixed by
        passing retry_options=HttpRetryOptions(attempts=1) to the SDK
        client, so a rate-limit/transient error raises immediately and
        THIS project's own pacing/fallback logic handles recovery
        instead. This test locks in that exact configuration."""
        client = self._client_with_key(clean_llm_env)

        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_response.candidates = []
        mock_genai_client_class = MagicMock()
        mock_genai_client_class.return_value.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", mock_genai_client_class):
            client.complete(system="s", user="u")

        constructor_kwargs = mock_genai_client_class.call_args.kwargs
        http_options = constructor_kwargs["http_options"]
        assert http_options.retry_options.attempts == 1, (
            "SDK-internal retries must be disabled (attempts=1) so a "
            "rate-limited call fails fast instead of silently retrying "
            "for minutes before FallbackLLMClient ever gets a chance to "
            "fall back to OpenAI."
        )


class TestFallbackLlmClient:
    def test_primary_success_never_touches_secondary(self):
        primary = FakeLLMClient(fixed_response="Primary response")
        secondary = FakeLLMClient(fixed_response="Should never be used")
        fallback = FallbackLLMClient(primary, secondary)

        result = fallback.complete(system="s", user="u")
        assert result.text == "Primary response"
        assert len(secondary.calls) == 0

    def test_primary_failure_falls_back_to_secondary(self):
        class AlwaysFailsClient:
            def complete(self, **kwargs):
                raise LLMProviderError("Simulated failure")

        secondary = FakeLLMClient(fixed_response="Fallback response")
        fallback = FallbackLLMClient(AlwaysFailsClient(), secondary)

        result = fallback.complete(system="s", user="u")
        assert result.text == "Fallback response"
        assert len(secondary.calls) == 1

    def test_both_fail_propagates_secondary_error(self):
        class AlwaysFailsClient:
            def __init__(self, message):
                self._message = message

            def complete(self, **kwargs):
                raise LLMProviderError(self._message)

        primary = AlwaysFailsClient("primary failed")
        secondary = AlwaysFailsClient("secondary also failed")
        fallback = FallbackLLMClient(primary, secondary)

        with pytest.raises(LLMProviderError, match="secondary also failed"):
            fallback.complete(system="s", user="u")

    def test_arguments_forwarded_correctly_to_primary(self):
        primary = FakeLLMClient(fixed_response="ok")
        secondary = FakeLLMClient(fixed_response="unused")
        fallback = FallbackLLMClient(primary, secondary)

        fallback.complete(system="SYS", user="USR", max_tokens=100, temperature=0.7)
        assert primary.calls[0] == {"system": "SYS", "user": "USR", "max_tokens": 100, "temperature": 0.7}

    def test_arguments_forwarded_correctly_to_secondary_on_fallback(self):
        class AlwaysFailsClient:
            def complete(self, **kwargs):
                raise LLMProviderError("fail")

        secondary = FakeLLMClient(fixed_response="ok")
        fallback = FallbackLLMClient(AlwaysFailsClient(), secondary)

        fallback.complete(system="SYS", user="USR", max_tokens=50, temperature=0.1)
        assert secondary.calls[0] == {"system": "SYS", "user": "USR", "max_tokens": 50, "temperature": 0.1}
