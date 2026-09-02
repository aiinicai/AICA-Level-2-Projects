"""Adaptive AI interview engine.

Question planner = Verified financials + calculated ratios + triggered rules
+ previous answers + missing valuation inputs → next best question.
Deterministic plan; Gemini optionally re-drafts phrasing and interprets answers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import (
    AuditLog, InterviewAnswer, InterviewQuestion, InterviewSession,
    NormalisationAdjustment, RuleTrigger, ValuationCase,
)
from ...rules import evaluate_rules
from ..ai.provider import AIProviderError
from ..ai.service import get_provider, logged_call
from ..financial.numbers import parse_amount
from ..financial.store import compute_case_analytics, load_financial_data
from .bank import BASELINE_QUESTIONS, FOLLOW_UPS, TRIGGERED_QUESTIONS, score_to_priority

TARGET_QUESTIONS = 14  # 8–15 substantive questions for a normal case

CATEGORY_LABELS = {
    "business_overview": "Business Overview",
    "growth": "Growth Drivers",
    "profitability": "Profitability",
    "customers": "Customers",
    "working_capital": "Working Capital",
    "capital_structure": "Capital & Structure",
    "management": "Management",
    "business_risks": "Risk Factors",
    "litigation": "Risk Factors",
    "related_parties": "Related Parties",
    "forecast": "Forecast & Outlook",
    "normalisation": "Normalisation",
    "capex": "Capex",
    "competition": "Competition",
    "operations": "Operations",
    "financial_performance": "Financial Performance",
}


def _context_values(analytics: dict) -> dict[str, str]:
    s = analytics.get("summary", {})
    periods = analytics.get("periods", [])
    latest = analytics.get("per_period", {}).get(periods[-1], {}) if periods else {}
    fmt_pct = lambda v: f"{v * 100:.1f}%" if v is not None else "n/a"
    return {
        "latest_period": periods[-1] if periods else "the latest year",
        "revenue_growth_pct": fmt_pct(s.get("latest_revenue_growth")),
        "margin_change_pp": (f"{s['margin_change_pp'] * 100:+.1f}"
                             if s.get("margin_change_pp") is not None else "n/a"),
        "cfo_pat_ratio": (f"{latest['cfo_pat']:.2f}×"
                          if latest.get("cfo_pat") is not None else "n/a"),
        "debt_equity": (f"{latest['debt_equity']:.2f}×"
                        if latest.get("debt_equity") is not None else "n/a"),
    }


def _fill(template: str, ctx: dict[str, str]) -> str:
    out = template
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", v)
    return out


def start_interview(db: Session, case: ValuationCase, facts: dict | None = None) -> InterviewSession:
    """Evaluate rules, build the deterministic question plan, persist session."""
    analytics = compute_case_analytics(db, case.id)
    triggers = evaluate_rules(analytics, facts)

    db.execute(delete(RuleTrigger).where(RuleTrigger.case_id == case.id))
    for t in triggers:
        db.add(RuleTrigger(case_id=case.id, **t))

    # close any prior active session
    for s in db.execute(select(InterviewSession).where(
            InterviewSession.case_id == case.id,
            InterviewSession.status == "active")).scalars():
        s.status = "superseded"

    session = InterviewSession(case_id=case.id, status="active")
    db.add(session)
    db.flush()

    ctx = _context_values(analytics)
    plan: list[dict] = []
    used_codes: set[str] = set()

    for t in triggers:
        tpl = TRIGGERED_QUESTIONS.get(t["rule_code"])
        if not tpl or tpl["code"] in used_codes:
            continue
        used_codes.add(tpl["code"])
        plan.append({**tpl, "trigger_rule": t["rule_code"]})

    for q in BASELINE_QUESTIONS:
        if len(plan) >= TARGET_QUESTIONS:
            break
        if q["code"] in used_codes:
            continue
        # skip growth baseline if a growth trigger already covers it
        if q["code"] == "GROWTH_001" and any(p.get("trigger_rule", "").startswith("REV_") for p in plan):
            continue
        used_codes.add(q["code"])
        plan.append({**q, "trigger_rule": ""})

    scored = []
    for q in plan:
        score, priority = score_to_priority(q["m"], q["v"], q["u"])
        scored.append((score, priority, q))
    scored.sort(key=lambda x: x[0], reverse=True)

    for idx, (score, priority, q) in enumerate(scored):
        db.add(InterviewQuestion(
            session_id=session.id, case_id=case.id,
            question_code=q["code"], category=q["category"],
            priority=priority, priority_score=score,
            reason=_fill(q.get("reason", ""), ctx),
            trigger_rule=q.get("trigger_rule", ""),
            question=_fill(q["question"], ctx),
            qtype=q["type"], options=q.get("options", []),
            valuation_impact=q.get("impact", []),
            order_index=idx, status="pending",
        ))
    session.total_planned = len(scored)
    case.status = "interview"
    db.add(AuditLog(case_id=case.id, action="interview_started",
                    detail={"session_id": session.id, "questions": len(scored),
                            "triggers": [t["rule_code"] for t in triggers]}))
    db.commit()
    db.refresh(session)
    return session


def get_active_session(db: Session, case_id: str) -> InterviewSession | None:
    return db.execute(select(InterviewSession).where(
        InterviewSession.case_id == case_id,
        InterviewSession.status.in_(["active", "completed"]),
    ).order_by(InterviewSession.started_at.desc())).scalars().first()


def next_question(db: Session, session: InterviewSession) -> InterviewQuestion | None:
    q = db.execute(select(InterviewQuestion).where(
        InterviewQuestion.session_id == session.id,
        InterviewQuestion.status.in_(["pending", "asked"]),
    ).order_by(InterviewQuestion.order_index)).scalars().first()
    if q and q.status == "pending":
        q.status = "asked"
        db.commit()
    return q


def _deterministic_interpretation(question: InterviewQuestion, value: str) -> tuple[str, str]:
    """Fallback signal classification when AI is unavailable."""
    positive_markers = ["strong growth", "improve", "long-term contract", "professional team",
                        "none material", "over 75%", "yes, regularly", "few competitors",
                        "maintenance only", "no, timing only"]
    negative_markers = ["declining", "material decline", "at risk", "over 50%",
                        "heavily promoter", "material matters", "disputed", "provision",
                        "unlikely to recur", "one-time order", "intense price",
                        "needing normalisation", "no"]
    v = value.lower()
    signal = "neutral"
    if any(mk in v for mk in positive_markers):
        signal = "positive"
    elif any(mk in v for mk in negative_markers):
        signal = "negative"
    interp = f"Answer noted for {CATEGORY_LABELS.get(question.category, question.category)}: {value}."
    return signal, interp


def submit_answer(db: Session, case: ValuationCase, session: InterviewSession,
                  question: InterviewQuestion, value: Any, elaboration: str = "") -> dict:
    """Store answer, interpret it, spawn deterministic follow-ups, propose
    normalisations where material."""
    value_str = str(value)
    provider = get_provider(db)
    signal, interpretation = _deterministic_interpretation(question, value_str)
    if provider:
        try:
            result = logged_call(db, "interpret_answer", case.id,
                                 provider.interpret_answer, question.question, value_str,
                                 {"category": question.category,
                                  "trigger_rule": question.trigger_rule,
                                  "elaboration": elaboration}, _provider=provider)
            signal = result.get("signal", signal)
            interpretation = result.get("interpretation", interpretation)
        except AIProviderError:
            pass  # deterministic fallback already set

    answer = InterviewAnswer(
        question_id=question.id, session_id=session.id, case_id=case.id,
        answer_value={"value": value}, elaboration=elaboration,
        ai_interpretation=interpretation, signal=signal,
    )
    db.add(answer)
    question.status = "answered"
    session.answered_count = (session.answered_count or 0) + 1

    if question.trigger_rule:
        trig = db.execute(select(RuleTrigger).where(
            RuleTrigger.case_id == case.id,
            RuleTrigger.rule_code == question.trigger_rule)).scalars().first()
        if trig:
            trig.status = "addressed"

    follow_ups = _spawn_follow_ups(db, case, session, question, value_str)
    _maybe_propose_normalisation(db, case, question, value_str)

    remaining = db.execute(select(InterviewQuestion).where(
        InterviewQuestion.session_id == session.id,
        InterviewQuestion.status.in_(["pending", "asked"]),
    )).scalars().all()
    if not remaining:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        case.status = "valuation"

    db.add(AuditLog(case_id=case.id, action="interview_answer",
                    detail={"question": question.question_code, "signal": signal}))
    db.commit()
    return {"signal": signal, "interpretation": interpretation,
            "follow_ups": follow_ups, "session_status": session.status}


def _spawn_follow_ups(db: Session, case: ValuationCase, session: InterviewSession,
                      question: InterviewQuestion, value: str) -> list[str]:
    spawned: list[str] = []
    existing = {q.question_code for q in db.execute(select(InterviewQuestion).where(
        InterviewQuestion.session_id == session.id)).scalars()}
    analytics = compute_case_analytics(db, case.id)
    ctx = _context_values(analytics)
    for fu in FOLLOW_UPS:
        if fu["parent"] != question.question_code:
            continue
        if fu["match"] != "*" and fu["match"].lower() not in value.lower():
            continue
        if fu["code"] in existing:
            continue
        score, priority = score_to_priority(fu["m"], fu["v"], fu["u"])
        db.add(InterviewQuestion(
            session_id=session.id, case_id=case.id,
            question_code=fu["code"], category=fu["category"],
            priority=priority, priority_score=score,
            reason=_fill(fu.get("reason", ""), ctx),
            trigger_rule=question.trigger_rule,
            question=_fill(fu["question"], ctx),
            qtype=fu["type"], options=fu.get("options", []),
            valuation_impact=fu.get("impact", []),
            order_index=question.order_index,  # asked immediately after parent
            status="pending",
        ))
        session.total_planned = (session.total_planned or 0) + 1
        spawned.append(fu["code"])
    return spawned


def _maybe_propose_normalisation(db: Session, case: ValuationCase,
                                 question: InterviewQuestion, value: str) -> None:
    """Deterministic normalisation proposals from interview facts."""
    if question.question_code == "GROWTH_004A":
        amount = parse_amount(value)
        if amount and amount > 0:
            data, periods = load_financial_data(db, case.id)
            latest = periods[-1] if periods else ""
            reported = data.get(latest, {}).get("revenue", 0)
            db.add(NormalisationAdjustment(
                case_id=case.id, period_label=latest, metric="revenue",
                kind="one_time_revenue", reported_value=reported,
                adjustment=-amount,
                reason="One-time order identified during AI interview — proposed removal "
                       "from the maintainable revenue base.",
                source="interview", status="proposed",
            ))
    if question.question_code == "NORM_002" and value.strip().lower().startswith("yes"):
        data, periods = load_financial_data(db, case.id)
        latest = periods[-1] if periods else ""
        ebitda = data.get(latest, {}).get("ebitda", 0)
        db.add(NormalisationAdjustment(
            case_id=case.id, period_label=latest, metric="ebitda",
            kind="exceptional_item", reported_value=ebitda, adjustment=0.0,
            reason="Management confirmed a material non-recurring item should be normalised. "
                   "Enter the adjustment amount before approval.",
            source="interview", status="proposed",
        ))


def progress_by_category(db: Session, session: InterviewSession) -> list[dict]:
    qs = db.execute(select(InterviewQuestion).where(
        InterviewQuestion.session_id == session.id)).scalars().all()
    cats: dict[str, dict] = {}
    for q in qs:
        label = CATEGORY_LABELS.get(q.category, q.category.title())
        c = cats.setdefault(label, {"category": label, "total": 0, "answered": 0})
        c["total"] += 1
        if q.status in ("answered", "skipped"):
            c["answered"] += 1
    return list(cats.values())
