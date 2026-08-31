"""Deterministic interview question bank.

Priority = materiality × valuation_impact × uncertainty (each 1-5), mapped to
critical/high/medium/low bands. Rule-triggered questions outrank baseline ones.
The AI may re-draft phrasing, but the plan itself is deterministic."""
from __future__ import annotations

from typing import Any

# question templates; {placeholders} filled from analytics context
BASELINE_QUESTIONS: list[dict[str, Any]] = [
    dict(code="BIZ_001", category="business_overview", m=4, v=3, u=4,
         question="How would you describe the company's core business model and primary revenue streams?",
         type="text", options=[], impact=["business_understanding"]),
    dict(code="BIZ_002", category="business_overview", m=3, v=3, u=3,
         question="What proportion of revenue is recurring or repeat in nature?",
         type="single_choice",
         options=["Over 75% recurring", "50–75% recurring", "25–50% recurring", "Under 25% recurring"],
         impact=["revenue_quality", "growth_sustainability"]),
    dict(code="GROWTH_001", category="growth", m=5, v=5, u=3,
         question="Has your company experienced strong revenue growth in the last 3 years?",
         type="single_choice",
         options=["Yes, strong growth (> 20% CAGR)", "Moderate growth (5% – 20% CAGR)",
                  "Flat / No growth (-5% – 5% CAGR)", "Declining revenue (< -5% CAGR)"],
         impact=["revenue_forecast", "growth_sustainability"],
         reason="Revenue growth is a key indicator of business momentum and helps determine "
                "appropriate valuation multiples and growth-adjusted cash flow projections."),
    dict(code="CUST_001", category="customers", m=4, v=4, u=4,
         question="Approximately what share of revenue comes from your single largest customer?",
         type="single_choice",
         options=["Under 10%", "10% – 25%", "25% – 50%", "Over 50%"],
         impact=["concentration_risk", "discount_rate"]),
    dict(code="PROF_001", category="profitability", m=4, v=4, u=3,
         question="Do you expect current EBITDA margins to be sustainable over the next 3–5 years?",
         type="single_choice",
         options=["Yes, margins should improve", "Yes, broadly stable",
                  "Some pressure expected", "Material decline likely"],
         impact=["ebitda_margin_forecast"]),
    dict(code="WC_001", category="working_capital", m=3, v=3, u=3,
         question="Are current receivable and inventory levels representative of normal operations?",
         type="yes_no", options=["Yes", "No"],
         impact=["nwc_assumption"]),
    dict(code="CAPEX_001", category="capex", m=4, v=4, u=4,
         question="What level of capital expenditure do you expect over the next 3 years?",
         type="single_choice",
         options=["Maintenance only (≈ current levels)", "Moderate expansion", "Major capacity expansion",
                  "Reducing capex"],
         impact=["capex_forecast", "fcf_forecast"]),
    dict(code="MGMT_001", category="management", m=3, v=3, u=3,
         question="How dependent is day-to-day operation on the promoters/founders?",
         type="single_choice",
         options=["Professional team runs operations", "Partially promoter-dependent",
                  "Heavily promoter-dependent"],
         impact=["key_person_risk"]),
    dict(code="RISK_001", category="business_risks", m=4, v=4, u=4,
         question="Are there any pending litigations, regulatory issues or contingent liabilities?",
         type="single_choice",
         options=["None material", "Minor matters", "Material matters exist"],
         impact=["risk_assessment", "nav_adjustment"]),
    dict(code="RPT_001", category="related_parties", m=3, v=3, u=4,
         question="Are there material related-party transactions (sales, purchases, loans or remuneration)?",
         type="single_choice",
         options=["None material", "At arm's length, disclosed", "Material and needing normalisation"],
         impact=["normalisation"]),
    dict(code="FCST_001", category="forecast", m=5, v=5, u=4,
         question="What annual revenue growth do you consider realistic for the next 5 years?",
         type="percentage", options=[],
         impact=["revenue_forecast"]),
    dict(code="COMP_001", category="competition", m=3, v=3, u=3,
         question="How would you characterise competitive intensity in your core market?",
         type="single_choice",
         options=["Few competitors, strong moat", "Moderate competition", "Intense price competition"],
         impact=["margin_forecast", "discount_rate"]),
]

# rule_code → triggered question template
TRIGGERED_QUESTIONS: dict[str, dict[str, Any]] = {
    "REV_GROWTH_HIGH": dict(
        code="GROWTH_004", category="growth", m=5, v=5, u=5,
        question="What principally contributed to the substantial increase in revenue during {latest_period}?",
        type="single_choice",
        options=["New customers", "Price increase", "New geography", "New product/service",
                 "One-time order", "Acquisition", "Other"],
        impact=["revenue_forecast", "growth_sustainability"],
        reason="Revenue growth of {revenue_growth_pct} materially exceeds the 25% threshold — "
               "the driver determines whether this growth can be sustained in projections."),
    "REV_DECLINE": dict(
        code="GROWTH_005", category="growth", m=5, v=5, u=5,
        question="What caused the revenue decline in {latest_period}, and is recovery underway?",
        type="text", options=[],
        impact=["revenue_forecast"],
        reason="Revenue declined more than 10% — decline drivers and recovery paths change the forecast."),
    "EBITDA_MARGIN_SWING": dict(
        code="PROF_004", category="profitability", m=4, v=5, u=4,
        question="EBITDA margin moved by {margin_change_pp} percentage points in {latest_period}. What drove this?",
        type="single_choice",
        options=["Input cost movement", "Pricing change", "Operating leverage", "One-time expense/income",
                 "Product mix change", "Other"],
        impact=["ebitda_margin_forecast", "normalisation"],
        reason="A margin swing above 3pp needs a cause before margins can be projected."),
    "CFO_PAT_LOW": dict(
        code="CASH_003", category="working_capital", m=5, v=4, u=4,
        question="Operating cash flow is only {cfo_pat_ratio} of reported profit. What is causing this gap?",
        type="single_choice",
        options=["Receivables build-up", "Inventory build-up", "Advance payments to suppliers",
                 "Revenue recognised ahead of billing", "Other"],
        impact=["earnings_quality", "nwc_assumption"],
        reason="CFO/PAT below 0.70 questions how fully earnings convert to cash."),
    "DEBT_EQUITY_HIGH": dict(
        code="DEBT_002", category="capital_structure", m=5, v=4, u=4,
        question="Debt/Equity stands at {debt_equity}. What is the plan for servicing or refinancing this debt?",
        type="text", options=[],
        impact=["discount_rate", "risk_assessment"],
        reason="Leverage above 1.5× raises refinancing and solvency questions."),
    "RECEIVABLE_DAYS_UP": dict(
        code="WC_004", category="working_capital", m=4, v=4, u=4,
        question="Receivable days increased materially. Are any large receivables overdue or disputed?",
        type="single_choice",
        options=["No, timing only", "Some overdue but collectible", "Disputed amounts exist",
                 "Provision likely needed"],
        impact=["nwc_assumption", "earnings_quality"],
        reason="A >20% rise in receivable days can signal collection stress or channel stuffing."),
    "EXCEPTIONAL_ITEM": dict(
        code="NORM_002", category="normalisation", m=5, v=5, u=4,
        question="A non-recurring item exceeds 10% of EBITDA. Should this be normalised out of earnings?",
        type="yes_no", options=["Yes", "No"],
        impact=["normalisation", "ebitda_margin_forecast"],
        reason="Material one-off items distort maintainable earnings used in valuation."),
    "CUSTOMER_CONCENTRATION": dict(
        code="CUST_004", category="customers", m=4, v=4, u=4,
        question="Your largest customer contributes over 25% of revenue. How secure is this relationship?",
        type="single_choice",
        options=["Long-term contract in place", "Long relationship, no contract",
                 "Recently won", "At risk"],
        impact=["concentration_risk", "discount_rate"],
        reason="Concentration above 25% affects risk premium and forecast confidence."),
    "REV_VOLATILITY": dict(
        code="GROWTH_006", category="growth", m=3, v=4, u=4,
        question="Revenue growth has been volatile across recent years. What explains the swings?",
        type="text", options=[],
        impact=["revenue_forecast", "discount_rate"],
        reason="Volatile growth reduces forecast reliability and may warrant a wider range."),
    "INTEREST_COVER_LOW": dict(
        code="DEBT_003", category="capital_structure", m=4, v=4, u=3,
        question="Interest coverage is below 2×. Are debt covenants being met comfortably?",
        type="yes_no", options=["Yes", "No"],
        impact=["risk_assessment", "discount_rate"],
        reason="Thin interest coverage raises going-concern and refinancing risk."),
}

# adaptive follow-ups: (question_code, answer_matcher) → follow-up template
FOLLOW_UPS: list[dict[str, Any]] = [
    dict(parent="GROWTH_004", match="One-time order",
         code="GROWTH_004A", category="normalisation", m=5, v=5, u=5,
         question="Approximately what amount of {latest_period} revenue arose from this one-time order?",
         type="currency", options=[],
         impact=["normalisation", "revenue_forecast"],
         reason="One-time revenue must be quantified so it can be normalised out of the forecast base."),
    dict(parent="GROWTH_004A", match="*",
         code="GROWTH_004B", category="normalisation", m=4, v=5, u=4,
         question="Do you expect similar orders to recur regularly in future years?",
         type="single_choice",
         options=["Yes, regularly", "Occasionally", "Unlikely to recur"],
         impact=["revenue_forecast", "normalisation"],
         reason="Recurrence determines whether the one-time order stays in the valuation base."),
    dict(parent="CUST_001", match="Over 50%",
         code="CUST_005", category="customers", m=5, v=4, u=4,
         question="Is there a contractual commitment with this dominant customer, and for how long?",
         type="text", options=[],
         impact=["concentration_risk"],
         reason="Dominant-customer dependence above 50% is a critical valuation risk."),
    dict(parent="CUST_001", match="25% – 50%",
         code="CUST_004", category="customers", m=4, v=4, u=4,
         question="Your largest customer contributes over 25% of revenue. How secure is this relationship?",
         type="single_choice",
         options=["Long-term contract in place", "Long relationship, no contract", "Recently won", "At risk"],
         impact=["concentration_risk", "discount_rate"],
         reason="Concentration above 25% affects risk premium and forecast confidence."),
    dict(parent="RISK_001", match="Material matters exist",
         code="RISK_002", category="litigation", m=5, v=4, u=5,
         question="Please describe the material litigation/contingencies and the amounts involved.",
         type="text", options=[],
         impact=["nav_adjustment", "risk_assessment"],
         reason="Material contingent liabilities may need an adjustment in the NAV method."),
    dict(parent="RPT_001", match="Material and needing normalisation",
         code="RPT_002", category="related_parties", m=4, v=4, u=4,
         question="Which related-party amounts should be normalised, and to what arm's-length level?",
         type="text", options=[],
         impact=["normalisation"],
         reason="Off-market related-party terms distort maintainable earnings."),
]


def score_to_priority(m: int, v: int, u: int) -> tuple[float, str]:
    score = m * v * u  # 1..125
    if score >= 100:
        return score, "critical"
    if score >= 60:
        return score, "high"
    if score >= 27:
        return score, "medium"
    return score, "low"
