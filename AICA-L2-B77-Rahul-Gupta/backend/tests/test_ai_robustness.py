"""AI responses must never break the core app.

A real document failed with "'list' object has no attribute 'get'": _generate_json
is annotated -> dict but returns json.loads(text), the model answered a
list-shaped request with a bare array, and pipeline.py then called .get() on it.
The AttributeError escaped the AIProviderError handling and killed the document,
discarding good Python extraction. Malformed AI output must degrade, not crash.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.ai.gemini import GeminiProvider
from app.services.ai.provider import AIProviderError


def _json_result(payload: str, **kw):
    with patch.object(GeminiProvider, "_generate", return_value=payload):
        return GeminiProvider(api_key="test-key")._generate_json([], "system", **kw)


def test_bare_array_is_recovered_for_list_shaped_tasks():
    """The exact payload that crashed the pipeline."""
    out = _json_result('[{"metric": "revenue"}]', list_key="items")
    assert out == {"items": [{"metric": "revenue"}]}


def test_objects_pass_through_unchanged():
    assert _json_result('{"items": [], "note": "x"}') == {"items": [], "note": "x"}


def test_fenced_json_is_still_tolerated():
    assert _json_result('```json\n{"ok": true}\n```') == {"ok": True}


@pytest.mark.parametrize("payload", ['"a string"', "null", "42", "true"])
def test_non_object_payloads_raise_the_handled_error_type(payload):
    """Callers catch AIProviderError; anything else escapes and fails the document."""
    with pytest.raises(AIProviderError):
        _json_result(payload)


def test_bare_array_without_a_list_key_is_still_not_a_crash():
    with pytest.raises(AIProviderError):
        _json_result("[1, 2, 3]")


def test_verify_document_asks_for_list_recovery():
    """verify_document's natural answer is an array, so it must opt into recovery."""
    seen = {}

    def fake(self, parts, system, list_key=None, **kw):
        seen["list_key"] = list_key
        return {"items": []}

    with patch.object(GeminiProvider, "_generate_json", fake), \
            patch("pathlib.Path.read_bytes", return_value=b"png"):
        GeminiProvider(api_key="k").verify_document(
            "img.png", 1, "balance_sheet", "lakh", 100000.0, ["FY2023-24"], [],
        )
    assert seen["list_key"] == "items"
