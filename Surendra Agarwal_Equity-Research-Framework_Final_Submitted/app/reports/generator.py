"""Report generation - Module 14.

Assembles the spec's 19-section report from typed objects only - no
string concatenation of raw LLM output, no re-deriving numbers here.
Every section either renders already-computed data via templates.py
(so the Level 1/2/3 labeling is structural) or explicitly states that
section's data was not supplied, rather than silently omitting it.

ReportContext is a plain container, not a new "smart" model - it holds
whatever the caller has available for this run. Every field is
Optional/defaults to empty, so a report can be generated from a partial
pipeline run (e.g. no document evidence yet) and will say so honestly
in each affected section rather than fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.models import (
    AIInterpretation,
    AuditTrailEntry,
    Company,
    FinancialStatement,
    HumanReview,
    InvestmentScore,
    InvestmentThesis,
    MetricResult,
    RiskItem,
    TrendResult,
)
from app.reports.templates import (
    DISCLAIMER,
    format_ai_interpretation,
    format_human_review_checklist,
    format_investment_score,
    format_metric,
    format_risk_item,
    format_trend,
    section_header,
)


@dataclass
class ReportContext:
    """Everything a report generation run has available. Every list
    defaults to empty rather than requiring the caller to assemble a
    fully-populated pipeline before a report can be produced at all."""

    company: Company
    statements: list[FinancialStatement] = field(default_factory=list)
    fundamental_metrics: list[MetricResult] = field(default_factory=list)
    cashflow_metrics: list[MetricResult] = field(default_factory=list)
    working_capital_metrics: list[MetricResult] = field(default_factory=list)
    shareholder_metrics: list[MetricResult] = field(default_factory=list)
    technical_metrics: list[MetricResult] = field(default_factory=list)
    valuation_metrics: list[MetricResult] = field(default_factory=list)
    trends: list[TrendResult] = field(default_factory=list)
    business_interpretations: list[AIInterpretation] = field(default_factory=list)
    management_interpretations: list[AIInterpretation] = field(default_factory=list)
    governance_interpretations: list[AIInterpretation] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    investment_score: InvestmentScore | None = None
    thesis: InvestmentThesis | None = None
    human_reviews: list[HumanReview] = field(default_factory=list)
    audit_trail: list[AuditTrailEntry] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_limitations_override: list[str] = field(default_factory=list)


def _section_or_placeholder(items: list, render_fn, empty_message: str) -> str:
    if not items:
        return f"*{empty_message}*"
    return "\n".join(render_fn(i) for i in items)


def _executive_summary(ctx: ReportContext) -> str:
    lines = [f"**{ctx.company.name}** ({ctx.company.ticker}, {ctx.company.exchange.value}) "
             f"- Analysis as of {ctx.company.analysis_date}"]
    if ctx.investment_score and ctx.investment_score.overall_score is not None:
        lines.append(f"\nAI-IDS Score: **{ctx.investment_score.overall_score:.1f}/100**")
    if ctx.thesis:
        lines.append(f"\nRecommendation: **{ctx.thesis.recommendation.value.upper()}** "
                      "*(decision support only - see Section 19 for the full disclaimer)*")
        lines.append(f"\n{ctx.thesis.core_thesis}")
    else:
        lines.append("\n*No investment thesis has been generated for this run.*")
    return "\n".join(lines)


def _company_overview(ctx: ReportContext) -> str:
    lines = [
        f"- **Name**: {ctx.company.name}",
        f"- **Ticker**: {ctx.company.ticker} ({ctx.company.exchange.value})",
        f"- **Sector**: {ctx.company.sector or 'not specified'}",
        f"- **Analysis date**: {ctx.company.analysis_date}",
    ]
    return "\n".join(lines)


def _historical_financial_analysis(ctx: ReportContext) -> str:
    from app.reports.metric_tables import (
        build_key_financials_metrics,
        dataframe_to_markdown_table,
        pivot_metrics_to_wide_table,
    )

    # These tables are exclusively deterministic MetricResult data
    # (never AI-generated) — per-cell `[LEVEL 1 - Verified/Calculated]`
    # tagging (as used elsewhere by format_metric()) would be unreadable
    # repeated across dozens of table cells, so the label is stated once
    # per table instead — preserving the Level 1/2/3 labeling principle
    # in spirit without cluttering the actual numbers.
    level1_note = "`[LEVEL 1 - Verified/Calculated]` — every figure in this table.\n\n"

    parts = []
    if ctx.statements:
        key_financials = build_key_financials_metrics(ctx.statements)
        table = dataframe_to_markdown_table(pivot_metrics_to_wide_table(key_financials))
        parts.append("**Key Financials**\n\n" + level1_note + table)
    if ctx.fundamental_metrics:
        table = dataframe_to_markdown_table(pivot_metrics_to_wide_table(ctx.fundamental_metrics))
        parts.append("**Fundamentals**\n\n" + level1_note + table)
    if ctx.cashflow_metrics:
        table = dataframe_to_markdown_table(pivot_metrics_to_wide_table(ctx.cashflow_metrics))
        parts.append("**Cash Flow**\n\n" + level1_note + table)
    if ctx.working_capital_metrics:
        table = dataframe_to_markdown_table(pivot_metrics_to_wide_table(ctx.working_capital_metrics))
        parts.append("**Working Capital**\n\n" + level1_note + table)
    if ctx.shareholder_metrics:
        table = dataframe_to_markdown_table(pivot_metrics_to_wide_table(ctx.shareholder_metrics))
        parts.append("**Shareholder Metrics**\n\n" + level1_note + table)
    if ctx.trends:
        parts.append("**Trends**\n" + "\n".join(format_trend(t) for t in ctx.trends))
    if not parts:
        return "*No financial metrics have been computed for this run.*"
    return "\n\n".join(parts)


def _management_analysis(ctx: ReportContext) -> str:
    return _section_or_placeholder(
        ctx.management_interpretations, format_ai_interpretation,
        "No management commentary has been extracted for this run.",
    )


def _corporate_governance(ctx: ReportContext) -> str:
    return _section_or_placeholder(
        ctx.governance_interpretations, format_ai_interpretation,
        "No governance-related commentary has been extracted for this run.",
    )


def _competitive_position(ctx: ReportContext) -> str:
    return _section_or_placeholder(
        ctx.business_interpretations, format_ai_interpretation,
        "No business/competitive-position commentary has been extracted for this run.",
    )


def _technical_analysis(ctx: ReportContext) -> str:
    return _section_or_placeholder(
        ctx.technical_metrics, format_metric,
        "No technical indicators have been computed for this run (requires daily price history).",
    )


def _valuation(ctx: ReportContext) -> str:
    return _section_or_placeholder(
        ctx.valuation_metrics, format_metric,
        "No valuation metrics have been computed for this run.",
    )


def _risk_analysis(ctx: ReportContext) -> str:
    if not ctx.risks:
        return "*No risks have been identified/supplied for this run.*"
    by_category: dict[str, list[RiskItem]] = {}
    for r in ctx.risks:
        by_category.setdefault(r.category.value, []).append(r)
    parts = []
    for category, items in sorted(by_category.items()):
        parts.append(f"**{category.title()} Risk**\n" + "\n".join(format_risk_item(r) for r in items))
    return "\n\n".join(parts)


def _investment_score_section(ctx: ReportContext) -> str:
    if ctx.investment_score is None:
        return "*No investment score has been computed for this run.*"
    return format_investment_score(ctx.investment_score)


def _investment_thesis(ctx: ReportContext) -> str:
    if ctx.thesis is None:
        return "*No investment thesis has been generated for this run.*"
    return ctx.thesis.core_thesis


def _counter_thesis(ctx: ReportContext) -> str:
    if ctx.thesis is None or not ctx.thesis.counterarguments:
        return "*No counterarguments available.*"
    return "\n".join(f"- {c}" for c in ctx.thesis.counterarguments)


def _catalysts(ctx: ReportContext) -> str:
    if ctx.thesis is None or not ctx.thesis.catalysts:
        return "*No catalysts identified.*"
    return "\n".join(f"- {c}" for c in ctx.thesis.catalysts)


def _invalidation_triggers(ctx: ReportContext) -> str:
    if ctx.thesis is None or not ctx.thesis.invalidation_triggers:
        return (
            "*No thesis invalidation triggers were generated. Per methodology, a "
            "thesis with fewer than 2 invalidation triggers should be treated with "
            "extra caution - see Data Limitations.*"
        )
    lines = []
    for t in ctx.thesis.invalidation_triggers:
        ref = f" (ref: {t.metric_reference})" if t.metric_reference else ""
        lines.append(f"- {t.condition}{ref} *[basis: {t.threshold_basis}]*")
    return "\n".join(lines)


def _data_limitations(ctx: ReportContext) -> str:
    limitations = list(ctx.data_limitations_override)
    if ctx.thesis:
        limitations.extend(ctx.thesis.data_limitations)
    if not ctx.statements:
        limitations.append("No structured financial statements were supplied for this run.")
    if not limitations:
        return "*No specific data limitations were flagged for this run.*"
    seen = set()
    unique = []
    for item in limitations:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return "\n".join(f"- {l}" for l in unique)


def _human_validation_checklist(ctx: ReportContext) -> str:
    all_interps = ctx.business_interpretations + ctx.management_interpretations + ctx.governance_interpretations
    target_ids = [i.interpretation_id for i in all_interps]
    target_labels = {i.interpretation_id: i.claim[:80] for i in all_interps}
    if ctx.thesis is not None:
        target_ids.append("thesis")
        target_labels["thesis"] = f"Investment thesis ({ctx.thesis.recommendation.value.upper()})"
    return format_human_review_checklist(ctx.human_reviews, target_ids, target_labels)


def _final_conclusion(ctx: ReportContext) -> str:
    lines = [DISCLAIMER]
    if ctx.thesis:
        lines.append(f"\nBased on the analysis above, the decision-support recommendation is "
                      f"**{ctx.thesis.recommendation.value.upper()}**, subject to human review "
                      "of all Level 2 (AI Interpretation) content and the data limitations noted "
                      "in Section 17.")
    else:
        lines.append("\nNo recommendation has been generated for this run.")
    return "\n".join(lines)


_SECTIONS = [
    ("Executive Summary", _executive_summary),
    ("Company Overview", _company_overview),
    ("Business Model", _competitive_position),
    ("Industry Overview", lambda ctx: "*Industry overview requires business-focused document "
                                       "evidence; see Section 8 (Competitive Position).*"),
    ("Historical Financial Analysis", _historical_financial_analysis),
    ("Management Analysis", _management_analysis),
    ("Corporate Governance", _corporate_governance),
    ("Competitive Position", _competitive_position),
    ("Technical Analysis", _technical_analysis),
    ("Valuation", _valuation),
    ("Risk Analysis", _risk_analysis),
    ("Investment Score", _investment_score_section),
    ("Investment Thesis", _investment_thesis),
    ("Counter-Thesis", _counter_thesis),
    ("Catalysts", _catalysts),
    ("Thesis Invalidation Triggers", _invalidation_triggers),
    ("Data Limitations", _data_limitations),
    ("Human Validation Checklist", _human_validation_checklist),
    ("Final Decision-Support Conclusion", _final_conclusion),
]


def generate_report(ctx: ReportContext) -> str:
    """Generate the full 19-section markdown report. Always succeeds -
    sections with no supplied data render an explicit placeholder
    rather than raising, since a partial pipeline run should still
    produce a reviewable (if incomplete) document.
    """
    lines = [
        f"# Equity Research Report: {ctx.company.name} ({ctx.company.ticker})",
        f"*Generated {ctx.generated_at.strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        DISCLAIMER,
    ]
    for i, (title, render_fn) in enumerate(_SECTIONS, start=1):
        lines.append(section_header(i, title))
        lines.append(render_fn(ctx))
    return "\n".join(lines)


def generate_audit_trail_export(ctx: ReportContext) -> list[dict]:
    """Serializable audit trail, exportable alongside the report so
    every claim's lineage can be reviewed independently of the prose."""
    return [e.model_dump(mode="json") for e in ctx.audit_trail]
