"""Explainable Valuation Readiness and Valuation Confidence scoring.

Readiness = completeness of the workflow (data, verification, forecast inputs,
interview, risk coverage). Confidence = how much the methods and data agree.
Neither is a claim of statistical accuracy.
"""
from __future__ import annotations

from typing import Any

READINESS_WEIGHTS = {
    "data_completeness": 0.25,
    "financial_verification": 0.20,
    "forecast_inputs": 0.20,
    "business_interview": 0.20,
    "risk_information": 0.15,
}

ESSENTIAL_ASSUMPTIONS = ["revenue_growth", "ebitda_margin", "wacc", "terminal_growth",
                         "tax_rate", "ev_ebitda_multiple"]


def readiness_score(
    metric_coverage: float,  # 0-1: share of canonical metrics with approved values
    verified_share: float,  # 0-1: share of line items verified
    assumptions_present: int,
    critical_open: int,  # unresolved critical/high questions
    answered: int,
    planned: int,
    risks_covered: int,  # risk categories with information
    risks_total: int,
) -> dict[str, Any]:
    components = {
        "data_completeness": min(metric_coverage, 1.0),
        "financial_verification": min(verified_share, 1.0),
        "forecast_inputs": min(assumptions_present / len(ESSENTIAL_ASSUMPTIONS), 1.0),
        "business_interview": (answered / planned if planned else 0.0) * (0.6 if critical_open else 1.0),
        "risk_information": (risks_covered / risks_total) if risks_total else 0.0,
    }
    total = sum(components[k] * READINESS_WEIGHTS[k] for k in READINESS_WEIGHTS)
    score = round(total * 100)
    label = "Ready" if score >= 85 else ("Almost there!" if score >= 60 else "Getting started")
    band = "Excellent" if score >= 90 else ("Good" if score >= 75 else ("Fair" if score >= 55 else "Low"))
    return {
        "score": score,
        "label": label,
        "band": band,
        "components": {k: round(v * 100) for k, v in components.items()},
        "weights": READINESS_WEIGHTS,
    }


def confidence_score(method_evs: dict[str, float], verified_share: float,
                     assumptions_present: int, terminal_share_of_ev: float | None,
                     normalisations_resolved: bool) -> dict[str, Any]:
    """Blend of method agreement, verification, forecast completeness, sensitivity."""
    # method agreement: dispersion of EVs around their mean
    agreement = 1.0
    if len(method_evs) >= 2:
        vals = list(method_evs.values())
        mean = sum(vals) / len(vals)
        if mean:
            # half-spread around the mean: methods within ±50% of mean → partial credit
            spread = (max(vals) - min(vals)) / mean
            agreement = max(0.0, 1.0 - spread / 2)  # 0 spread → 1.0
    forecast = min(assumptions_present / len(ESSENTIAL_ASSUMPTIONS), 1.0)
    sensitivity = 1.0
    if terminal_share_of_ev is not None:
        # heavy terminal-value reliance reduces confidence
        sensitivity = max(0.3, 1.0 - max(0.0, terminal_share_of_ev - 0.5))
    normal = 1.0 if normalisations_resolved else 0.7

    score = (0.35 * agreement + 0.25 * verified_share + 0.20 * forecast
             + 0.10 * sensitivity + 0.10 * normal)
    pct = round(score * 100)
    label = "High Confidence" if pct >= 80 else ("Moderate Confidence" if pct >= 55 else "Low Confidence")
    return {
        "score": pct,
        "label": label,
        "basis": {
            "method_agreement": round(agreement * 100),
            "data_verification": round(verified_share * 100),
            "forecast_completeness": round(forecast * 100),
            "sensitivity": round(sensitivity * 100),
            "normalisation": round(normal * 100),
        },
    }


def build_wacc(cost_of_equity: float | None, cost_of_debt: float | None,
               equity_weight: float | None, tax_rate: float) -> float | None:
    """WACC from components when all are explicitly provided; else None."""
    if cost_of_equity is None or cost_of_debt is None or equity_weight is None:
        return None
    e = max(0.0, min(1.0, equity_weight))
    return e * cost_of_equity + (1 - e) * cost_of_debt * (1 - tax_rate)
