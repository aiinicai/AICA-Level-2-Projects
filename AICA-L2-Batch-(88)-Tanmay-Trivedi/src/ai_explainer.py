"""
ai_explainer.py
-----------------
Optional plain-language rewording of a verdict already reached by the rule
engine (src/rules.py). The rule engine's own reasoning is already
human-readable on its own - this just offers a friendlier one-paragraph
version, and only runs if ANTHROPIC_API_KEY is set. No key -> the caller
just uses the rule-based reasoning text as-is; nothing about the verdict
itself ever depends on this module, and no transaction-level client data is
sent, only the (already-anonymous) expense description and the verdict.
"""

from __future__ import annotations

import os


def explain(description: str, category_title: str, clause: str, verdict: str, reasoning: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return reasoning + "\n\n[No ANTHROPIC_API_KEY set - showing the rule engine's own explanation.]"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "In 2-3 short sentences, explain this GST input tax credit verdict in plain English for a "
            "chartered accountant's working file. Do not change the verdict or invent new facts - just "
            "restate it clearly and naturally.\n\n"
            f"Expense description: {description}\n"
            f"Matched category: {category_title} (Section {clause}, CGST Act)\n"
            f"Verdict: {verdict}\n"
            f"Rule engine's reasoning: {reasoning}"
        )
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text")).strip()
        if text:
            return text + "\n\n[Plain-language rewording by Claude, from the verdict above - not an independent determination.]"
    except Exception:
        pass

    return reasoning + "\n\n[Live AI call unavailable - showing the rule engine's own explanation.]"
