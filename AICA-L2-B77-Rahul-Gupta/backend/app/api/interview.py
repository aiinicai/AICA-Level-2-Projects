"""Adaptive AI interview + assumptions + normalisations."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AuditLog, InterviewAnswer, InterviewQuestion, NormalisationAdjustment,
    RuleTrigger, ValuationAssumption, ValuationCase,
)
from ..schemas import (
    AssumptionsUpdate, InterviewAnswerRequest, NormalisationCreate,
    NormalisationDecision,
)
from ..services.financial.store import compute_case_analytics, load_financial_data
from ..services.interview.engine import (
    CATEGORY_LABELS, get_active_session, next_question, progress_by_category,
    start_interview, submit_answer,
)
from ..services.valuation.orchestrator import DEFAULT_ASSUMPTIONS, compute_readiness

router = APIRouter()


def _case_or_404(db: Session, case_id: str) -> ValuationCase:
    case = db.get(ValuationCase, case_id)
    if case is None:
        raise HTTPException(404, "Valuation case not found")
    return case


def _question_out(q: InterviewQuestion) -> dict:
    return {"id": q.id, "code": q.question_code, "category": q.category,
            "category_label": CATEGORY_LABELS.get(q.category, q.category.title()),
            "priority": q.priority, "reason": q.reason,
            "trigger_rule": q.trigger_rule, "question": q.question,
            "type": q.qtype, "options": q.options,
            "valuation_impact": q.valuation_impact, "status": q.status,
            "order_index": q.order_index}


@router.post("/api/valuations/{case_id}/interview/start")
def start(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    data, periods = load_financial_data(db, case_id)
    if not periods:
        raise HTTPException(409, "Approve financial data before starting the interview")
    session = start_interview(db, case)
    return {"session_id": session.id, "total_planned": session.total_planned}


def _financial_context(db: Session, case_id: str) -> dict:
    analytics = compute_case_analytics(db, case_id)
    data, periods = load_financial_data(db, case_id)
    s = analytics["summary"]
    latest = periods[-1] if periods else None
    return {
        "revenue_latest": data.get(latest, {}).get("revenue") if latest else None,
        "revenue_cagr": s.get("revenue_cagr"),
        "revenue_growth": s.get("latest_revenue_growth"),
        "ebitda_margin": s.get("latest_ebitda_margin"),
        "pat_latest": data.get(latest, {}).get("pat") if latest else None,
        "latest_period": latest,
    }


@router.get("/api/valuations/{case_id}/interview/state")
def state(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    session = get_active_session(db, case_id)
    if session is None:
        return {"session": None}
    qs = db.execute(select(InterviewQuestion).where(
        InterviewQuestion.session_id == session.id)
        .order_by(InterviewQuestion.order_index)).scalars().all()
    answers = db.execute(select(InterviewAnswer).where(
        InterviewAnswer.session_id == session.id)).scalars().all()
    answered = len([q for q in qs if q.status in ("answered", "skipped")])
    current = next_question(db, session) if session.status == "active" else None
    readiness = compute_readiness(db, case)
    interpretations = [a.ai_interpretation for a in answers if a.ai_interpretation]
    return {
        "session": {"id": session.id, "status": session.status,
                    "total": len(qs), "answered": answered},
        "current_question": _question_out(current) if current else None,
        "current_number": answered + 1 if current else answered,
        "categories": progress_by_category(db, session),
        "financial_context": _financial_context(db, case_id),
        "readiness": readiness,
        "interpretation_so_far": interpretations[-1] if interpretations else
            "Answers will be interpreted as the interview progresses.",
        "answers": [{"question_id": a.question_id,
                     "value": a.answer_value.get("value"),
                     "signal": a.signal, "interpretation": a.ai_interpretation}
                    for a in answers],
    }


@router.post("/api/valuations/{case_id}/interview/answer")
def answer(case_id: str, body: InterviewAnswerRequest, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    session = get_active_session(db, case_id)
    if session is None or session.status != "active":
        raise HTTPException(409, "No active interview session")
    q = db.get(InterviewQuestion, body.question_id)
    if q is None or q.session_id != session.id:
        raise HTTPException(404, "Question not found in active session")
    if q.status == "answered":
        raise HTTPException(409, "Question already answered")
    result = submit_answer(db, case, session, q, body.value, body.elaboration)
    return result


@router.post("/api/valuations/{case_id}/interview/skip")
def skip(case_id: str, body: dict, db: Session = Depends(get_db)):
    _case_or_404(db, case_id)
    session = get_active_session(db, case_id)
    if session is None:
        raise HTTPException(409, "No active interview session")
    q = db.get(InterviewQuestion, body.get("question_id", ""))
    if q is None or q.session_id != session.id:
        raise HTTPException(404, "Question not found")
    q.status = "skipped"
    remaining = db.execute(select(InterviewQuestion).where(
        InterviewQuestion.session_id == session.id,
        InterviewQuestion.status.in_(["pending", "asked"]))).scalars().all()
    if not remaining:
        session.status = "completed"
    db.commit()
    return {"ok": True, "session_status": session.status}


@router.get("/api/valuations/{case_id}/triggers")
def triggers(case_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(RuleTrigger).where(
        RuleTrigger.case_id == case_id)).scalars().all()
    return [{"rule_code": t.rule_code, "metric": t.metric,
             "observed_value": t.observed_value, "threshold": t.threshold,
             "severity": t.severity, "action": t.action, "message": t.message,
             "status": t.status} for t in rows]


# ---------------------------------------------------------------------------
# Assumptions (human-in-the-loop)
# ---------------------------------------------------------------------------

ASSUMPTION_META = {
    "revenue_growth": {"label": "Revenue Growth (CAGR)", "kind": "pct", "min": 0.05, "max": 0.25},
    "ebitda_margin": {"label": "EBITDA Margin", "kind": "pct", "min": 0.05, "max": 0.30},
    "wacc": {"label": "WACC", "kind": "pct", "min": 0.06, "max": 0.16},
    "terminal_growth": {"label": "Terminal Growth Rate", "kind": "pct", "min": 0.0, "max": 0.06},
    "tax_rate": {"label": "Tax Rate", "kind": "pct", "min": 0.15, "max": 0.35},
    "ev_ebitda_multiple": {"label": "EV / EBITDA Multiple (Exit)", "kind": "x", "min": 6.0, "max": 16.0},
    "capex_pct": {"label": "Capex (% of Revenue)", "kind": "pct", "min": 0.0, "max": 0.15},
    "nwc_pct": {"label": "Net Working Capital (% of Revenue)", "kind": "pct", "min": 0.0, "max": 0.35},
    "depreciation_pct": {"label": "Depreciation (% of Revenue)", "kind": "pct", "min": 0.0, "max": 0.10},
    "weight_dcf": {"label": "DCF Weight", "kind": "pct", "min": 0, "max": 1},
    "weight_market_multiple": {"label": "Market Multiple Weight", "kind": "pct", "min": 0, "max": 1},
    "weight_adjusted_nav": {"label": "Adjusted NAV Weight", "kind": "pct", "min": 0, "max": 1},
}


@router.get("/api/valuations/{case_id}/assumptions")
def get_assumptions_api(case_id: str, db: Session = Depends(get_db)):
    _case_or_404(db, case_id)
    rows = {r.key: r for r in db.execute(select(ValuationAssumption).where(
        ValuationAssumption.case_id == case_id)).scalars()}
    out = []
    for key, meta in ASSUMPTION_META.items():
        row = rows.get(key)
        default = DEFAULT_ASSUMPTIONS.get(key)
        if key == "weight_dcf":
            default = 0.5
        elif key == "weight_market_multiple":
            default = 0.3
        elif key == "weight_adjusted_nav":
            default = 0.2
        out.append({
            "key": key, **meta,
            "value": row.value if row and row.value is not None else default,
            "source": row.source if row else "default",
            "status": row.status if row else "accepted",
            "ai_recommended_value": row.ai_recommended_value if row else None,
            "ai_reason": row.ai_reason if row else "",
        })
    return out


@router.put("/api/valuations/{case_id}/assumptions")
def put_assumptions(case_id: str, body: AssumptionsUpdate, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    weight_keys = {"weight_dcf", "weight_market_multiple", "weight_adjusted_nav"}
    new_weights = {k: v for k, v in body.values.items() if k in weight_keys and v is not None}
    if new_weights:
        existing = {r.key: (r.value or 0) for r in db.execute(
            select(ValuationAssumption).where(
                ValuationAssumption.case_id == case_id,
                ValuationAssumption.key.in_(weight_keys))).scalars()}
        merged = {"weight_dcf": 0.5, "weight_market_multiple": 0.3,
                  "weight_adjusted_nav": 0.2} | existing | new_weights
        total = sum(merged.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(422, f"Method weights must total 100% (got {total * 100:.0f}%)")

    for key, value in body.values.items():
        row = db.execute(select(ValuationAssumption).where(
            ValuationAssumption.case_id == case_id,
            ValuationAssumption.key == key)).scalars().first()
        if row is None:
            row = ValuationAssumption(case_id=case_id, key=key)
            db.add(row)
        row.value = value
        row.source = body.source
        row.status = "accepted"
    db.add(AuditLog(case_id=case_id, action="assumptions_updated",
                    detail={"keys": list(body.values.keys()), "source": body.source}))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Normalisation adjustments
# ---------------------------------------------------------------------------

def _norm_out(n: NormalisationAdjustment) -> dict:
    return {"id": n.id, "period_label": n.period_label, "metric": n.metric,
            "kind": n.kind, "reported_value": n.reported_value,
            "adjustment": n.adjustment,
            "normalised_value": n.reported_value + n.adjustment,
            "reason": n.reason, "source": n.source, "status": n.status,
            "approved_by": n.approved_by}


@router.get("/api/valuations/{case_id}/normalisations")
def list_normalisations(case_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(NormalisationAdjustment).where(
        NormalisationAdjustment.case_id == case_id)
        .order_by(NormalisationAdjustment.created_at)).scalars().all()
    return [_norm_out(n) for n in rows]


@router.post("/api/valuations/{case_id}/normalisations", status_code=201)
def create_normalisation(case_id: str, body: NormalisationCreate,
                         db: Session = Depends(get_db)):
    _case_or_404(db, case_id)
    data, _ = load_financial_data(db, case_id)
    reported = data.get(body.period_label, {}).get(body.metric, 0.0)
    n = NormalisationAdjustment(
        case_id=case_id, period_label=body.period_label, metric=body.metric,
        kind=body.kind, reported_value=reported, adjustment=body.adjustment,
        reason=body.reason, source="analyst", status="proposed")
    db.add(n)
    db.commit()
    return _norm_out(n)


@router.post("/api/normalisations/{norm_id}/decision")
def decide_normalisation(norm_id: str, body: NormalisationDecision,
                         db: Session = Depends(get_db)):
    n = db.get(NormalisationAdjustment, norm_id)
    if n is None:
        raise HTTPException(404, "Adjustment not found")
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be approve or reject")
    if body.adjustment is not None:
        n.adjustment = body.adjustment
    if body.reason:
        n.reason = body.reason
    n.status = "approved" if body.action == "approve" else "rejected"
    n.approved_by = "Arjun Demo"
    db.add(AuditLog(case_id=n.case_id, action=f"normalisation_{n.status}",
                    detail={"id": n.id, "metric": n.metric, "adjustment": n.adjustment}))
    db.commit()
    return _norm_out(n)
