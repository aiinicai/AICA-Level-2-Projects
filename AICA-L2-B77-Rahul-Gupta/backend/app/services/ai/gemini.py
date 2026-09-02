"""Google Gemini provider (REST via httpx). Default model: Gemini 3.6 Flash.

Structured output is requested with response_mime_type=application/json and a
low temperature for extraction/verification tasks."""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import httpx

from ... import prompts
from .provider import AIProvider, AIProviderError

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiProvider(AIProvider):
    name = "Google Gemini"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, temperature: float = 0.2):
        self._api_key = api_key
        self.model = model
        self.temperature = temperature

    # -- low-level -----------------------------------------------------------
    def _generate(self, parts: list[dict], system: str, temperature: float | None = None,
                  json_output: bool = True, timeout: float = 60.0) -> str:
        url = f"{API_BASE}/models/{self.model}:generateContent"
        body: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": self.temperature if temperature is None else temperature,
            },
        }
        if json_output:
            body["generationConfig"]["response_mime_type"] = "application/json"
        try:
            # Credential goes in a header, never the URL: httpx logs full request
            # URLs at INFO, and httpx errors embed the URL in their message — either
            # would write the plaintext key to logs and to AICallLog.error.
            resp = httpx.post(url, headers={"x-goog-api-key": self._api_key},
                              json=body, timeout=timeout)
        except httpx.HTTPError as e:
            raise AIProviderError(f"Gemini connection failed: {e}") from e
        if resp.status_code == 429:
            raise AIProviderError("Gemini rate limit reached — please retry shortly")
        if resp.status_code >= 400:
            raise AIProviderError(f"Gemini error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise AIProviderError(f"Malformed Gemini response: {json.dumps(data)[:300]}") from e

    def _generate_json(self, parts: list[dict], system: str, list_key: str | None = None,
                       **kw) -> dict[str, Any]:
        """Return a dict, or raise AIProviderError — never another exception type.

        Callers treat this as a mapping and immediately call .get(). A model is free
        to answer with a bare array, a string or null, and any of those used to escape
        as an AttributeError/TypeError that killed the whole document pipeline. Every
        malformed shape now becomes AIProviderError, which callers already handle as
        "AI unavailable" and degrade past. ``list_key`` names the field to wrap a
        top-level array into, for tasks whose natural answer *is* a list.
        """
        text = self._generate(parts, system, **kw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # tolerate fenced JSON
            cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as e:
                raise AIProviderError(f"Gemini returned non-JSON output: {text[:200]}") from e

        if isinstance(data, dict):
            return data
        if list_key and isinstance(data, list):
            return {list_key: data}
        raise AIProviderError(
            f"Gemini returned a JSON {type(data).__name__} where an object was expected"
        )

    # -- interface -----------------------------------------------------------
    def test_connection(self) -> bool:
        out = self._generate([{"text": "Reply with the JSON {\"ok\": true}"}],
                             "You reply with strict JSON only.", timeout=20.0)
        return "ok" in out

    def verify_document(self, image_path: str, page: int, statement_type: str,
                        unit_name: str, unit_multiplier: float,
                        periods: list[str], items: list[dict]) -> dict[str, Any]:
        img_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
        user_text = prompts.VERIFY_DOCUMENT_USER.format(
            page=page, statement_type=statement_type,
            unit_name=unit_name or "absolute INR", unit_multiplier=unit_multiplier,
            periods=", ".join(periods) or "unknown",
            items_json=json.dumps(items, indent=1),
        )
        parts = [
            {"inline_data": {"mime_type": "image/png", "data": img_b64}},
            {"text": user_text},
        ]
        # the natural answer here is a list of checked items, and the model sometimes
        # returns that array bare instead of under an "items" key
        return self._generate_json(parts, prompts.VERIFY_DOCUMENT_SYSTEM, list_key="items",
                                   temperature=0.1, timeout=120.0)

    def generate_question(self, context: dict[str, Any]) -> dict[str, Any]:
        parts = [{"text": "Context:\n" + json.dumps(context, indent=1, default=str)
                  + "\n\nDraft the single next-best question as strict JSON with keys: "
                    "question_id, category, priority, reason, trigger_rule, question, "
                    "type, options (list), valuation_impact (list)."}]
        return self._generate_json(parts, prompts.GENERATE_QUESTION_SYSTEM, temperature=0.4)

    def interpret_answer(self, question: str, answer: str, context: dict[str, Any]) -> dict[str, Any]:
        parts = [{"text": json.dumps({"question": question, "answer": answer,
                                      "context": context}, indent=1, default=str)}]
        return self._generate_json(parts, prompts.INTERPRET_ANSWER_SYSTEM, temperature=0.2)

    def generate_insights(self, payload: dict[str, Any]) -> dict[str, Any]:
        parts = [{"text": "Data package:\n" + json.dumps(payload, indent=1, default=str)
                  + "\n\nReturn JSON: {\"key_insights\": [{\"title\",\"body\"}...], "
                    "\"business_quality\": {\"grade\": \"A\"-\"D\", \"summary\"}, "
                    "\"earnings_quality\": \"<paragraph>\", "
                    "\"strengths\": [\"...\"], \"next_actions\": [\"...\"]}"}]
        return self._generate_json(parts, prompts.INSIGHTS_SYSTEM, temperature=0.4, timeout=90.0)

    def generate_report_sections(self, payload: dict[str, Any], sections: list[str]) -> dict[str, Any]:
        parts = [{"text": "Authoritative data package:\n"
                  + json.dumps(payload, indent=1, default=str)
                  + "\n\nWrite these sections as JSON keys with HTML content: "
                  + ", ".join(sections)}]
        return self._generate_json(parts, prompts.REPORT_SYSTEM, temperature=0.5, timeout=180.0)
