"""Provider routing for the LLM client seam (OpenAI vs Anthropic by model name)."""

import json
import sys
import types

import pytest

from services.llm_client import (
    ANTHROPIC,
    OPENAI,
    OPENROUTER,
    _extract_json,
    complete,
    provider_for_model,
)


@pytest.mark.parametrize("raw,expected_key", [
    ('{"criteria": [1]}', "criteria"),                       # already clean
    ('```json\n{"criteria": [1]}\n```', "criteria"),         # fenced (Claude/Gemini)
    ('```\n{"criteria": [1]}\n```', "criteria"),             # bare fence
    ('Here is the JSON:\n{"criteria": [1]}\nDone.', "criteria"),  # prose-wrapped
])
def test_extract_json_unwraps_fences_and_prose(raw, expected_key):
    assert expected_key in json.loads(_extract_json(raw))


@pytest.mark.parametrize("model,expected", [
    ("gpt-4o-mini", OPENAI),
    ("o1-preview", OPENAI),
    ("openai:gpt-4o", OPENAI),
    ("claude-haiku-4-5-20251001", ANTHROPIC),
    ("claude-opus-4-8", ANTHROPIC),
    ("anthropic:claude-sonnet-4-6", ANTHROPIC),
    ("openrouter:anthropic/claude-3.5-sonnet", OPENROUTER),
    ("anthropic/claude-3.5-haiku", OPENROUTER),   # bare vendor/model
    ("openai/gpt-4o-mini", OPENROUTER),
    ("some-unknown-model", OPENAI),  # safe default
])
def test_provider_for_model(model, expected):
    assert provider_for_model(model) == expected


def test_openrouter_path_uses_base_url_and_key(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            msg = types.SimpleNamespace(content='{"ok": true}')
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class FakeClient:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.OpenAI", FakeClient)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)

    out = complete("anthropic/claude-3.5-haiku", "sys", "user")
    assert out == '{"ok": true}'
    assert captured["init"]["api_key"] == "sk-or-test"
    assert captured["init"]["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["model"] == "anthropic/claude-3.5-haiku"  # slash preserved


def test_openrouter_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        complete("openrouter:openai/gpt-4o-mini", "sys", "user")


def test_openai_path_calls_openai(monkeypatch):
    captured = {}

    def fake_openai(model, system_prompt, user_prompt, temperature, api_key, json_mode):
        captured["model"] = model
        return '{"ok": true}'

    monkeypatch.setattr("services.llm_client._complete_openai", fake_openai)
    out = complete("openai:gpt-4o", "sys", "user")
    assert out == '{"ok": true}'
    assert captured["model"] == "gpt-4o"  # prefix stripped


def test_anthropic_path_prefixes_and_parses(monkeypatch):
    """Simulate the Anthropic SDK: assert prefill is re-attached into valid JSON."""
    sent = {}

    class FakeBlock:
        type = "text"
        text = '"id": "C1", "status": "PASS"}'  # continues the prefilled "{"

    class FakeMessages:
        def create(self, **kwargs):
            sent.update(kwargs)
            return types.SimpleNamespace(content=[FakeBlock()])

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    fake_mod = types.SimpleNamespace(Anthropic=FakeClient)
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    out = complete("claude-haiku-4-5-20251001", "sys", "user", json_mode=True)
    assert out == '{"id": "C1", "status": "PASS"}'
    # prefill assistant message was injected
    assert sent["messages"][-1] == {"role": "assistant", "content": "{"}
    assert sent["system"] == "sys"


def test_anthropic_missing_sdk_raises(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)  # force ImportError
    with pytest.raises(RuntimeError, match="Anthropic SDK"):
        complete("claude-opus-4-8", "sys", "user")
