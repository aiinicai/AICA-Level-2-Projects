"""AI helpers: provider detection, model lists and replies, with the network replaced by fakes."""
import pytest

from advtax import ai


class FakeResponse:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data


@pytest.fixture
def net(monkeypatch):
    """Records every request and answers from a table keyed by a fragment of the URL."""
    calls, answers = [], {}

    def fake(method, url, headers=None, json=None, timeout=None):
        calls.append({"method": method, "url": url, "headers": headers, "json": json})
        for fragment, (status, data) in answers.items():
            if fragment in url:
                return FakeResponse(status, data)
        return FakeResponse(404, {"error": {"message": "no such url"}})

    import requests
    monkeypatch.setattr(requests, "request", fake)
    return calls, answers


@pytest.mark.parametrize("key,expected", [
    ("sk-ant-api03-abc", "anthropic"), ("sk-proj-abc", "openai"), ("sk-abc", "openai"),
    ("AIzaSyabc", "gemini"), ("  AIzaSyabc ", "gemini"), ("something-else", None), ("", None)])
def test_detect_provider(key, expected):
    assert ai.detect_provider(key) == expected


def test_unknown_key_needs_a_provider():
    with pytest.raises(ai.AIError):
        ai.ask("hi", "mystery-key", "m")


def test_anthropic_models_and_reply(net):
    calls, answers = net
    answers["anthropic.com/v1/models"] = (200, {"data": [
        {"id": "claude-old", "display_name": "Old", "created_at": "2024-01-01"},
        {"id": "claude-sonnet-new", "display_name": "Sonnet New", "created_at": "2026-01-01"}]})
    answers["anthropic.com/v1/messages"] = (200, {"content": [{"type": "text", "text": " Pay by 15 Dec. "}]})
    models = ai.list_models("sk-ant-x")
    assert [m["id"] for m in models] == ["claude-sonnet-new", "claude-old"]
    assert ai.suggested_model(models, "anthropic") == "claude-sonnet-new"
    assert ai.ask("q", "sk-ant-x", "claude-sonnet-new") == "Pay by 15 Dec."
    assert calls[-1]["headers"]["x-api-key"] == "sk-ant-x"
    assert calls[-1]["json"]["model"] == "claude-sonnet-new"


def test_openai_models_are_filtered_and_reply(net):
    calls, answers = net
    answers["openai.com/v1/models"] = (200, {"data": [
        {"id": "gpt-4o", "created": 5}, {"id": "gpt-4o-mini", "created": 6}, {"id": "whisper-1", "created": 9},
        {"id": "text-embedding-3-small", "created": 8}, {"id": "gpt-4o-audio-preview", "created": 7},
        {"id": "o3", "created": 4}]})
    answers["chat/completions"] = (200, {"choices": [{"message": {"content": "Namaste"}}]})
    models = ai.list_models("sk-proj-x")
    assert [m["id"] for m in models] == ["gpt-4o-mini", "gpt-4o", "o3"]
    assert ai.suggested_model(models, "openai") == "gpt-4o-mini"
    assert ai.ask("q", "sk-proj-x", "gpt-4o") == "Namaste"
    assert calls[-1]["headers"]["Authorization"] == "Bearer sk-proj-x"


def test_gemini_models_are_filtered_and_reply(net):
    calls, answers = net
    answers["googleapis.com/v1beta/models?"] = (200, {"models": [
        {"name": "models/gemini-2.5-flash", "displayName": "Gemini 2.5 Flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/gemini-2.5-flash-image", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemma-3", "supportedGenerationMethods": ["generateContent"]}]})
    answers[":generateContent"] = (200, {"candidates": [{"content": {"parts": [{"text": "Theek "}, {"text": "hai"}]}}]})
    models = ai.list_models("AIzaX")
    assert models == [{"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash"}]
    assert ai.ask("q", "AIzaX", "gemini-2.5-flash") == "Theek hai"
    assert "gemini-2.5-flash:generateContent" in calls[-1]["url"]
    assert "AIzaX" not in calls[-1]["url"]  # the key travels in a header, never in the address


def test_bad_key_gives_a_plain_message(net):
    _, answers = net
    answers["openai.com/v1/models"] = (401, {"error": {"message": "Incorrect API key provided"}})
    with pytest.raises(ai.AIError, match="key was not accepted"):
        ai.list_models("sk-bad")


def test_provider_can_be_forced(net):
    calls, answers = net
    answers["anthropic.com/v1/messages"] = (200, {"content": [{"type": "text", "text": "ok"}]})
    assert ai.ask("q", "odd-looking-key", "m", provider="anthropic") == "ok"


def test_classify_ledgers_keeps_only_valid_types(net):
    _, answers = net
    answers["chat/completions"] = (200, {"choices": [{"message": {"content":
        'Here you go: {"Sales A": "Income", "Rent": "Expense", "Odd": "Banana"}'}}]})
    assert ai.classify_ledgers([{"ledger": "Sales A"}], "sk-x", "gpt-4o") == {"Sales A": "Income", "Rent": "Expense"}
