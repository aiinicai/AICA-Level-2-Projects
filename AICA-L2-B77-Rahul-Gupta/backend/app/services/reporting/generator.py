"""Professional report generation: Jinja2 HTML + pluggable PDF rendering.

The AI receives only the structured authoritative data package and returns
narrative HTML for specific sections; deterministic fallbacks are used when
the AI is unavailable. PDF rendering is isolated behind render_pdf() so the
renderer (xhtml2pdf today, WeasyPrint if installed) can be swapped."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import BACKEND_DIR, get_settings
from ...models import (
    AIInsight, AuditLog, Document, InterviewAnswer, InterviewQuestion,
    NormalisationAdjustment, Report, RuleTrigger, ValuationCase, ValuationRun,
)
from ..ai.provider import AIProviderError
from ..ai.service import get_ai_config, get_provider, logged_call
from ..financial.canonical import METRIC_LABELS
from ..financial.numbers import format_inr
from ..financial.store import compute_case_analytics, load_financial_data

log = logging.getLogger(__name__)

_env = Environment(
    loader=FileSystemLoader(str(BACKEND_DIR / "app" / "templates")),
    autoescape=select_autoescape(["html"]),
)

NARRATIVE_SECTIONS = [
    "executive_summary", "company_profile", "financial_performance",
    "earnings_quality", "business_assessment", "dcf_commentary",
    "value_drivers", "conclusion",
]

ASSUMPTION_LABELS = {
    "revenue_growth": ("Revenue Growth (CAGR)", "pct"),
    "ebitda_margin": ("EBITDA Margin", "pct"),
    "wacc": ("WACC / Discount Rate", "pct"),
    "terminal_growth": ("Terminal Growth Rate", "pct"),
    "tax_rate": ("Tax Rate", "pct"),
    "ev_ebitda_multiple": ("EV/EBITDA Multiple (Exit)", "x"),
    "capex_pct": ("Capex (% of Revenue)", "pct"),
    "nwc_pct": ("Net Working Capital (% of Revenue)", "pct"),
    "depreciation_pct": ("Depreciation (% of Revenue)", "pct"),
}

REPORT_METRIC_ORDER = [
    "revenue", "other_income", "ebitda", "depreciation", "ebit", "finance_cost",
    "pbt", "tax", "pat", "net_worth", "total_assets", "cash", "cfo", "capex",
]

RATIO_ROWS = [
    ("revenue_growth", "Revenue Growth", "pct"),
    ("ebitda_margin", "EBITDA Margin", "pct"),
    ("pat_margin", "PAT Margin", "pct"),
    ("roe", "Return on Equity", "pct"),
    ("roce", "ROCE", "pct"),
    ("current_ratio", "Current Ratio", "x"),
    ("debt_equity", "Debt / Equity", "x"),
    ("cfo_pat", "CFO / PAT", "x"),
    ("receivable_days", "Receivable Days", "days"),
]


def _fmt_ratio(v: float | None, kind: str) -> str:
    if v is None:
        return "—"
    if kind == "pct":
        return f"{v * 100:.1f}%"
    if kind == "days":
        return f"{v:.0f}"
    return f"{v:.2f}×"


def _fallback_narrative(case: ValuationCase, run: ValuationRun, analytics: dict) -> dict[str, str]:
    s = analytics.get("summary", {})
    growth = s.get("revenue_cagr")
    margin = s.get("latest_ebitda_margin")
    name = case.company.name if case.company else "The company"
    p = lambda t: f"<p>{t}</p>"
    return {
        "executive_summary": p(
            f"{name} has been valued using discounted cash flow, market multiple and "
            f"adjusted net asset value methods on human-approved historical financials. "
            + (f"Revenue compounded at {growth * 100:.1f}% with an EBITDA margin of "
               f"{margin * 100:.1f}% in the latest year. " if growth is not None and margin is not None else "")
            + "Multiple valuation methods support the indicative range shown below."),
        "company_profile": p(
            f"{name} operates in the {case.company.industry if case.company else ''} sector as a "
            f"{case.company.entity_type.lower() if case.company else 'private company'} in "
            f"{case.company.country if case.company else 'India'}."),
        "financial_performance": p(
            "The historical statements above were extracted by the Python document engine, "
            "independently verified and locked after analyst review."),
        "earnings_quality": p(
            "Earnings quality has been assessed through cash conversion, normalisation "
            "requirements and accounting validation checks summarised in this report."),
        "business_assessment": p(
            "Management responses captured through the adaptive AI interview inform the "
            "growth, margin and risk assumptions adopted in the valuation."),
        "dcf_commentary": p(
            "The FCFF projection applies the accepted growth, margin, capex and working-"
            "capital assumptions, discounted at the accepted WACC with a Gordon terminal value."),
        "value_drivers": p(
            "The tornado and assumption-impact analyses identify the assumptions to which "
            "this valuation is most sensitive; these deserve the greatest diligence."),
        "conclusion": p(
            f"Based on the selected methods and their weights, the central estimate is "
            f"{format_inr(run.central_estimate)} within an indicative range of "
            f"{format_inr(run.range_low)} – {format_inr(run.range_high)}."),
    }


def generate_report(db: Session, case: ValuationCase, template: str = "comprehensive",
                    options: dict | None = None, analyst: str = "Arjun Demo") -> Report:
    settings = get_settings()
    options = options or {}
    run = db.execute(select(ValuationRun).where(
        ValuationRun.case_id == case.id, ValuationRun.is_current == 1)).scalars().first()
    if run is None:
        raise ValueError("No valuation run exists — calculate the valuation first")

    analytics = compute_case_analytics(db, case.id)
    data, periods = load_financial_data(db, case.id)
    detail = run.detail or {}
    result = detail.get("result", {})
    methods = result.get("methods", {})

    financial_rows = []
    for metric in REPORT_METRIC_ORDER:
        if not any(metric in data.get(p, {}) for p in periods):
            continue
        financial_rows.append({
            "label": METRIC_LABELS.get(metric, metric),
            "vals": [
                (f"{data[p][metric] / 1e7:,.2f}" if metric in data.get(p, {}) else "—")
                for p in periods
            ],
        })

    ratio_rows = []
    for key, label, kind in RATIO_ROWS:
        vals = [analytics["per_period"].get(p, {}).get(key) for p in periods]
        if not any(v is not None for v in vals):
            continue
        ratio_rows.append({"label": label, "vals": [_fmt_ratio(v, kind) for v in vals]})

    method_labels = {"dcf": "Discounted Cash Flow", "market_multiple": "Market Multiple",
                     "adjusted_nav": "Adjusted NAV"}
    bar_classes = {"dcf": "", "market_multiple": "alt", "adjusted_nav": "nav"}
    evs = [m.get("enterprise_value") or 0 for m in methods.values()]
    max_ev = max(evs) if evs else 1
    method_rows = []
    for key, m in methods.items():
        w = result.get("weights", {}).get(key, 0)
        ev = m.get("enterprise_value") or 0
        method_rows.append({
            "label": method_labels.get(key, key), "ev": ev, "eq": m.get("equity_value"),
            "weight": w, "contribution": ev * w,
            "bar_pct": max(5, round(ev / max_ev * 60)) if max_ev else 5,
            "bar_class": bar_classes.get(key, ""),
        })

    assumptions_rows = []
    for key, val in (run.assumptions or {}).items():
        if key not in ASSUMPTION_LABELS or val is None:
            continue
        label, kind = ASSUMPTION_LABELS[key]
        display = f"{val * 100:.1f}%" if kind == "pct" else f"{val:.1f}×"
        assumptions_rows.append({"label": label, "display": display, "source": "Accepted by analyst"})

    questions = {q.id: q for q in db.execute(select(InterviewQuestion).where(
        InterviewQuestion.case_id == case.id)).scalars()}
    findings = [
        {"question": questions[a.question_id].question if a.question_id in questions else "",
         "answer": str(a.answer_value.get("value", "")), "signal": a.signal}
        for a in db.execute(select(InterviewAnswer).where(
            InterviewAnswer.case_id == case.id)).scalars()
    ]

    risks = [
        {"title": i.title, "body": i.body, "severity": i.severity}
        for i in db.execute(select(AIInsight).where(
            AIInsight.case_id == case.id, AIInsight.section == "risk_flag")).scalars()
    ]

    normalisations = db.execute(select(NormalisationAdjustment).where(
        NormalisationAdjustment.case_id == case.id,
        NormalisationAdjustment.status.in_(["approved", "proposed"]))).scalars().all()

    documents = db.execute(select(Document).where(
        Document.case_id == case.id)).scalars().all()

    # AI narrative (optional, engine values are authoritative)
    narrative = _fallback_narrative(case, run, analytics)
    cfg = get_ai_config(db)
    provider = get_provider(db)
    if provider and cfg.get("ai_final_report", True) and options.get("ai_narrative", True):
        payload = {
            "company": {"name": case.company.name if case.company else "",
                        "industry": case.company.industry if case.company else "",
                        "purpose": case.purpose},
            "historical_summary": analytics["summary"],
            "valuation": {"central_estimate_ev": run.central_estimate,
                          "range": [run.range_low, run.range_high],
                          "equity_value": run.equity_value,
                          "per_share": run.per_share_value,
                          "confidence": run.confidence_label,
                          "weights": result.get("weights"),
                          "methods": {k: {"ev": m.get("enterprise_value"),
                                          "equity": m.get("equity_value")}
                                      for k, m in methods.items()}},
            "scenarios": detail.get("scenarios"),
            "top_sensitivities": (detail.get("assumption_impacts") or [])[:4],
            "risks": risks,
            "interview_findings": findings,
            "normalisations": [
                {"metric": n.metric, "adjustment": n.adjustment, "reason": n.reason,
                 "status": n.status} for n in normalisations],
        }
        try:
            ai_sections = logged_call(db, "report", case.id,
                                      provider.generate_report_sections, payload,
                                      NARRATIVE_SECTIONS, _provider=provider)
            for k in NARRATIVE_SECTIONS:
                v = ai_sections.get(k)
                if isinstance(v, str) and v.strip():
                    narrative[k] = v if v.strip().startswith("<") else f"<p>{v}</p>"
        except AIProviderError as e:
            log.warning("AI narrative unavailable, using deterministic text: %s", e)

    tpl = _env.get_template("report.html")
    html = tpl.render(
        company=case.company, case=case, run=run,
        periods=periods, financial_rows=financial_rows, ratio_rows=ratio_rows,
        dcf=methods.get("dcf"), mm=methods.get("market_multiple"),
        nav=methods.get("adjusted_nav"), method_rows=method_rows,
        bridge=result.get("bridge", {}),
        heatmap=detail.get("sensitivity_heatmap"),
        impacts=detail.get("assumption_impacts"),
        scenarios=detail.get("scenarios"),
        assumptions=assumptions_rows, interview_findings=findings,
        risks=risks, normalisations=normalisations, documents=documents,
        narrative=narrative, fmt=format_inr,
        generated_on=datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        analyst=analyst,
    )

    report = Report(case_id=case.id, template=template,
                    title=f"{case.company.name if case.company else 'Company'} — "
                          f"Comprehensive Valuation Report",
                    options=options, status="generating")
    db.add(report)
    db.flush()

    out_dir = Path(settings.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"report_{report.id}.html"
    html_path.write_text(html, encoding="utf-8")
    report.html_path = str(html_path)

    pdf_path = out_dir / f"report_{report.id}.pdf"
    if render_pdf(html, pdf_path):
        report.pdf_path = str(pdf_path)
    report.status = "generated"
    db.add(AuditLog(case_id=case.id, actor=analyst, action="report_generated",
                    detail={"report_id": report.id, "template": template}))
    db.commit()
    db.refresh(report)
    return report


def render_pdf(html: str, out_path: Path) -> bool:
    """Try WeasyPrint first (best CSS), then xhtml2pdf. Returns success."""
    try:
        from weasyprint import HTML  # type: ignore

        HTML(string=html).write_pdf(str(out_path))
        return True
    except Exception:
        pass
    try:
        from xhtml2pdf import pisa  # type: ignore

        # xhtml2pdf's built-in Helvetica lacks the ₹ glyph — use Rs. in PDF output
        pdf_html = html.replace("₹", "Rs.")
        with open(out_path, "wb") as f:
            status = pisa.CreatePDF(pdf_html, dest=f, encoding="utf-8")
        if status.err:
            out_path.unlink(missing_ok=True)
            return False
        return True
    except Exception:
        log.exception("PDF rendering failed; HTML report remains available")
        out_path.unlink(missing_ok=True)
        return False
