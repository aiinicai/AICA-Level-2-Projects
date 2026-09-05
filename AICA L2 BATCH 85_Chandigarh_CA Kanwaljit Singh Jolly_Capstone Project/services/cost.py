"""
Per-run LLM cost tracking.

Token counts are EXACT (read from each provider's usage response). Prices are
editable estimates (USD per 1M tokens, June 2026) — override any of them with
env vars like AI_PRICE_GPT_4O_MINI="0.15/0.60" if your rates differ.

Usage is recorded via a context-local tracker so nothing in the LLM seams or the
validators needs new arguments: the pipeline opens `with cost.track() as t:` around
the generic path and every nested call (derivation, validator, jurors, tool loop)
records into `t` automatically. In tests the LLM calls are stubbed, so no usage is
recorded and the cost is simply 0.0.
"""

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Optional, Tuple

# USD per 1,000,000 tokens, (input, output). Estimates — edit or override via env.
# Embedding models are input-only (output price 0).
_PRICES: Dict[str, Tuple[float, float]] = {
    "gpt-5.5": (3.0, 15.0),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "o1": (15.0, 60.0),
    "claude-fable-5": (15.0, 75.0),
    "claude-opus-4.8": (5.0, 25.0),
    "claude-opus-4": (5.0, 25.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-3.5-sonnet": (3.0, 15.0),
    "claude-3.5-haiku": (0.80, 4.0),
    "claude-haiku-4": (1.0, 5.0),
    "gemini-3.1-pro": (2.0, 12.0),
    "gemini-flash": (0.15, 0.60),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
}

_DEFAULT_PRICE = (1.0, 5.0)  # used when a model isn't in the table (flagged in output)


def _normalize(model: str) -> str:
    m = (model or "").strip().lower()
    for p in ("openai:", "anthropic:", "openrouter:"):
        if m.startswith(p):
            m = m[len(p):]
    if "/" in m:  # openrouter vendor/model
        m = m.split("/", 1)[1]
    return m


def _price_for(model: str) -> Tuple[Tuple[float, float], bool]:
    """Return ((in, out) per 1M, known?). Longest-key substring match; env override wins."""
    norm = _normalize(model)
    env = os.getenv("AI_PRICE_" + norm.upper().replace("-", "_").replace(".", "_"))
    if env and "/" in env:
        try:
            i, o = env.split("/", 1)
            return (float(i), float(o)), True
        except ValueError:
            pass
    best = None
    for key, price in _PRICES.items():
        if key in norm and (best is None or len(key) > len(best[0])):
            best = (key, price)
    if best:
        return best[1], True
    return _DEFAULT_PRICE, False


class CostTracker:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0
        self.cost_usd = 0.0
        self.by_model: Dict[str, Dict[str, float]] = {}
        self.unpriced_models: set = set()

    def add(self, model: str, input_tokens: int, output_tokens: int) -> None:
        input_tokens = int(input_tokens or 0)
        output_tokens = int(output_tokens or 0)
        (pin, pout), known = _price_for(model)
        cost = input_tokens / 1e6 * pin + output_tokens / 1e6 * pout
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.calls += 1
        self.cost_usd += cost
        if not known:
            self.unpriced_models.add(_normalize(model))
        m = self.by_model.setdefault(_normalize(model),
                                     {"input_tokens": 0, "output_tokens": 0, "calls": 0, "cost_usd": 0.0})
        m["input_tokens"] += input_tokens
        m["output_tokens"] += output_tokens
        m["calls"] += 1
        m["cost_usd"] += cost

    def summary(self) -> Dict[str, object]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "calls": self.calls,
            "cost_usd": round(self.cost_usd, 4),
            "by_model": {k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in self.by_model.items()},
            "estimated_prices": bool(self.unpriced_models),
            "unpriced_models": sorted(self.unpriced_models),
        }


_current: ContextVar[Optional[CostTracker]] = ContextVar("cost_tracker", default=None)


@contextmanager
def track():
    """Open a cost-tracking scope; all nested LLM calls record into the yielded tracker."""
    tracker = CostTracker()
    token = _current.set(tracker)
    try:
        yield tracker
    finally:
        _current.reset(token)


def record(model: str, input_tokens: int, output_tokens: int) -> None:
    """Record one call's usage into the active tracker (no-op if none is active)."""
    tracker = _current.get()
    if tracker is not None:
        tracker.add(model, input_tokens, output_tokens)
