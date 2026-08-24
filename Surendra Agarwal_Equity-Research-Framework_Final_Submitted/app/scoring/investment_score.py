"""Investment scoring engine — Module 9 (AI-Assisted Investment Decision Score).

HONEST METHODOLOGY NOTE: the spec defines the six component weights
(Fundamentals 30%, Cash Flow Quality 15%, Business/Management 15%,
Valuation 20%, Technical 10%, Risk/Governance 10%) but does not define
how each component's underlying metrics translate into a 0-100 score.
That translation is this module's own explicit, documented rubric - a
judgment call, not an objective formula - and is written out in full in
each scorer function's docstring so it is auditable and adjustable,
per Principle 4 (no silent assumptions). A different, equally
defensible rubric could produce different component scores from the
same inputs; treat the resulting AI-IDS as one transparent, replicable
scoring convention, not an objectively "correct" number.

MISSING DATA POLICY (the spec's own explicit requirement): a component
with no usable input data is never scored as 0. It is marked
UNAVAILABLE, excluded from the overall score, and the remaining
components' weights are renormalized proportionally so they still sum
to 100% of whatever confidence-bearing weight is available. This is
implemented in `compute_investment_score()` and is the one piece of
aggregation logic every component scorer below depends on downstream.
"""

from __future__ import annotations

import logging

from app.core.enums import ConfidenceLevel, DataStatus, RiskSeverity
from app.core.models import (
    AIInterpretation,
    InvestmentScore,
    MetricResult,
    RiskItem,
    ScoreComponent,
)
from app.analysis.peers import PeerComparisonResult

logger = logging.getLogger(__name__)

_MAX_SCORE = 100.0


def _metric_by_name(metrics: list[MetricResult], name: str) -> MetricResult | None:
    for m in metrics:
        if m.metric_name == name and m.status == DataStatus.OK and m.value is not None:
            return m
    return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


# --------------------------------------------------------------------------
# Fundamentals (weight 30%)
# --------------------------------------------------------------------------


def score_fundamentals(metrics: list[MetricResult]) -> ScoreComponent:
    """Rubric (each present sub-metric contributes an equally-weighted
    0-100 sub-score; overall = average of available sub-scores):

    - Revenue CAGR (3yr): <0% -> 20, 0-5% -> 40, 5-10% -> 60, 10-15% -> 80, >=15% -> 100
    - EBITDA Margin: <10% -> 20, 10-15% -> 40, 15-20% -> 60, 20-25% -> 80, >=25% -> 100
    - ROE: <5% -> 20, 5-10% -> 40, 10-15% -> 60, 15-20% -> 80, >=20% -> 100
    - ROCE: same bands as ROE
    - Debt/Equity (lower is better): >1.5 -> 20, 1.0-1.5 -> 40, 0.5-1.0 -> 60, 0.25-0.5 -> 80, <0.25 -> 100

    Requires at least 2 of these 5 sub-metrics to be OK; otherwise UNAVAILABLE
    (a single data point isn't enough to call this a "fundamentals score").
    """
    sub_scores: list[float] = []
    evidence_ids: list[str] = []

    revenue_cagr = _metric_by_name(metrics, "Revenue CAGR (3yr)")
    if revenue_cagr:
        v = revenue_cagr.value
        sub_scores.append(100 if v >= 0.15 else 80 if v >= 0.10 else 60 if v >= 0.05 else 40 if v >= 0 else 20)
        evidence_ids.append(revenue_cagr.metric_id)

    ebitda_margin = _metric_by_name(metrics, "EBITDA Margin")
    if ebitda_margin:
        v = ebitda_margin.value
        sub_scores.append(100 if v >= 0.25 else 80 if v >= 0.20 else 60 if v >= 0.15 else 40 if v >= 0.10 else 20)
        evidence_ids.append(ebitda_margin.metric_id)

    roe = _metric_by_name(metrics, "ROE")
    if roe:
        v = roe.value
        sub_scores.append(100 if v >= 0.20 else 80 if v >= 0.15 else 60 if v >= 0.10 else 40 if v >= 0.05 else 20)
        evidence_ids.append(roe.metric_id)

    roce = _metric_by_name(metrics, "ROCE")
    if roce:
        v = roce.value
        sub_scores.append(100 if v >= 0.20 else 80 if v >= 0.15 else 60 if v >= 0.10 else 40 if v >= 0.05 else 20)
        evidence_ids.append(roce.metric_id)

    debt_equity = _metric_by_name(metrics, "Debt/Equity")
    if debt_equity:
        v = debt_equity.value
        sub_scores.append(100 if v < 0.25 else 80 if v < 0.5 else 60 if v < 1.0 else 40 if v < 1.5 else 20)
        evidence_ids.append(debt_equity.metric_id)

    if len(sub_scores) < 2:
        return ScoreComponent(
            name="Fundamentals", score=None, weight=0.0, status=DataStatus.UNAVAILABLE,
            confidence=ConfidenceLevel.UNAVAILABLE,
        )

    avg_score = sum(sub_scores) / len(sub_scores)
    confidence = ConfidenceLevel.HIGH if len(sub_scores) >= 4 else ConfidenceLevel.MEDIUM
    return ScoreComponent(
        name="Fundamentals", score=round(avg_score, 1), weight=0.0, status=DataStatus.OK,
        evidence_ids=evidence_ids, confidence=confidence,
    )


# --------------------------------------------------------------------------
# Cash Flow Quality (weight 15%)
# --------------------------------------------------------------------------


def score_cashflow_quality(metrics: list[MetricResult]) -> ScoreComponent:
    """Rubric:
    - CFO/PAT: <0.5 -> 20, 0.5-0.8 -> 50, 0.8-1.1 -> 90, 1.1-1.5 -> 100, >1.5 -> 70
      (very high CFO/PAT can indicate working-capital timing noise rather
      than pure quality, hence the taper above 1.5 rather than a monotonic
      increase)
    - FCF Conversion (FCF/EBITDA): <0 -> 20, 0-0.3 -> 50, 0.3-0.6 -> 80, >=0.6 -> 100

    Requires at least 1 of these 2 sub-metrics; average of whichever are available.
    """
    sub_scores: list[float] = []
    evidence_ids: list[str] = []

    cfo_pat = _metric_by_name(metrics, "CFO/PAT")
    if cfo_pat:
        v = cfo_pat.value
        sub_scores.append(
            70 if v > 1.5 else 100 if v >= 1.1 else 90 if v >= 0.8 else 50 if v >= 0.5 else 20
        )
        evidence_ids.append(cfo_pat.metric_id)

    fcf_conversion = _metric_by_name(metrics, "FCF Conversion")
    if fcf_conversion:
        v = fcf_conversion.value
        sub_scores.append(100 if v >= 0.6 else 80 if v >= 0.3 else 50 if v >= 0 else 20)
        evidence_ids.append(fcf_conversion.metric_id)

    if not sub_scores:
        return ScoreComponent(
            name="Cash Flow Quality", score=None, weight=0.0, status=DataStatus.UNAVAILABLE,
            confidence=ConfidenceLevel.UNAVAILABLE,
        )

    avg_score = sum(sub_scores) / len(sub_scores)
    confidence = ConfidenceLevel.HIGH if len(sub_scores) == 2 else ConfidenceLevel.MEDIUM
    return ScoreComponent(
        name="Cash Flow Quality", score=round(avg_score, 1), weight=0.0, status=DataStatus.OK,
        evidence_ids=evidence_ids, confidence=confidence,
    )


# --------------------------------------------------------------------------
# Business / Management (weight 15%)
# --------------------------------------------------------------------------


_CONFIDENCE_TO_SCORE = {
    ConfidenceLevel.HIGH: 85.0, ConfidenceLevel.MEDIUM: 60.0, ConfidenceLevel.LOW: 35.0,
}


def score_business_management(interpretations: list[AIInterpretation]) -> ScoreComponent:
    """Rubric: average of each AIInterpretation's confidence mapped to a
    score (HIGH=85, MEDIUM=60, LOW=35), i.e. this measures how
    well-supported the AI-extracted management/business commentary was,
    NOT a judgment of whether management is "good" - this module has no
    basis to make that call, only to reflect how much confidently-
    grounded qualitative evidence was found.

    Requires at least 3 interpretations for a MEDIUM+ confidence score
    (fewer than that is too thin a sample to summarize).
    """
    if not interpretations:
        return ScoreComponent(
            name="Business/Management", score=None, weight=0.0, status=DataStatus.UNAVAILABLE,
            confidence=ConfidenceLevel.UNAVAILABLE,
        )

    scores = [_CONFIDENCE_TO_SCORE[i.confidence] for i in interpretations if i.confidence in _CONFIDENCE_TO_SCORE]
    if not scores:
        return ScoreComponent(
            name="Business/Management", score=None, weight=0.0, status=DataStatus.UNAVAILABLE,
            confidence=ConfidenceLevel.UNAVAILABLE,
        )

    avg_score = sum(scores) / len(scores)
    confidence = ConfidenceLevel.MEDIUM if len(interpretations) >= 3 else ConfidenceLevel.LOW
    return ScoreComponent(
        name="Business/Management", score=round(avg_score, 1), weight=0.0, status=DataStatus.OK,
        evidence_ids=[i.interpretation_id for i in interpretations],
        confidence=confidence,
    )


# --------------------------------------------------------------------------
# Valuation (weight 20%)
# --------------------------------------------------------------------------


def score_valuation(peer_comparisons: list[PeerComparisonResult]) -> ScoreComponent:
    """Rubric, applied to each multiple's premium/discount vs. peer median
    and averaged (cheaper relative to peers scores higher - this is a
    valuation-attractiveness score, not a quality score):

    premium_discount_pct: <=-30% -> 100, -30% to -10% -> 80, -10% to +10% ->
    60, +10% to +40% -> 40, >+40% -> 20

    Requires at least 1 comparison with status=OK.
    """
    usable = [c for c in peer_comparisons if c.status == DataStatus.OK and c.premium_discount_pct is not None]
    if not usable:
        return ScoreComponent(
            name="Valuation", score=None, weight=0.0, status=DataStatus.UNAVAILABLE,
            confidence=ConfidenceLevel.UNAVAILABLE,
        )

    sub_scores = []
    for c in usable:
        pct = c.premium_discount_pct
        sub_scores.append(
            100 if pct <= -0.30 else 80 if pct <= -0.10 else 60 if pct <= 0.10
            else 40 if pct <= 0.40 else 20
        )

    avg_score = sum(sub_scores) / len(sub_scores)
    confidence = ConfidenceLevel.HIGH if len(usable) >= 3 else ConfidenceLevel.MEDIUM
    return ScoreComponent(
        name="Valuation", score=round(avg_score, 1), weight=0.0, status=DataStatus.OK,
        confidence=confidence,
    )


# --------------------------------------------------------------------------
# Technical (weight 10%)
# --------------------------------------------------------------------------


def score_technical(technical_metrics: list[MetricResult]) -> ScoreComponent:
    """Rubric:
    - RSI(14): <30 (oversold, could bounce) -> 70, 30-45 -> 60, 45-60 (neutral) -> 80,
      60-70 -> 60, >=70 (overbought) -> 30
    - Price vs SMA 200 (if both a "latest close" and SMA200 are derivable
      from the supplied metrics' `inputs`): above SMA200 -> +20, below -> -20,
      applied as an adjustment to the RSI-based score.

    Requires RSI at minimum; UNAVAILABLE otherwise (this is by far the
    most likely component to be UNAVAILABLE in this project currently,
    since Milestone 1's market-data layer has not yet been exercised
    against live daily price history - see market_data.py's known
    limitations).
    """
    rsi = None
    for m in technical_metrics:
        if m.metric_name.startswith("RSI") and m.status == DataStatus.OK and m.value is not None:
            rsi = m
            break

    if rsi is None:
        return ScoreComponent(
            name="Technical", score=None, weight=0.0, status=DataStatus.UNAVAILABLE,
            confidence=ConfidenceLevel.UNAVAILABLE,
        )

    v = rsi.value
    base_score = 80 if 45 <= v < 60 else 70 if v < 30 else 60 if v < 45 else 60 if v < 70 else 30

    sma_200 = next((m for m in technical_metrics if m.metric_name == "SMA 200" and m.status == DataStatus.OK), None)
    adjustment = 0.0
    if sma_200 and sma_200.value and "latest_close" in sma_200.inputs and sma_200.inputs["latest_close"]:
        adjustment = 20.0 if sma_200.inputs["latest_close"] >= sma_200.value else -20.0

    final_score = _clamp(base_score + adjustment)
    return ScoreComponent(
        name="Technical", score=round(final_score, 1), weight=0.0, status=DataStatus.OK,
        evidence_ids=[rsi.metric_id], confidence=ConfidenceLevel.MEDIUM,
    )


# --------------------------------------------------------------------------
# Risk / Governance (weight 10%)
# --------------------------------------------------------------------------


_SEVERITY_PENALTY = {
    RiskSeverity.LOW: 5.0, RiskSeverity.MODERATE: 15.0, RiskSeverity.HIGH: 30.0, RiskSeverity.SEVERE: 50.0,
}


def score_risk_governance(risks: list[RiskItem]) -> ScoreComponent:
    """Rubric: start at 100, subtract a penalty per identified risk based
    on severity (LOW=-5, MODERATE=-15, HIGH=-30, SEVERE=-50), floored at 0.

    An EMPTY risk list is treated as UNAVAILABLE, not a perfect 100 -
    "no risks were supplied" and "no risks exist" are not the same
    thing, and conflating them would silently reward a component that
    simply wasn't populated yet (Module 8's full risk framework is not
    built in this project as of this milestone).
    """
    if not risks:
        return ScoreComponent(
            name="Risk/Governance", score=None, weight=0.0, status=DataStatus.UNAVAILABLE,
            confidence=ConfidenceLevel.UNAVAILABLE,
            evidence_ids=[],
        )

    total_penalty = sum(_SEVERITY_PENALTY[r.severity] for r in risks)
    score = _clamp(100.0 - total_penalty)
    confidence = ConfidenceLevel.MEDIUM if len(risks) >= 3 else ConfidenceLevel.LOW
    return ScoreComponent(
        name="Risk/Governance", score=round(score, 1), weight=0.0, status=DataStatus.OK,
        evidence_ids=[r.risk_id for r in risks], confidence=confidence,
    )


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------

_DEFAULT_WEIGHTS = {
    "Fundamentals": 0.30, "Cash Flow Quality": 0.15, "Business/Management": 0.15,
    "Valuation": 0.20, "Technical": 0.10, "Risk/Governance": 0.10,
}


def compute_investment_score(
    components: list[ScoreComponent], weights: dict[str, float] | None = None,
) -> InvestmentScore:
    """Aggregate component scores into the overall AI-IDS.

    Missing-data policy: any component with status != OK (score is None)
    is excluded entirely from the weighted average, and the weights of
    the remaining available components are renormalized to sum to 1.0
    (i.e. proportionally scaled up) rather than leaving the unavailable
    component's weight simply unused (which would silently understate
    the overall score) or zero-filling it (which the spec explicitly
    forbids).

    If ALL components are unavailable, overall_score is None - this
    function never fabricates a number from nothing.
    """
    weights = weights or _DEFAULT_WEIGHTS
    missing_weight_keys = [c.name for c in components if c.name not in weights]
    if missing_weight_keys:
        raise ValueError(f"No configured weight for component(s): {missing_weight_keys}")

    available = [c for c in components if c.status == DataStatus.OK and c.score is not None]
    unavailable_names = [c.name for c in components if c not in available]

    total_available_weight = sum(weights[c.name] for c in available)

    final_components: list[ScoreComponent] = []
    overall_score: float | None = None

    if available and total_available_weight > 0:
        weighted_sum = 0.0
        for c in components:
            declared_weight = weights[c.name]
            if c in available:
                renorm_weight = declared_weight / total_available_weight
                weighted_score = round(c.score * renorm_weight, 2)
                weighted_sum += weighted_score
                final_components.append(
                    c.model_copy(update={"weight": declared_weight, "weighted_score": weighted_score})
                )
            else:
                final_components.append(
                    c.model_copy(update={"weight": declared_weight, "weighted_score": None})
                )
        overall_score = round(weighted_sum, 2)
    else:
        final_components = [c.model_copy(update={"weight": weights[c.name]}) for c in components]
        logger.warning("compute_investment_score: no components had usable data; overall_score is None.")

    renormalized = bool(unavailable_names) and bool(available)

    return InvestmentScore(
        overall_score=overall_score, max_possible_score=_MAX_SCORE, components=final_components,
        weights_used=weights, renormalized=renormalized, unavailable_components=unavailable_names,
    )
