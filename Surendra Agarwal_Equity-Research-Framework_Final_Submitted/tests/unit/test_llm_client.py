"""Tests for app/ai/llm_client.py. No live API calls anywhere in this file."""

from __future__ import annotations

import pytest

from app.core.exceptions import LLMProviderError
from app.ai.llm_client import FakeLLMClient, LLMClient, LLMResponse


class TestFakeLLMClient:
    def test_fixed_response_returned_every_call(self):
        client = FakeLLMClient(fixed_response="hello")
        r1 = client.complete(system="s", user="u1")
        r2 = client.complete(system="s", user="u2")
        assert r1.text == "hello"
        assert r2.text == "hello"

    def test_scripted_responses_returned_in_order(self):
        client = FakeLLMClient(responses=["first", "second"])
        assert client.complete(system="s", user="u").text == "first"
        assert client.complete(system="s", user="u").text == "second"

    def test_scripted_responses_exhausted_raises(self):
        client = FakeLLMClient(responses=["only one"])
        client.complete(system="s", user="u")
        with pytest.raises(LLMProviderError):
            client.complete(system="s", user="u")

    def test_calls_are_recorded(self):
        client = FakeLLMClient(fixed_response="x")
        client.complete(system="sys text", user="user text", max_tokens=500)
        assert len(client.calls) == 1
        assert client.calls[0]["system"] == "sys text"
        assert client.calls[0]["user"] == "user text"
        assert client.calls[0]["max_tokens"] == 500

    def test_requires_fixed_response_or_responses(self):
        with pytest.raises(ValueError):
            FakeLLMClient()

    def test_conforms_to_llm_client_interface(self):
        client = FakeLLMClient(fixed_response="x")
        assert isinstance(client, LLMClient)

    def test_returns_llm_response_type(self):
        client = FakeLLMClient(fixed_response="x")
        result = client.complete(system="s", user="u")
        assert isinstance(result, LLMResponse)
        assert result.model == "fake-model"
