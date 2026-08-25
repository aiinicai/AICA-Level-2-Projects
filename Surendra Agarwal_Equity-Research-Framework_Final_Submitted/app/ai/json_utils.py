"""Shared helper for parsing strict-JSON LLM responses.

Used by both document_analysis.py and thesis_generator.py — factored
out rather than one importing a private function from the other.
"""

from __future__ import annotations

import json
import re

from app.core.exceptions import LLMProviderError

_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) some models wrap
    JSON output in despite instructions not to."""
    return _FENCE_PATTERN.sub("", text).strip()


def parse_json_response(text: str) -> dict:
    """Parse an LLM response as strict JSON, tolerating markdown fences.

    Raises:
        LLMProviderError: if the cleaned text still isn't valid JSON —
            this is treated as a provider-layer failure (the model
            didn't follow the output contract), not silently ignored.
    """
    cleaned = strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMProviderError(
            f"LLM response was not valid JSON after fence-stripping: {exc}. "
            f"Raw response (truncated): {text[:200]!r}"
        ) from exc
