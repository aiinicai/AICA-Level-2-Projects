"""Central deterministic rules engine.

All product rules live here — never scattered across frontend components.
A rule evaluates against the analytics package and (optionally) interview
facts, producing triggers that drive the adaptive interview and risk flags.
"""
from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Any, Callable

_OPS: dict[str, Callable[[float, float], bool]] = {
    ">": operator.gt, "<": operator.lt, ">=": operator.ge,
    "<=": operator.le, "==": operator.eq, "abs>": lambda a, b: abs(a) > b,
}


@dataclass
class Rule:
    code: str
    metric: str  # key into analytics summary or latest-period ratios
    operator: str
    threshold: float
    severity: str  # high | medium | low
    action: str
    message: str = ""
    scope: str = "summary"  # summary | latest | fact
    field: str = ""  # for scope=fact: key into extra facts dict


RULES: list[Rule] = [
    Rule("REV_GROWTH_HIGH", "latest_revenue_growth", ">", 0.25, "high",
         "investigate_growth_sustainability",
         "YoY revenue growth exceeds 25% — investigate growth sustainability."),
    Rule("REV_DECLINE", "latest_revenue_growth", "<", -0.10, "high",
         "investigate_decline_and_recovery",
         "Revenue declined more than 10% — investigate decline and recovery."),
    Rule("EBITDA_MARGIN_SWING", "margin_change_pp", "abs>", 0.03, "medium",
         "investigate_margin_movement",
         "EBITDA margin moved more than 3 percentage points year on year."),
    Rule("CFO_PAT_LOW", "cfo_pat", "<", 0.70, "high",
         "investigate_earnings_to_cash_conversion",
         "CFO/PAT below 0.70 — earnings are not fully converting to cash.", scope="latest"),
    Rule("DEBT_EQUITY_HIGH", "debt_equity", ">", 1.50, "high",
         "investigate_leverage_refinancing",
         "Debt/Equity above 1.5× — investigate leverage and refinancing risk.", scope="latest"),
    Rule("RECEIVABLE_DAYS_UP", "receivable_days_change", ">", 0.20, "medium",
         "investigate_collections",
         "Receivable days increased more than 20% — investigate collections.", scope="summary"),
    Rule("EXCEPTIONAL_ITEM", "exceptional_to_ebitda", ">", 0.10, "high",
         "investigate_normalisation",
         "Non-recurring item exceeds 10% of EBITDA — normalisation required.", scope="fact",
         field="exceptional_to_ebitda"),
    Rule("CUSTOMER_CONCENTRATION", "largest_customer_share", ">", 0.25, "medium",
         "flag_concentration_risk",
         "Largest customer contributes more than 25% of revenue.", scope="fact",
         field="largest_customer_share"),
    Rule("REV_VOLATILITY", "revenue_volatility", ">", 0.20, "medium",
         "investigate_revenue_stability",
         "Revenue growth is volatile across periods."),
    Rule("INTEREST_COVER_LOW", "interest_coverage", "<", 2.0, "medium",
         "investigate_debt_service",
         "Interest coverage below 2× — debt service capacity is thin.", scope="latest"),
]


def evaluate_rules(analytics: dict[str, Any], facts: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Evaluate all rules; returns trigger dicts."""
    facts = facts or {}
    summary = dict(analytics.get("summary", {}))
    periods: list[str] = analytics.get("periods", [])
    latest = analytics.get("per_period", {}).get(periods[-1], {}) if periods else {}

    # derived: receivable days change over the window
    per_period = analytics.get("per_period", {})
    rd = [per_period.get(p, {}).get("receivable_days") for p in periods]
    rd_known = [v for v in rd if v is not None]
    if len(rd_known) >= 2 and rd_known[0]:
        summary["receivable_days_change"] = (rd_known[-1] - rd_known[0]) / rd_known[0]

    triggers: list[dict[str, Any]] = []
    for rule in RULES:
        if rule.scope == "summary":
            value = summary.get(rule.metric)
        elif rule.scope == "latest":
            value = latest.get(rule.metric)
        else:
            value = facts.get(rule.field)
        if value is None:
            continue
        op = _OPS[rule.operator]
        if op(float(value), rule.threshold):
            triggers.append({
                "rule_code": rule.code,
                "metric": rule.metric,
                "observed_value": float(value),
                "threshold": rule.threshold,
                "severity": rule.severity,
                "action": rule.action,
                "message": rule.message,
                "period_label": periods[-1] if periods else "",
            })
    return triggers
