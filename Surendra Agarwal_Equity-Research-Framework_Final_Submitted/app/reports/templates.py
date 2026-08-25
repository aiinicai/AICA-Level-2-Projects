"""Markdown formatting helpers - Module 14.

Pure functions only: given a typed object, return a markdown string.
No knowledge of report structure/ordering lives here (that's
generator.py's job) - this module just knows how to render one thing
at a time, consistently, including the Level 1/2/3 labeling (Module 13)
that must appear on every rendered claim.
"""

from __future__ import annotations

from app.core.enums import DataStatus, InsightLevel
from app.core.models import (
    AIInterpretation,
    HumanReview,
    InvestmentScore,
    MetricResult,
    RiskItem,
    TrendResult,
)

DISCLAIMER = (
    "**AI-assisted decision support only. Final investment decisions require "
    "human professional judgement.** This report does not predict stock prices "
    "and does not guarantee any investment outcome."
)

_LEVEL_LABELS = {
    InsightLevel.LEVEL_1_VERIFIED: "LEVEL 1 - Verified/Calculated",
    InsightLevel.LEVEL_2_AI_INTERPRETATION: "LEVEL 2 - AI Interpretation",
    InsightLevel.LEVEL_3_HUMAN_VALIDATED: "LEVEL 3 - Human Validated",
}


def format_metric(m: MetricResult) -> str:
    """Render one MetricResult as a markdown bullet. Always Level 1
    (verified/calculated) - this function is never used for AI output."""
    if m.status != DataStatus.OK or m.value is None:
        return f"- **{m.metric_name}** ({m.period}): *not available - {m.status.value}*"
    if m.unit.value == "percent":
        value_str = f"{m.value:.2%}"
    elif m.unit.value == "ratio" and "RSI" not in m.metric_name:
        value_str = f"{m.value:,.2f}x"
    elif m.unit.value == "days":
        value_str = f"{m.value:,.1f} days"
    else:
        value_str = f"{m.value:,.2f}"
    line = f"- **{m.metric_name}** ({m.period}): {value_str} `[{_LEVEL_LABELS[InsightLevel.LEVEL_1_VERIFIED]}]`"
    if m.data_quality_notes:
        line += f"\n  - *Note: {'; '.join(m.data_quality_notes)}*"
    return line


def format_trend(t: TrendResult) -> str:
    span = f"{t.periods[0]}\u2013{t.periods[-1]}" if t.periods else "n/a"
    change_str = f"{t.percentage_change:+.1%}" if t.percentage_change is not None else "n/a"
    return (
        f"- **{t.metric_name}** ({span}): {t.direction.value.upper()} "
        f"(overall change: {change_str}, significance: {t.significance.value}) "
        f"`[{_LEVEL_LABELS[InsightLevel.LEVEL_1_VERIFIED]}]`"
    )


def format_ai_interpretation(a: AIInterpretation) -> str:
    """Always Level 2 - this function must never be used to render a
    verified fact, which is what makes the Level 1/2 boundary structural
    rather than a formatting convention someone could forget."""
    return (
        f"- {a.claim} "
        f"`[{_LEVEL_LABELS[InsightLevel.LEVEL_2_AI_INTERPRETATION]}, "
        f"confidence={a.confidence.value}]`"
    )


def format_risk_item(r: RiskItem) -> str:
    lines = [f"- **[{r.severity.value.upper()}] {r.category.value.title()}**: {r.description}"]
    if r.potential_impact:
        lines.append(f"  - *Potential impact*: {r.potential_impact}")
    if r.mitigation:
        lines.append(f"  - *Mitigation*: {r.mitigation}")
    if r.monitoring_trigger:
        lines.append(f"  - *Monitor*: {r.monitoring_trigger}")
    return "\n".join(lines)


def format_investment_score(score: InvestmentScore) -> str:
    lines = []
    if score.overall_score is None:
        lines.append("**Overall AI-IDS Score: not available** - no component had usable data.")
    else:
        lines.append(f"**Overall AI-IDS Score: {score.overall_score:.1f} / {score.max_possible_score:.0f}**")
        if score.renormalized:
            lines.append(
                f"*Weights renormalized: {', '.join(score.unavailable_components)} "
                "were unavailable and excluded rather than scored as zero.*"
            )
    lines.append("")
    lines.append("| Component | Score | Weight | Weighted | Confidence |")
    lines.append("|---|---|---|---|---|")
    for c in score.components:
        score_str = f"{c.score:.1f}" if c.score is not None else "N/A"
        weighted_str = f"{c.weighted_score:.2f}" if c.weighted_score is not None else "\u2014"
        lines.append(f"| {c.name} | {score_str} | {c.weight:.0%} | {weighted_str} | {c.confidence.value} |")
    return "\n".join(lines)


def format_human_review_checklist(
    reviews: list[HumanReview], target_ids: list[str], target_labels: dict[str, str]
) -> str:
    """Render Module 13 Level 3 - never claims validation that didn't
    happen. Any target_id without a matching HumanReview is rendered as
    unreviewed, explicitly."""
    reviewed_ids = {r.target_id: r for r in reviews}
    lines = []
    for tid in target_ids:
        label = target_labels.get(tid, tid)
        if tid in reviewed_ids:
            r = reviewed_ids[tid]
            status = "[Accepted]" if r.accepted else "[Rejected]"
            lines.append(f"- [x] {label} - {status} by {r.reviewer_name} on {r.reviewed_at.date()}")
        else:
            lines.append(f"- [ ] {label} - *not yet reviewed*")
    return "\n".join(lines) if lines else "*No items require human validation in this report.*"


def section_header(number: int, title: str) -> str:
    return f"\n## {number}. {title}\n"
