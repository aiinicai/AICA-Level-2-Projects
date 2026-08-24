"""Per-token pricing table for cost ESTIMATION - not for billing.

This is a dashboard convenience, not an authoritative source. Every
number here was verified via web search on the date below; AI provider
pricing (and even model names) changes fast enough that this project
has already been bitten by it multiple times (see docs/TESTING_NOTES.md
- the Gemini model-retirement finding is the clearest example). Always
confirm actual billed amounts against your provider's own usage
dashboard: platform.openai.com/account/usage for OpenAI,
aistudio.google.com/usage for Gemini.

PRICING_LAST_VERIFIED - re-check both providers' current pricing pages
if this gets more than a couple of months stale:
  https://platform.openai.com/docs/pricing
  https://ai.google.dev/gemini-api/docs/pricing
"""

from __future__ import annotations

PRICING_LAST_VERIFIED = "2026-08-14"

# model_name -> (input_usd_per_1m_tokens, output_usd_per_1m_tokens)
# Covers this project's configured defaults (gpt-4o, gemini-3.5-flash-lite)
# plus common alternatives a user might switch OPENAI_MODEL/GEMINI_MODEL to.
_PRICING_PER_1M_TOKENS: dict[str, tuple[float, float]] = {
    # --- OpenAI ---
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5": (1.25, 10.00),
    # --- Gemini ---
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.6-flash": (1.50, 7.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro": (2.00, 12.00),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
}


def estimate_cost_usd(
    model: str | None, prompt_tokens: int | None, completion_tokens: int | None,
) -> float | None:
    """Rough cost estimate in USD for one LLM call.

    Returns None - never a fabricated 0 - if the model isn't in the
    pricing table above (e.g. a model released after this table was
    last updated) or either token count is unavailable. A caller
    displaying this should show "N/A" or omit the call from a running
    total rather than silently treating None as zero cost.
    """
    if model is None or prompt_tokens is None or completion_tokens is None:
        return None
    if model not in _PRICING_PER_1M_TOKENS:
        return None
    input_rate, output_rate = _PRICING_PER_1M_TOKENS[model]
    return (prompt_tokens / 1_000_000) * input_rate + (completion_tokens / 1_000_000) * output_rate


def is_known_model(model: str | None) -> bool:
    """Whether `model` has a pricing entry - useful for a caller to
    show "pricing not available for this model" rather than silently
    omitting it from a total with no explanation."""
    return model in _PRICING_PER_1M_TOKENS
