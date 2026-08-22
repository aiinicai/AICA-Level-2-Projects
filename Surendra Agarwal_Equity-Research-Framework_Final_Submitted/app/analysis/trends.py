"""Change-detection engine — Module 3.

Two granularities are supported, matching the two things the spec asks
for:

1. Period-over-period: `compute_period_over_period()` - previous value,
   current value, absolute/percentage change, direction, significance,
   for exactly one step (e.g. FY2025 -> FY2026).

2. Multi-period trajectory: `compute_multi_period_trend()` - classifies
   the trajectory across an entire series (IMPROVING / STABLE /
   DETERIORATING / MIXED / INSUFFICIENT_DATA), using a strict,
   deterministic rule (see _classify_direction) rather than a fuzzy
   "mostly up" heuristic - a single significant reversal within an
   otherwise-improving series is correctly reported as MIXED, not
   smoothed over. This is a deliberate choice: silently classifying a
   series with one bad year as cleanly "improving" would hide something
   an analyst should see and investigate themselves.

Neither function infers or states a cause for any change. The
`explanation` and `evidence_ids` parameters are optional and must be
supplied explicitly by the caller (typically only when Layer 2 document
evidence actually supports a causal statement) - per Principle 4/Module
3's own instruction: "Do not infer causation unless evidence exists."
"""

from __future__ import annotations

from app.core.enums import ConfidenceLevel, TrendDirection
from app.core.models import MetricResult, TrendResult

# Percentage-change legs within this threshold (in either direction) are
# treated as "flat" / noise rather than a genuine up or down move, for
# the purposes of multi-period trajectory classification.
_DEFAULT_FLAT_THRESHOLD = 0.03

# Overall percentage-change magnitude thresholds for `significance`.
_HIGH_SIGNIFICANCE_THRESHOLD = 0.20
_MEDIUM_SIGNIFICANCE_THRESHOLD = 0.05


def _pct_change(prev: float, curr: float) -> float | None:
    if prev == 0:
        return None  # undefined, not infinity — caller must handle explicitly
    return (curr - prev) / abs(prev)


def _significance_from_pct_change(pct_change: float | None) -> ConfidenceLevel:
    if pct_change is None:
        return ConfidenceLevel.UNAVAILABLE
    magnitude = abs(pct_change)
    if magnitude >= _HIGH_SIGNIFICANCE_THRESHOLD:
        return ConfidenceLevel.HIGH
    if magnitude >= _MEDIUM_SIGNIFICANCE_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def compute_period_over_period(
    metric_name: str,
    period_prior: str,
    value_prior: float | None,
    period_current: str,
    value_current: float | None,
    *,
    higher_is_better: bool = True,
    explanation: str | None = None,
    evidence_ids: list[str] | None = None,
) -> TrendResult:
    """Single-step change between two consecutive periods."""
    if value_prior is None or value_current is None:
        return TrendResult(
            metric_name=metric_name, periods=[period_prior, period_current],
            values=[value_prior, value_current], direction=TrendDirection.INSUFFICIENT_DATA,
            significance=ConfidenceLevel.UNAVAILABLE,
        )

    absolute_change = value_current - value_prior
    pct_change = _pct_change(value_prior, value_current)

    if pct_change is None:
        direction = TrendDirection.INSUFFICIENT_DATA
    elif abs(pct_change) < _DEFAULT_FLAT_THRESHOLD:
        direction = TrendDirection.STABLE
    elif (pct_change > 0) == higher_is_better:
        direction = TrendDirection.IMPROVING
    else:
        direction = TrendDirection.DETERIORATING

    return TrendResult(
        metric_name=metric_name, periods=[period_prior, period_current],
        values=[value_prior, value_current], absolute_change=round(absolute_change, 4),
        percentage_change=round(pct_change, 4) if pct_change is not None else None,
        direction=direction, significance=_significance_from_pct_change(pct_change),
        potential_explanation=explanation if evidence_ids else None,
        evidence_ids=evidence_ids or [],
    )


def _classify_direction(
    values: list[float | None], *, higher_is_better: bool, flat_threshold: float
) -> TrendDirection:
    """Strict leg-by-leg classification — see module docstring for why
    this does not use a "mostly up" majority rule."""
    valid_points = [v for v in values if v is not None]
    if len(valid_points) < 2:
        return TrendDirection.INSUFFICIENT_DATA

    # Build consecutive valid-to-valid legs (skips a None by bridging
    # across it, rather than breaking the whole series on one gap).
    legs: list[float] = []
    prev = None
    for v in values:
        if v is None:
            continue
        if prev is not None:
            pct = _pct_change(prev, v)
            if pct is not None:
                legs.append(pct)
        prev = v

    if not legs:
        return TrendDirection.INSUFFICIENT_DATA

    signed_legs = [
        1 if pct >= flat_threshold else (-1 if pct <= -flat_threshold else 0)
        for pct in legs
    ]
    non_flat = [s for s in signed_legs if s != 0]

    if not non_flat:
        return TrendDirection.STABLE
    if all(s == 1 for s in non_flat):
        return TrendDirection.IMPROVING if higher_is_better else TrendDirection.DETERIORATING
    if all(s == -1 for s in non_flat):
        return TrendDirection.DETERIORATING if higher_is_better else TrendDirection.IMPROVING
    return TrendDirection.MIXED


def compute_multi_period_trend(
    metric_name: str,
    periods: list[str],
    values: list[float | None],
    *,
    higher_is_better: bool = True,
    flat_threshold: float = _DEFAULT_FLAT_THRESHOLD,
    explanation: str | None = None,
    evidence_ids: list[str] | None = None,
) -> TrendResult:
    """Classify the trajectory across an entire chronologically-ordered
    series (periods[0]/values[0] = earliest).

    `higher_is_better` controls how a rising value is interpreted:
    True for metrics like Revenue/EBITDA/ROE (up = IMPROVING), False for
    metrics like Debt/Equity (up = DETERIORATING).
    """
    if len(periods) != len(values):
        raise ValueError(
            f"periods ({len(periods)}) and values ({len(values)}) must be the same length."
        )

    direction = _classify_direction(values, higher_is_better=higher_is_better, flat_threshold=flat_threshold)

    valid_indexed = [(p, v) for p, v in zip(periods, values) if v is not None]
    absolute_change = None
    pct_change = None
    if len(valid_indexed) >= 2:
        first_val, last_val = valid_indexed[0][1], valid_indexed[-1][1]
        absolute_change = round(last_val - first_val, 4)
        raw_pct = _pct_change(first_val, last_val)
        pct_change = round(raw_pct, 4) if raw_pct is not None else None

    return TrendResult(
        metric_name=metric_name, periods=periods, values=values,
        absolute_change=absolute_change, percentage_change=pct_change,
        direction=direction, significance=_significance_from_pct_change(pct_change),
        potential_explanation=explanation if evidence_ids else None,
        evidence_ids=evidence_ids or [],
    )


def compute_multi_period_trend_from_metric_results(
    metric_results: list[MetricResult], *, higher_is_better: bool = True, flat_threshold: float = _DEFAULT_FLAT_THRESHOLD,
) -> TrendResult:
    """Convenience wrapper: build a multi-period trend directly from a
    chronologically-ordered list of MetricResult (e.g. one fundamentals.py
    metric computed across every period in a statement series).

    Non-OK results contribute a None at that period (never a fabricated
    value), consistent with how compute_multi_period_trend bridges gaps.
    """
    if not metric_results:
        raise ValueError("metric_results must not be empty.")
    periods = [m.period for m in metric_results]
    values = [m.value if m.status.value == "ok" else None for m in metric_results]
    metric_name = metric_results[0].metric_name
    return compute_multi_period_trend(
        metric_name, periods, values, higher_is_better=higher_is_better, flat_threshold=flat_threshold,
    )
