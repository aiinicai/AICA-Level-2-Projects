"""Risk & Governance framework — Module 8.

Two complementary sources feed the risk register, and this module never
invents a risk from neither:

1. DETERMINISTIC financial/quantitative risk flags: derived from
   already-computed MetricResult/TrendResult objects (Milestones 2-4)
   using explicit, documented threshold rules (see the _rule_* functions
   below). No LLM involved — these are exact, reproducible, and their
   "evidence" is literally the metric_id of the number that triggered
   them.

2. AI-ASSISTED qualitative risk extraction: derived from document
   evidence already classified as RISK/GOVERNANCE/MANAGEMENT_DISCUSSION
   in Milestone 5, run through the LLM via a dedicated risk-extraction
   prompt (app/ai/prompts.py::build_risk_extraction_prompt) that is
   explicitly instructed to extract ONLY risks the source text itself
   discloses — never to infer a risk from outside knowledge. Every
   resulting RiskItem carries evidence_ids pointing back to the source
   DocumentEvidence, so "why is this a risk" is always traceable to a
   specific page.

Per the spec: "Never invent risk evidence." Both code paths above are
built specifically so that constraint is structural, not just a hope.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from app.core.enums import DataStatus, RiskCategory, RiskSeverity, TrendDirection
from app.core.exceptions import LLMProviderError
from app.core.models import DocumentEvidence, MetricResult, RiskItem, TrendResult
from app.ai.json_utils import parse_json_response
from app.ai.llm_client import LLMClient
from app.ai.prompts import build_risk_extraction_prompt

logger = logging.getLogger(__name__)

_SEVERITY_MAP = {
    "low": RiskSeverity.LOW, "moderate": RiskSeverity.MODERATE,
    "high": RiskSeverity.HIGH, "severe": RiskSeverity.SEVERE,
}
_CATEGORY_MAP = {c.value: c for c in RiskCategory}


# --------------------------------------------------------------------------
# Deterministic financial risk rules
# --------------------------------------------------------------------------
#
# Each rule inspects already-computed metrics/trends and returns a
# RiskItem only if its explicit threshold is crossed. Documented here
# rather than buried, per Principle 4 (no silent assumptions).

def _rule_debt_equity(metrics: list[MetricResult]) -> RiskItem | None:
    m = next((x for x in metrics if x.metric_name == "Debt/Equity" and x.status == DataStatus.OK), None)
    if m is None or m.value is None:
        return None
    if m.value > 1.5:
        severity = RiskSeverity.HIGH
    elif m.value > 1.0:
        severity = RiskSeverity.MODERATE
    else:
        return None
    return RiskItem(
        category=RiskCategory.FINANCIAL,
        description=f"Debt/Equity of {m.value:.2f} in {m.period} indicates elevated leverage.",
        severity=severity, evidence_ids=[m.metric_id],
        probability_assumption="Derived directly from reported balance sheet figures; not a forecast.",
        potential_impact="Higher leverage increases sensitivity to interest rate changes and refinancing risk.",
        monitoring_trigger=f"Debt/Equity rising further above {m.value:.2f}",
    )


def _rule_net_debt_ebitda(metrics: list[MetricResult]) -> RiskItem | None:
    m = next((x for x in metrics if x.metric_name == "Net Debt/EBITDA" and x.status == DataStatus.OK), None)
    if m is None or m.value is None:
        return None
    if m.value > 4.0:
        severity = RiskSeverity.HIGH
    elif m.value > 2.5:
        severity = RiskSeverity.MODERATE
    else:
        return None
    return RiskItem(
        category=RiskCategory.FINANCIAL,
        description=f"Net Debt/EBITDA of {m.value:.2f}x in {m.period} suggests debt load is high relative to earnings.",
        severity=severity, evidence_ids=[m.metric_id],
        probability_assumption="Derived directly from reported figures; not a forecast.",
        potential_impact="Reduced financial flexibility; covenant risk if earnings decline.",
        monitoring_trigger=f"Net Debt/EBITDA rising further above {m.value:.2f}x",
    )


def _rule_cash_conversion(metrics: list[MetricResult]) -> RiskItem | None:
    m = next((x for x in metrics if x.metric_name == "CFO/PAT" and x.status == DataStatus.OK), None)
    if m is None or m.value is None:
        return None
    if m.value < 0.5:
        severity = RiskSeverity.MODERATE
    else:
        return None
    return RiskItem(
        category=RiskCategory.FINANCIAL,
        description=f"CFO/PAT of {m.value:.2f} in {m.period} is below 0.5, indicating reported profit is "
                     "converting to operating cash at a low rate.",
        severity=severity, evidence_ids=[m.metric_id],
        probability_assumption="Derived directly from reported cash flow and profit figures.",
        potential_impact="May indicate earnings quality concerns (e.g. working capital buildup) worth investigating.",
        monitoring_trigger="CFO/PAT remaining below 0.5 for a second consecutive period",
    )


def _rule_negative_fcf(metrics: list[MetricResult]) -> RiskItem | None:
    m = next((x for x in metrics if x.metric_name == "Free Cash Flow" and x.status == DataStatus.OK), None)
    if m is None or m.value is None or m.value >= 0:
        return None
    return RiskItem(
        category=RiskCategory.FINANCIAL,
        description=f"Free Cash Flow was negative ({m.value:.1f}) in {m.period}.",
        severity=RiskSeverity.LOW,  # low by default — negative FCF during expansion capex is often benign
        evidence_ids=[m.metric_id],
        probability_assumption="Derived directly from reported cash flow and estimated capex.",
        potential_impact="If sustained across multiple periods without a growth capex justification, could "
                          "indicate funding pressure.",
        monitoring_trigger="Negative FCF persisting beyond the current capex cycle",
    )


def _rule_deteriorating_trend(trend: TrendResult) -> RiskItem | None:
    if trend.direction != TrendDirection.DETERIORATING:
        return None
    severity = RiskSeverity.HIGH if trend.significance.value == "high" else RiskSeverity.MODERATE
    return RiskItem(
        category=RiskCategory.FINANCIAL,
        description=f"{trend.metric_name} has been deteriorating over {trend.periods[0]}-{trend.periods[-1]}.",
        severity=severity, evidence_ids=[trend.trend_id],
        probability_assumption="Derived directly from the computed multi-period trend classification.",
        potential_impact=f"Continued deterioration in {trend.metric_name} could pressure overall financial health.",
        monitoring_trigger=f"{trend.metric_name} continuing to decline in the next reported period",
    )


def _rule_declining_promoter_holding(trend: TrendResult) -> RiskItem | None:
    """Promoter holding is a governance signal, not a financial one — a
    sustained decline (e.g. lock-in expiry, secondary sales, dilution
    from fundraising) can precede reduced promoter skin-in-the-game, and
    is worth surfacing distinctly from the generic financial-trend rule
    above rather than lumped in as a FINANCIAL risk.
    """
    if trend.metric_name != "Promoter Holding" or trend.direction != TrendDirection.DETERIORATING:
        return None
    severity = RiskSeverity.HIGH if trend.significance.value == "high" else RiskSeverity.MODERATE
    change_str = f"{trend.percentage_change:+.1%}" if trend.percentage_change is not None else "a material amount"
    valid_values = [v for v in trend.values if v is not None]
    if len(valid_values) >= 2:
        description = (
            f"Promoter holding declined {change_str} over {trend.periods[0]}-{trend.periods[-1]} "
            f"(from {valid_values[0]:.1%} to {valid_values[-1]:.1%})."
        )
    else:
        description = f"Promoter holding has been deteriorating over {trend.periods[0]}-{trend.periods[-1]}."
    return RiskItem(
        category=RiskCategory.GOVERNANCE,
        description=description,
        severity=severity, evidence_ids=[trend.trend_id],
        probability_assumption="Derived directly from manually-entered or uploaded shareholding-pattern data "
                                "(see app/analysis/shareholder.py) — not itself independently verified by this application.",
        potential_impact="A declining promoter stake can reflect lock-in expiry, planned secondary sales, or "
                          "dilution from fundraising — not automatically negative, but worth understanding the "
                          "specific cause before drawing a conclusion.",
        monitoring_trigger="Promoter holding continuing to decline in the next reported/filed period",
    )


_FINANCIAL_RULES = [_rule_debt_equity, _rule_net_debt_ebitda, _rule_cash_conversion, _rule_negative_fcf]
_TREND_RULES = [_rule_declining_promoter_holding, _rule_deteriorating_trend]


def detect_financial_risks(
    metrics: list[MetricResult], trends: list[TrendResult] | None = None,
) -> list[RiskItem]:
    """Run every deterministic financial risk rule against the supplied
    metrics (and optionally trends) for one period, returning only the
    rules that actually fired. No LLM call; fully reproducible given the
    same inputs.
    """
    risks: list[RiskItem] = []
    for rule in _FINANCIAL_RULES:
        result = rule(metrics)
        if result is not None:
            risks.append(result)

    for trend in trends or []:
        for trend_rule in _TREND_RULES:
            result = trend_rule(trend)
            if result is not None:
                risks.append(result)
                break  # first matching rule wins — don't double-flag one trend

    return risks


# --------------------------------------------------------------------------
# AI-assisted qualitative risk extraction
# --------------------------------------------------------------------------


def extract_risk_from_evidence(evidence: DocumentEvidence, llm_client: LLMClient) -> RiskItem | None:
    """Extract at most one structured RiskItem from a single piece of
    document evidence. Returns None if the model found no risk disclosed
    in this excerpt (the common case for most pages — not an error).

    Raises:
        LLMProviderError: if the LLM call fails or returns unparseable JSON.
    """
    system, user = build_risk_extraction_prompt(evidence)
    response = llm_client.complete(system=system, user=user)
    data = parse_json_response(response.text)

    if not data.get("risk_found"):
        return None

    category_str = str(data.get("category", "")).lower()
    category = _CATEGORY_MAP.get(category_str)
    if category is None:
        logger.warning("Unrecognized risk category %r from LLM; defaulting to BUSINESS.", category_str)
        category = RiskCategory.BUSINESS

    severity_str = str(data.get("severity", "moderate")).lower()
    severity = _SEVERITY_MAP.get(severity_str, RiskSeverity.MODERATE)

    description = data.get("description")
    if not description:
        return None  # risk_found=true but no description is an incomplete/unusable extraction

    return RiskItem(
        category=category, description=str(description), severity=severity,
        evidence_ids=[evidence.evidence_id],
        potential_impact=data.get("potential_impact"),
        mitigation=data.get("mitigation"),
    )


def extract_risks_batch(
    evidence_list: list[DocumentEvidence], llm_client: LLMClient,
    *,
    delay_seconds: float = 0.0,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[RiskItem]:
    """Extract risks from a batch of document evidence, skipping (with a
    logged warning) any page whose LLM call fails — consistent with
    document_analysis.analyze_evidence_batch's failure handling.

    Args:
        delay_seconds: pause between each page's API call, proactively
            reducing how often a real account's rate limit gets hit —
            see app/ai/rate_limiting.py. 0 (default) disables pacing.
        progress_callback: if supplied, called as
            progress_callback(completed_count, total_count) after every
            page (success, skip, or failure alike).
    """
    total = len(evidence_list)
    risks: list[RiskItem] = []
    for i, evidence in enumerate(evidence_list):
        try:
            risk = extract_risk_from_evidence(evidence, llm_client)
        except LLMProviderError as exc:
            logger.warning(
                "Skipping risk extraction for page %s of %s due to LLM error: %s",
                evidence.page_number, evidence.source_document, exc,
            )
            risk = None
        if risk is not None:
            risks.append(risk)
        if progress_callback is not None:
            progress_callback(i + 1, total)
        if delay_seconds > 0 and i < total - 1:
            time.sleep(delay_seconds)
    return risks


def build_risk_register(
    *,
    metrics: list[MetricResult],
    trends: list[TrendResult] | None = None,
    risk_document_evidence: list[DocumentEvidence] | None = None,
    llm_client: LLMClient | None = None,
) -> list[RiskItem]:
    """Convenience entry point combining both sources into one risk
    register. Qualitative extraction is skipped (not an error) if no
    document evidence or LLM client is supplied — this lets the
    deterministic half of the register be used entirely on its own.
    """
    risks = detect_financial_risks(metrics, trends)
    if risk_document_evidence and llm_client:
        risks.extend(extract_risks_batch(risk_document_evidence, llm_client))
    elif risk_document_evidence and not llm_client:
        logger.info(
            "risk_document_evidence supplied without an llm_client — "
            "qualitative risk extraction skipped; only deterministic "
            "financial risks are included in this register."
        )
    return risks
