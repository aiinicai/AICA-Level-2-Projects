"""Per-run cost tracking: token accounting, pricing, env override, context scope."""

from services import cost


def test_known_model_priced():
    t = cost.CostTracker()
    t.add("anthropic/claude-opus-4.8", 1_000_000, 1_000_000)  # $5 in + $25 out
    s = t.summary()
    assert s["cost_usd"] == 30.0
    assert s["calls"] == 1
    assert s["estimated_prices"] is False


def test_unknown_model_flagged():
    t = cost.CostTracker()
    t.add("some/mystery-model", 1_000_000, 0)
    s = t.summary()
    assert s["estimated_prices"] is True
    assert "mystery-model" in s["unpriced_models"]


def test_env_price_override(monkeypatch):
    monkeypatch.setenv("AI_PRICE_GPT_4O_MINI", "1.0/2.0")
    t = cost.CostTracker()
    t.add("openai/gpt-4o-mini", 1_000_000, 1_000_000)
    assert t.summary()["cost_usd"] == 3.0


def test_by_model_breakdown():
    t = cost.CostTracker()
    t.add("openai/gpt-4o-mini", 1000, 500)
    t.add("openai/gpt-4o-mini", 1000, 500)
    t.add("anthropic/claude-3.5-haiku", 2000, 0)
    s = t.summary()
    assert s["by_model"]["gpt-4o-mini"]["calls"] == 2
    assert s["by_model"]["gpt-4o-mini"]["input_tokens"] == 2000


def test_context_scope_records_via_record():
    with cost.track() as t:
        cost.record("openai/gpt-4o", 1_000_000, 0)   # $2.50
    assert t.summary()["cost_usd"] == 2.5


def test_record_outside_scope_is_noop():
    # no active tracker -> must not raise
    cost.record("openai/gpt-4o", 100, 100)
