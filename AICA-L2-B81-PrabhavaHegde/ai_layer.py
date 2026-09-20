"""
AI drafting layer.

Design rule, and the one worth defending on camera: the AI never decides
compliance status and never sees client data. The deterministic engine decides
Present, Partial or Absent. The AI only rewrites the catalogue's fallback text
into engagement-specific prose.

What crosses the network for each finding:

    {"control": "R6.3", "title": "...", "status": "Absent", "weight": 5}

What never crosses: client name, entity details, evidence file contents, assessor
notes, management responses. A DPDP tool that leaks personal data to an LLM has
failed its own assessment.

Gemini is the provider because this is a compliance spend rather than a revenue
tool, and per-assessment cost has to stay near zero. It is called over its REST
API with the standard library alone, so the packaged exe needs no AI SDK and a
machine with no key, no network or a wrong key simply runs offline.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol

# --------------------------------------------------------------------------
# Prompts. These are the files submitted as 02_Prompts. Keep them here so the
# shipped exe and the submitted prompt file can never drift apart.
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You are drafting findings for a DPDP readiness assessment report \
prepared by a Chartered Accountant in India, under the Digital Personal Data \
Protection Act, 2023 and the DPDP Rules, 2025.

Rules you must follow:
1. Never state or imply that the entity is "compliant" or "non-compliant". The \
report records observations against stated criteria on the evidence provided.
2. Never invent facts. You are given only a control reference, its title and an \
assessed status. You have no access to the entity's records.
3. Write in plain professional English. No legal advice, no penalty predictions \
beyond the statutory amounts, no rhetorical questions.
4. Each finding has exactly three fields: observation, impact, action.
   - observation: what was found, stated factually in one or two sentences.
   - impact: why it matters to this entity, referring to the obligation breached.
   - action: what should be done, specific and sequenced.
5. Return ONLY a JSON array. No markdown fences, no preamble, no trailing text."""

USER_TEMPLATE = """Draft findings for the following assessed controls.

{findings_json}

Return a JSON array. One object per control, in the same order, each with keys:
"control", "observation", "impact", "action"."""

# Kept deliberately: this is the prompt version that failed, retained in the
# submission to show the iteration. It omitted rule 1 and rule 5, and the model
# returned markdown-fenced prose containing the phrase "the entity is
# non-compliant", which is an assurance statement a CA cannot make.
FAILED_PROMPT_V1 = """You are a DPDP compliance expert. Review these controls and \
explain what is wrong and how to fix it."""


@dataclass
class Finding:
    """One assessed control, reduced to what the AI is allowed to see."""
    control: str
    title: str
    status: str
    weight: int

    def to_payload(self) -> dict:
        return {"control": self.control, "title": self.title,
                "status": self.status, "weight": self.weight}


class Provider(Protocol):
    name: str
    def draft(self, findings: list[Finding]) -> list[dict]: ...


# --------------------------------------------------------------------------
# Providers. Each returns a list of dicts with control/observation/impact/action.
# Imports are inside the methods so a missing SDK never blocks startup - the exe
# must run on a machine with no AI library installed at all.
# --------------------------------------------------------------------------

class GeminiProvider:
    name = "gemini"
    default_model = "gemini-2.5-flash"
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    timeout_seconds = 60

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key, self.model = api_key, model or self.default_model

    def draft(self, findings: list[Finding]) -> list[dict]:
        body = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [
                {"text": USER_TEMPLATE.format(findings_json=_payload(findings))}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
        }
        req = urllib.request.Request(
            self.endpoint.format(model=self.model),
            data=json.dumps(body).encode("utf-8"),
            # The key travels in a header, never in the URL, so it cannot land in a log.
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = data["candidates"][0]["content"]["parts"]
        return _parse("".join(part.get("text", "") for part in parts))


class OfflineProvider:
    """No network. Returns nothing, so the caller keeps the catalogue text.

    This is not a degraded mode to apologise for. A firm that has decided no
    client work may touch an external model runs the tool exactly this way, and
    the report is complete.
    """
    name = "offline"

    def draft(self, findings: list[Finding]) -> list[dict]:
        return []


PROVIDERS = {
    "gemini": GeminiProvider,
    "offline": OfflineProvider,
}


def get_provider(name: str | None = None, api_key: str | None = None,
                 model: str | None = None) -> Provider:
    """Build the configured provider, falling back to offline on any problem.

    Resolution order: explicit argument, then config, then environment, then offline.
    The tool must never fail to produce a report because an API key is wrong.
    """
    name = (name or os.getenv("DPDP_AI_PROVIDER") or "offline").lower()
    if name not in PROVIDERS:
        return OfflineProvider()
    if name == "offline":
        return OfflineProvider()

    key = api_key or os.getenv(f"{name.upper()}_API_KEY") or os.getenv("DPDP_AI_KEY")
    if not key:
        return OfflineProvider()

    try:
        return PROVIDERS[name](key, model)
    except Exception:
        return OfflineProvider()


def draft_findings(provider: Provider, findings: list[Finding]) -> dict[str, dict]:
    """Return control_id -> {observation, impact, action}, or {} on any failure.

    Failure is silent by design. The caller already holds the catalogue text and
    the report must be produced either way.
    """
    if not findings:
        return {}
    try:
        rows = provider.draft(findings)
    except Exception:
        return {}

    out: dict[str, dict] = {}
    for row in rows:
        cid = row.get("control")
        if cid and all(k in row for k in ("observation", "impact", "action")):
            out[cid] = {k: str(row[k]).strip() for k in ("observation", "impact", "action")}
    return out


def _payload(findings: list[Finding]) -> str:
    return json.dumps([f.to_payload() for f in findings], indent=2)


def _parse(text: str) -> list[dict]:
    """Parse the model response, tolerating markdown fences and an object wrapper."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.lstrip().startswith("json") else text
    data = json.loads(text.strip())
    if isinstance(data, dict):
        data = data.get("findings") or data.get("results") or []
    return data if isinstance(data, list) else []


if __name__ == "__main__":
    # Self-check: what would be sent, and that offline resolves without a key.
    sample = [Finding("R6.1", "Encryption of personal data at rest", "Absent", 5)]
    print("Payload sent to the model (the whole of it):")
    print(_payload(sample))
    assert set(sample[0].to_payload()) == {"control", "title", "status", "weight"}
    assert get_provider("offline").name == "offline"
    assert get_provider("nonsense").name == "offline"
    assert draft_findings(OfflineProvider(), sample) == {}
    assert _parse('```json\n[{"control": "R6.1"}]\n```') == [{"control": "R6.1"}]
    print("\nConfigured provider:", get_provider(os.getenv("DPDP_AI_PROVIDER", "gemini")).name)
    print("ai_layer self-check: ok")
