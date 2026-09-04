"""AI Insights: explainability engine + optional Gemini narrative enrichment.

Every insight is grounded in stored engine data; the AI never invents numbers.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import (
    AIInsight, InterviewAnswer, InterviewQuestion, NormalisationAdjustment,
    RuleTrigger, ValuationCase, ValuationRun,
)
from .ai.provider import AIProviderError
from .ai.service import get_provider, logged_call
from .financial.numbers import format_inr
from .financial.store import compute_case_analytics

RISK_LABELS = {
    "REV_GROWTH_HIGH": ("Execution Risk", "Dependence on sustaining unusually high growth"),
    "REV_DECLINE": ("Market Risk", "Revenue decline needs a credible recovery path"),
    "EBITDA_MARGIN_SWING": ("Margin Risk", "Margin volatility across periods"),
    "CFO_PAT_LOW": ("Earnings Quality Risk", "Profits not fully converting to cash"),
    "DEBT_EQUITY_HIGH": ("Financial Risk", "Elevated leverage"),
    "RECEIVABLE_DAYS_UP": ("Working Capital Risk", "Collections slowing down"),
    "EXCEPTIONAL_ITEM": ("Earnings Quality Risk", "Material non-recurring items in earnings"),
    "CUSTOMER_CONCENTRATION": ("Concentration Risk", "Large single-customer dependence"),
    "REV_VOLATILITY": ("Market Risk", "Industry cyclicality and demand sensitivity"),
    "INTEREST_COVER_LOW": ("Financial Risk", "Thin interest coverage"),
}


def _pct(v: float | None, signed: bool = False) -> str:
    if v is None:
        return "n/a"
    return f"{v * 100:+.1f}%" if signed else f"{v * 100:.1f}%"


def build_engine_insights(db: Session, case: ValuationCase) -> list[dict[str, Any]]:
    """Deterministic insights derived straight from analytics + triggers + runs."""
    analytics = compute_case_analytics(db, case.id)
    s = analytics["summary"]
    periods = analytics["periods"]
    latest = analytics["per_period"].get(periods[-1], {}) if periods else {}
    run = db.execute(select(ValuationRun).where(
        ValuationRun.case_id == case.id, ValuationRun.is_current == 1)).scalars().first()
    triggers = db.execute(select(RuleTrigger).where(
        RuleTrigger.case_id == case.id)).scalars().all()

    out: list[dict[str, Any]] = []

    # positive drivers
    if (s.get("revenue_cagr") or 0) > 0.10:
        out.append(dict(section="positive_driver", title="Strong revenue trajectory",
                        body=f"Revenue compounded at {_pct(s['revenue_cagr'])} over the "
                             f"historical window, indicating sustained business momentum.",
                        severity="positive"))
    if (s.get("latest_ebitda_margin") or 0) > 0.15:
        out.append(dict(section="positive_driver", title="Healthy EBITDA margin",
                        body=f"EBITDA margin of {_pct(s['latest_ebitda_margin'])} in "
                             f"{periods[-1] if periods else 'the latest year'} is healthy and "
                             f"in line with quality mid-market businesses.",
                        severity="positive"))
    if (latest.get("cfo_pat") or 0) >= 0.8:
        out.append(dict(section="positive_driver", title="Good cash conversion",
                        body=f"CFO/PAT of {latest['cfo_pat']:.2f}× shows earnings are backed "
                             f"by operating cash flow.", severity="positive"))
    if latest.get("debt_equity") is not None and latest["debt_equity"] < 0.5:
        out.append(dict(section="positive_driver", title="Comfortable leverage",
                        body=f"Debt/Equity of {latest['debt_equity']:.2f}× leaves ample "
                             f"balance-sheet headroom.", severity="positive"))

    # risk flags from triggers
    for t in triggers:
        label, desc = RISK_LABELS.get(t.rule_code, ("Business Risk", t.message))
        sev = "high" if t.severity == "high" else "moderate"
        addressed = " Management response captured in the interview." if t.status == "addressed" else ""
        out.append(dict(section="risk_flag", title=label,
                        body=f"{desc}. {t.message}{addressed}",
                        severity=sev, data={"rule": t.rule_code,
                                            "observed": t.observed_value,
                                            "threshold": t.threshold}))

    # earnings quality
    cfo_pat = latest.get("cfo_pat")
    if cfo_pat is not None:
        grade = "strong" if cfo_pat >= 0.9 else ("acceptable" if cfo_pat >= 0.7 else "weak")
        out.append(dict(section="earnings_quality", title="Cash backing of earnings",
                        body=f"Operating cash flow covers {_pct(min(cfo_pat, 1.5))} of reported "
                             f"profit — {grade} earnings quality.",
                        severity="info" if grade != "weak" else "moderate"))
    pending = db.execute(select(NormalisationAdjustment).where(
        NormalisationAdjustment.case_id == case.id,
        NormalisationAdjustment.status == "proposed")).scalars().all()
    if pending:
        out.append(dict(section="earnings_quality", title="Normalisations pending review",
                        body=f"{len(pending)} proposed normalisation adjustment(s) await analyst "
                             f"approval and can move maintainable earnings.", severity="moderate"))

    # valuation explainability
    if run and run.detail:
        tornado = run.detail.get("tornado") or []
        if tornado:
            top = tornado[0]
            out.append(dict(section="explainability", title="Most sensitive assumption",
                            body=f"{top['label']} is the most sensitive assumption: a "
                                 f"±{top['delta'] * 100:.1f}{'pp' if top['delta'] < 1 else 'x'} swing moves enterprise value "
                                 f"between {format_inr(top['low'])} and {format_inr(top['high'])}.",
                            severity="info", data={"tornado_top": top["key"]}))
        impacts = run.detail.get("assumption_impacts") or []
        for imp in impacts[:3]:
            out.append(dict(section="assumption_review",
                            title=f"{imp['label']} {imp['change']}",
                            body=f"Changing {imp['label']} by {imp['change']} moves enterprise "
                                 f"value by {format_inr(imp['impact'])} ({_pct(imp['impact_pct'], signed=True)}).",
                            severity="info"))
        conf = run.detail.get("confidence", {})
        if conf:
            out.append(dict(section="business_quality", title=conf.get("label", ""),
                            body="Valuation confidence reflects method agreement "
                                 f"({conf['basis']['method_agreement']}%), data verification "
                                 f"({conf['basis']['data_verification']}%) and forecast completeness "
                                 f"({conf['basis']['forecast_completeness']}%).",
                            severity="info", data=conf))

    # next actions
    if pending:
        out.append(dict(section="next_action", title="Approve or reject proposed normalisations",
                        body="Normalisation proposals from the interview are awaiting a decision.",
                        severity="info"))
    open_triggers = [t for t in triggers if t.status == "open"]
    if open_triggers:
        out.append(dict(section="next_action", title="Complete the AI interview",
                        body=f"{len(open_triggers)} triggered rule(s) have not yet been addressed "
                             f"in the interview.", severity="info"))
    if not run:
        out.append(dict(section="next_action", title="Run the valuation engine",
                        body="Historical financials are ready — run the valuation to generate "
                             "DCF, market multiple and NAV results.", severity="info"))
    return out


def refresh_insights(db: Session, case: ValuationCase, use_ai: bool = True) -> list[AIInsight]:
    """Rebuild stored insights; optionally enrich with Gemini narrative."""
    engine_rows = build_engine_insights(db, case)
    db.execute(delete(AIInsight).where(AIInsight.case_id == case.id))
    for r in engine_rows:
        db.add(AIInsight(case_id=case.id, source="engine", **r))

    provider = get_provider(db) if use_ai else None
    if provider:
        analytics = compute_case_analytics(db, case.id)
        run = db.execute(select(ValuationRun).where(
            ValuationRun.case_id == case.id, ValuationRun.is_current == 1)).scalars().first()
        answers = db.execute(select(InterviewAnswer).where(
            InterviewAnswer.case_id == case.id)).scalars().all()
        questions = {q.id: q for q in db.execute(select(InterviewQuestion).where(
            InterviewQuestion.case_id == case.id)).scalars()}
        payload = {
            "company": case.company.name if case.company else "",
            "industry": case.company.industry if case.company else "",
            "analytics_summary": analytics["summary"],
            "latest_ratios": (analytics["per_period"].get(analytics["periods"][-1], {})
                              if analytics["periods"] else {}),
            "valuation": ({"enterprise_value": run.enterprise_value,
                           "equity_value": run.equity_value,
                           "range": [run.range_low, run.range_high],
                           "confidence": run.confidence_label} if run else None),
            "interview_findings": [
                {"question": questions[a.question_id].question if a.question_id in questions else "",
                 "answer": a.answer_value.get("value"), "signal": a.signal}
                for a in answers],
        }
        try:
            ai = logged_call(db, "insights", case.id, provider.generate_insights,
                             payload, _provider=provider)
            for ki in (ai.get("key_insights") or [])[:6]:
                db.add(AIInsight(case_id=case.id, source="ai", section="key_insight",
                                 title=str(ki.get("title", ""))[:200],
                                 body=str(ki.get("body", "")), severity="info"))
            bq = ai.get("business_quality") or {}
            if bq:
                db.add(AIInsight(case_id=case.id, source="ai", section="business_quality",
                                 title=f"Business Quality: {bq.get('grade', '')}",
                                 body=str(bq.get("summary", "")), severity="info"))
            for st in (ai.get("strengths") or [])[:5]:
                db.add(AIInsight(case_id=case.id, source="ai", section="strength",
                                 title="", body=str(st), severity="positive"))
            for na in (ai.get("next_actions") or [])[:5]:
                db.add(AIInsight(case_id=case.id, source="ai", section="next_action",
                                 title="", body=str(na), severity="info"))
            if ai.get("earnings_quality"):
                db.add(AIInsight(case_id=case.id, source="ai", section="earnings_quality",
                                 title="AI assessment", body=str(ai["earnings_quality"]),
                                 severity="info"))
        except AIProviderError:
            pass  # engine insights remain

    db.commit()
    return db.execute(select(AIInsight).where(AIInsight.case_id == case.id)).scalars().all()
