"""
valuation/scoring.py

Two distinct scores:
 1. Valuation Confidence Score (0-100%) — how much evidence backs the analysis.
 2. Combined Property Investment Score (0-100) — weighted composite signal.

Both use application-defined, configurable weights (see config.py) and are
explicitly NOT a certified valuation confidence metric.
"""

import datetime as dt

from config import SCORE_WEIGHTS, SCORE_BANDS, DATA_FRESHNESS_DAYS_GOOD, DATA_FRESHNESS_DAYS_STALE


def score_label(score: float, bands=SCORE_BANDS) -> str:
    for lo, hi, label in bands:
        if lo <= score <= hi:
            return label
    return "Unclassified"


def _freshness_factor(dates: list) -> float:
    """1.0 if data is fresh (<90 days median age), tapering to 0.3 if stale (>365 days)."""
    if not dates:
        return 0.5
    today = dt.date.today()
    ages = []
    for d in dates:
        try:
            parsed = dt.date.fromisoformat(str(d)[:10])
            ages.append((today - parsed).days)
        except (ValueError, TypeError):
            continue
    if not ages:
        return 0.5
    ages.sort()
    median_age = ages[len(ages) // 2]
    if median_age <= DATA_FRESHNESS_DAYS_GOOD:
        return 1.0
    if median_age >= DATA_FRESHNESS_DAYS_STALE:
        return 0.3
    # linear taper between good and stale thresholds
    span = DATA_FRESHNESS_DAYS_STALE - DATA_FRESHNESS_DAYS_GOOD
    return 1.0 - 0.7 * ((median_age - DATA_FRESHNESS_DAYS_GOOD) / span)


def confidence_score(n_comparables: int, n_rental_obs: int, n_sources: int,
                      locality_match: bool, bhk_match: bool, tier: str,
                      collected_dates: list = None, any_sample_data: bool = False) -> float:
    """
    Returns a percentage 0-100. Purely additive/multiplicative heuristic,
    intentionally conservative when little evidence exists.
    """
    # Volume component: caps out once "enough" evidence exists.
    vol_score = min(n_comparables, 100) / 100 * 40 + min(n_rental_obs, 100) / 100 * 20
    # Source diversity component.
    source_score = min(n_sources, 4) / 4 * 15
    # Match quality component.
    match_score = (10 if locality_match else 3) + (10 if bhk_match else 3)
    # Tier penalty: comparisons that had to fall back to city-level lose points.
    tier_penalty = 0 if tier and tier.startswith("locality") else 10

    raw = vol_score + source_score + match_score - tier_penalty
    raw *= _freshness_factor(collected_dates or [])

    if any_sample_data:
        raw *= 0.5  # demo/sample data can never earn high confidence

    return max(0.0, min(100.0, round(raw, 1)))


def investment_score(price_vs_fair_value_pct: float, gross_yield: float,
                      price_to_rent: float, n_comparables: int,
                      local_demand_index: float = 50.0,
                      price_trend_pct: float = 0.0, rent_trend_pct: float = 0.0,
                      weights: dict = None) -> (float, str):
    """
    All sub-scores are normalized to 0-100 before weighting.
    price_vs_fair_value_pct: negative = underpriced (good), positive = overpriced (bad)
    """
    weights = weights or SCORE_WEIGHTS

    # Price vs fair value: 0% deviation -> 100, +/-30% deviation -> 0, asymmetric
    # (being overpriced hurts more than being underpriced helps, since
    # underpriced still carries execution risk).
    if price_vs_fair_value_pct <= 0:
        price_score = max(0, 100 - abs(price_vs_fair_value_pct) * 1.5)
    else:
        price_score = max(0, 100 - price_vs_fair_value_pct * 3.0)
    price_score = min(100, price_score)

    # Rental yield: 2% -> ~30, 4% -> ~70, 6%+ -> 100 (rough linear-ish mapping)
    yield_score = max(0, min(100, (gross_yield - 1.5) / (6.5 - 1.5) * 100))

    # Price-to-rent: lower is better. <15 yrs -> 100, >35 yrs -> 0
    if price_to_rent <= 0:
        ptr_score = 50
    else:
        ptr_score = max(0, min(100, (35 - price_to_rent) / (35 - 15) * 100))

    # Comparable evidence: more comparables -> higher confidence in the price signal
    evidence_score = min(100, n_comparables / 50 * 100)

    demand_score = max(0, min(100, local_demand_index))
    price_trend_score = max(0, min(100, 50 + price_trend_pct * 5))
    rent_trend_score = max(0, min(100, 50 + rent_trend_pct * 5))

    total = (
        price_score * weights["price_vs_fair_value"] +
        yield_score * weights["rental_yield"] +
        ptr_score * weights["price_to_rent"] +
        evidence_score * weights["comparable_evidence"] +
        demand_score * weights["local_demand"] +
        price_trend_score * weights["price_trend"] +
        rent_trend_score * weights["rent_trend"]
    )
    total = round(max(0.0, min(100.0, total)), 1)
    return total, score_label(total)
