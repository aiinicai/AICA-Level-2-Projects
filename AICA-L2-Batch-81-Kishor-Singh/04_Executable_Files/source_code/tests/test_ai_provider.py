"""Tests for core.ai_provider: request construction and response parsing for every
backend, using a mocked HTTP layer. No real network calls or API keys are used --
these tests verify the adapter's own logic, not a live provider's behaviour."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.ai_provider import AIProvider, AIProviderError, AIProviderKind, AIRequest, is_configured


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    """Route all key storage to an in-memory dict instead of the real OS credential store."""
    store: dict[str, str] = {}

    def fake_get_api_key(provider):
        return store.get(provider.value)

    def fake_save_api_key(provider, key):
        store[provider.value] = key

    monkeypatch.setattr("core.ai_provider.get_api_key", fake_get_api_key)
    monkeypatch.setattr("core.ai_provider.save_api_key", fake_save_api_key)
    return store


def _mock_response(json_data, status_code=200, ok=True):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = ok
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def test_is_configured_false_without_key():
    assert not is_configured(AIProviderKind.ANTHROPIC)


def test_is_configured_true_after_save(fake_keyring):
    from core.ai_provider import save_api_key

    save_api_key(AIProviderKind.ANTHROPIC, "sk-test-123")
    assert is_configured(AIProviderKind.ANTHROPIC)


def test_ollama_always_reports_configured_no_key_needed():
    assert is_configured(AIProviderKind.OLLAMA)


def test_cloud_call_without_key_raises_clear_error():
    provider = AIProvider(AIProviderKind.OPENAI)
    with pytest.raises(AIProviderError, match="not configured"):
        provider.complete(AIRequest(system_prompt="sys", user_prompt="hello"))


def test_anthropic_request_and_response(fake_keyring):
    from core.ai_provider import save_api_key

    save_api_key(AIProviderKind.ANTHROPIC, "sk-ant-test")
    provider = AIProvider(AIProviderKind.ANTHROPIC, model="claude-sonnet-5")

    with patch("core.ai_provider.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"content": [{"type": "text", "text": "Hello from Claude"}]})
        response = provider.complete(AIRequest(system_prompt="You are helpful.", user_prompt="Hi"))

    assert response.text == "Hello from Claude"
    assert response.provider == AIProviderKind.ANTHROPIC
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["headers"]["x-api-key"] == "sk-ant-test"
    assert call_kwargs.kwargs["json"]["model"] == "claude-sonnet-5"
    assert call_kwargs.kwargs["json"]["messages"][0]["content"] == "Hi"


def test_openai_request_and_response(fake_keyring):
    from core.ai_provider import save_api_key

    save_api_key(AIProviderKind.OPENAI, "sk-oa-test")
    provider = AIProvider(AIProviderKind.OPENAI, model="gpt-4o-mini")

    with patch("core.ai_provider.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"choices": [{"message": {"content": "Hello from GPT"}}]})
        response = provider.complete(AIRequest(system_prompt="sys", user_prompt="hi"))

    assert response.text == "Hello from GPT"
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer sk-oa-test"


def test_gemini_request_and_response(fake_keyring):
    from core.ai_provider import save_api_key

    save_api_key(AIProviderKind.GEMINI, "gm-test")
    provider = AIProvider(AIProviderKind.GEMINI, model="gemini-2.0-flash")

    with patch("core.ai_provider.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"candidates": [{"content": {"parts": [{"text": "Hello from Gemini"}]}}]})
        response = provider.complete(AIRequest(system_prompt="sys", user_prompt="hi"))

    assert response.text == "Hello from Gemini"
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["params"]["key"] == "gm-test"


def test_ollama_request_needs_no_api_key():
    provider = AIProvider(AIProviderKind.OLLAMA, model="llama3")
    with patch("core.ai_provider.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"response": "Hello from local model"})
        response = provider.complete(AIRequest(system_prompt="sys", user_prompt="hi"))
    assert response.text == "Hello from local model"


def test_http_error_raises_ai_provider_error(fake_keyring):
    from core.ai_provider import save_api_key

    save_api_key(AIProviderKind.ANTHROPIC, "sk-ant-test")
    provider = AIProvider(AIProviderKind.ANTHROPIC)
    with patch("core.ai_provider.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"error": "invalid_api_key"}, status_code=401, ok=False)
        with pytest.raises(AIProviderError, match="401"):
            provider.complete(AIRequest(system_prompt="sys", user_prompt="hi"))


def test_connection_error_raises_clear_message(fake_keyring):
    from core.ai_provider import save_api_key
    import requests

    save_api_key(AIProviderKind.ANTHROPIC, "sk-ant-test")
    provider = AIProvider(AIProviderKind.ANTHROPIC)
    with patch("core.ai_provider.requests.post", side_effect=requests.ConnectionError()):
        with pytest.raises(AIProviderError, match="internet connection"):
            provider.complete(AIRequest(system_prompt="sys", user_prompt="hi"))
