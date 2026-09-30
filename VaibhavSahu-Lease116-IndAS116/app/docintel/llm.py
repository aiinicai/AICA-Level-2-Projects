"""LLM adapters for the agreement reader.

* LocalLLM  — Ollama (native API, JSON-schema output) or any OpenAI-compatible local server
              such as LM Studio. Runs on the user's PC; nothing leaves the machine.
* ClaudeLLM — Anthropic API (optional; only when the entity allows cloud AI and the user
              confirms for the specific document).

Both return, per field: {"value", "quote", "page", "confidence"}. Quotes are verified
against the document afterwards — an LLM answer is never trusted on its own.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from .schema import FIELDS, FIELD_MAP, GROUPS, llm_field_list

SYSTEM_PROMPT = (
    "You are a meticulous Indian chartered accountant specialising in Ind AS 116 (Leases). "
    "Extract lease-accounting inputs from the agreement text provided.\n"
    "Rules:\n"
    "1. Use ONLY information stated in the document. Never guess or assume.\n"
    "2. For every field you fill, copy a short VERBATIM quote (max 250 characters) from the document that supports the "
    "value and give its page number from the [[PAGE n]] markers.\n"
    "3. If a field is not stated, return value null and quote \"\".\n"
    "4. Dates as YYYY-MM-DD (Indian documents normally write DD/MM/YYYY). Amounts as plain numbers without commas or "
    "currency symbols (convert lakh/crore to the full number). Percentages as numbers (5 for 5%). Periods in months as "
    "integers (years x 12).\n"
    "5. Commencement date = date the lessee obtains the right to use the asset (licence/lease start or handover), not "
    "merely the signing date.\n"
    "6. Rent amount = fixed rent / licence fee per payment period, excluding GST and maintenance/CAM charges.\n"
    "7. Confidence between 0 and 1 reflecting how explicitly the document states the value."
)


def _output_schema(keys: list[str]) -> dict:
    item = {"type": "object",
            "properties": {"value": {"type": ["string", "null"]}, "quote": {"type": "string"},
                           "page": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["value", "quote", "page", "confidence"]}
    return {"type": "object", "properties": {"fields": {"type": "object", "properties": {k: item for k in keys},
                                                        "required": keys}}, "required": ["fields"]}


def _user_prompt(keys: list[str], text: str) -> str:
    return (f"Fields to extract:\n{llm_field_list(keys)}\n\nAGREEMENT TEXT:\n{text}\n\n"
            'Return JSON of the form {"fields": {"<field>": {"value": "...", "quote": "...", "page": 1, "confidence": 0.9}}} '
            "with every listed field present. Values must be strings (or null).")


def _parse_json(content: str) -> dict:
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def select_context(pages: list[tuple[int, str]], keys: list[str], budget_chars: int) -> str:
    """Pick the most relevant paragraphs for the given fields (keyword retrieval) within a character budget."""
    full = "\n".join(f"[[PAGE {n}]]\n{t}" for n, t in pages)
    if len(full) <= budget_chars:
        return full
    kws = set()
    for k in keys:
        kws.update(w.lower() for w in FIELD_MAP[k].keywords)
    paras = []
    for n, t in pages:
        for para in re.split(r"\n\s*\n|(?=\n\s*\d+(?:\.\d+)*[\.\)]\s)", t):
            p = para.strip()
            if not p:
                continue
            low = p.lower()
            score = sum(low.count(k) for k in kws)
            if n == 1 or "hereinafter" in low:
                score += 1
            paras.append((score, n, p))
    chosen, used = [], 0
    for score, n, p in sorted(paras, key=lambda x: -x[0]):
        if score <= 0:
            break
        if used + len(p) + 20 > budget_chars:
            continue
        chosen.append((n, p))
        used += len(p) + 20
    chosen.sort(key=lambda x: x[0])
    out, last = [], None
    for n, p in chosen:
        if n != last:
            out.append(f"[[PAGE {n}]]")
            last = n
        out.append(p)
    return "\n".join(out)


@dataclass
class LocalLLM:
    base_url: str = "http://localhost:11434"
    kind: str = "ollama"              # ollama | openai
    model: str = ""
    vision_model: str = ""
    timeout: float = 600.0
    context_chars: int = 24000        # ~6k tokens of agreement text per call
    name: str = "local"
    last_error: str = ""

    @staticmethod
    def detect(timeout: float = 1.5) -> list[dict]:
        found = []
        try:
            r = httpx.get("http://localhost:11434/api/tags", timeout=timeout)
            if r.status_code == 200:
                models = [m.get("name") for m in r.json().get("models", [])]
                found.append({"kind": "ollama", "base_url": "http://localhost:11434", "models": models})
        except Exception:
            pass
        try:
            r = httpx.get("http://localhost:1234/v1/models", timeout=timeout)
            if r.status_code == 200:
                models = [m.get("id") for m in r.json().get("data", [])]
                found.append({"kind": "openai", "base_url": "http://localhost:1234", "models": models})
        except Exception:
            pass
        return found

    def available(self) -> bool:
        return bool(self.model)

    def chat_json(self, system: str, user: str, schema: dict) -> dict:
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if self.kind == "ollama":
            r = httpx.post(f"{self.base_url}/api/chat", json={
                "model": self.model, "messages": msgs, "stream": False, "format": schema,
                "options": {"temperature": 0, "num_ctx": 16384}}, timeout=self.timeout)
            r.raise_for_status()
            return _parse_json(r.json()["message"]["content"])
        body = {"model": self.model, "messages": msgs, "temperature": 0,
                "response_format": {"type": "json_schema", "json_schema": {"name": "lease_terms", "schema": schema}}}
        r = httpx.post(f"{self.base_url}/v1/chat/completions", json=body, timeout=self.timeout)
        if r.status_code >= 400:
            body["response_format"] = {"type": "json_object"}
            r = httpx.post(f"{self.base_url}/v1/chat/completions", json=body, timeout=self.timeout)
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])

    def extract(self, pages: list[tuple[int, str]], keys: list[str] | None = None) -> dict:
        keys = keys or [f.key for f in FIELDS]
        full_len = sum(len(t) for _, t in pages)
        results: dict = {}
        groups = [keys] if full_len <= self.context_chars else \
            [[k for k in keys if FIELD_MAP[k].group == g] for g in GROUPS]
        for gkeys in groups:
            if not gkeys:
                continue
            ctx = select_context(pages, gkeys, self.context_chars)
            data = self.chat_json(SYSTEM_PROMPT, _user_prompt(gkeys, ctx), _output_schema(gkeys))
            results.update((data or {}).get("fields", {}))
        return results

    def transcribe_image(self, b64png: str) -> str:
        if not self.vision_model:
            raise RuntimeError("No local vision model configured")
        r = httpx.post(f"{self.base_url}/api/chat", json={
            "model": self.vision_model, "stream": False, "options": {"temperature": 0},
            "messages": [{"role": "user", "content": "Transcribe all text on this page exactly, line by line. Output only the text.",
                          "images": [b64png]}]}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["message"]["content"]


@dataclass
class ClaudeLLM:
    api_key: str
    model: str = ""
    name: str = "claude"
    max_tokens: int = 8000

    def _client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self.api_key)

    def resolve_model(self) -> str:
        if self.model:
            return self.model
        try:
            models = [m.id for m in self._client().models.list(limit=50).data]
            for pref in ("sonnet", "opus", "haiku"):
                for m in models:
                    if pref in m:
                        self.model = m
                        return m
            if models:
                self.model = models[0]
                return self.model
        except Exception:
            pass
        self.model = "claude-sonnet-4-5"
        return self.model

    def available(self) -> bool:
        return bool(self.api_key)

    def extract(self, pages: list[tuple[int, str]], keys: list[str] | None = None) -> dict:
        keys = keys or [f.key for f in FIELDS]
        text = "\n".join(f"[[PAGE {n}]]\n{t}" for n, t in pages)
        schema = _output_schema(keys)
        client = self._client()
        msg = client.messages.create(
            model=self.resolve_model(), max_tokens=self.max_tokens, system=SYSTEM_PROMPT,
            tools=[{"name": "record_lease_terms", "description": "Record the extracted Ind AS 116 lease inputs with verbatim evidence.",
                    "input_schema": schema}],
            tool_choice={"type": "tool", "name": "record_lease_terms"},
            messages=[{"role": "user", "content": _user_prompt(keys, text)}])
        for block in msg.content:
            if getattr(block, "type", "") == "tool_use":
                return (block.input or {}).get("fields", {})
        return {}

    def transcribe_image(self, b64png: str) -> str:
        client = self._client()
        msg = client.messages.create(model=self.resolve_model(), max_tokens=4000, messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64png}},
            {"type": "text", "text": "Transcribe all text on this page exactly, line by line. Output only the text."}]}])
        return "".join(getattr(b, "text", "") for b in msg.content)
