"""Builds ValuationInputs from stored case data, runs the engine, persists runs."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...models import (
    AuditLog, FinancialLineItem, InterviewQuestion, InterviewSession,
    NormalisationAdjustment, RuleTrigger, ValuationAssumption, ValuationCase,
    ValuationMethodResult, ValuationRun,
)
from ..financial.canonical import ALL_METRICS
from ..financial.store import compute_case_analytics, load_normalised_data
from .engine import (
    DEFAULT_WEIGHTS, ValuationInputs, assumption_impacts, run_scenarios,
    run_valuation, sensitivity_heatmap, tornado_analysis,
)
from .scoring import ESSENTIAL_ASSUMPTIONS, confidence_score, readiness_score

DEFAULT_ASSUMPTIONS: dict[str, float] = {
    "revenue_growth": 0.16,
    "ebitda_margin": 0.18,
    "wacc": 0.12,
    "terminal_growth": 0.03,
    "tax_rate": 0.25,
    "ev_ebitda_multiple": 8.5,
    "capex_pct": None,  # derived from history when None
    "nwc_pct": None,
    "depreciation_pct": None,
}


def get_assumptions(db: Session, case_id: str) -> dict[str, float | None]:
    rows = db.execute(
        select(ValuationAssumption).where(ValuationAssumption.case_id == case_id)
    ).scalars().all()
    out: dict[str, float | None] = dict(DEFAULT_ASSUMPTIONS)
    for r in rows:
        if r.status == "accepted" and r.value is not None:
            out[r.key] = r.value
    return out


def build_inputs(db: Session, case: ValuationCase,
                 overrides: dict[str, float] | None = None) -> ValuationInputs:
    """Assemble engine inputs from locked financials + accepted assumptions."""
    data, periods = load_normalised_data(db, case.id)
    if not periods:
        raise ValueError("No financial periods available — upload and approve financials first")
    latest = data.get(periods[-1], {})
    analytics = compute_case_analytics(db, case.id)
    summary = analytics["summary"]
    latest_ratios = analytics["per_period"].get(periods[-1], {})

    a = get_assumptions(db, case.id)
    if overrides:
        a.update({k: v for k, v in overrides.items() if v is not None})

    revenue = latest.get("revenue")
    if not revenue:
        raise ValueError("Latest revenue is missing — cannot value the company")

    ebitda_margin = a.get("ebitda_margin")
    if ebitda_margin is None:
        ebitda_margin = latest_ratios.get("ebitda_margin") or 0.15

    dep_pct = a.get("depreciation_pct")
    if dep_pct is None:
        dep = latest.get("depreciation")
        dep_pct = (dep / revenue) if dep else 0.03

    capex_pct = a.get("capex_pct")
    if capex_pct is None:
        capex = latest.get("capex")
        capex_pct = abs(capex) / revenue if capex else 0.04

    nwc_pct = a.get("nwc_pct")
    if nwc_pct is None:
        nwc = ((latest.get("receivables") or 0) + (latest.get("inventory") or 0)
               - (latest.get("trade_payables") or 0))
        nwc_pct = max(nwc / revenue, 0.0) if revenue else 0.10

    debt = (latest.get("long_term_borrowings") or 0) + (latest.get("short_term_borrowings") or 0)

    weights_row = db.execute(
        select(ValuationAssumption).where(
            ValuationAssumption.case_id == case.id,
            ValuationAssumption.key.in_(["weight_dcf", "weight_market_multiple", "weight_adjusted_nav"]),
        )
    ).scalars().all()
    weights = dict(DEFAULT_WEIGHTS)
    for w in weights_row:
        if w.value is not None:
            weights[w.key.removeprefix("weight_")] = w.value

    return ValuationInputs(
        base_revenue=revenue,
        base_ebitda_margin=float(ebitda_margin),
        base_depreciation_pct=float(dep_pct),
        base_capex_pct=float(capex_pct),
        base_nwc_pct=float(nwc_pct),
        tax_rate=float(a.get("tax_rate") or 0.25),
        revenue_growth=float(a.get("revenue_growth") or 0.10),
        wacc=float(a.get("wacc") or 0.12),
        terminal_growth=float(a.get("terminal_growth") or 0.03),
        total_debt=debt,
        cash=latest.get("cash") or 0.0,
        shares_outstanding=case.total_shares or 0.0,
        ev_ebitda_multiple=a.get("ev_ebitda_multiple"),
        base_pat=latest.get("pat"),
        net_worth=latest.get("net_worth"),
        nav_adjustments=_load_nav_adjustments(db, case.id),
        method_weights=weights,
    )


def _load_nav_adjustments(db: Session, case_id: str) -> list[dict]:
    rows = db.execute(
        select(NormalisationAdjustment).where(
            NormalisationAdjustment.case_id == case_id,
            NormalisationAdjustment.kind == "nav_adjustment",
            NormalisationAdjustment.status == "approved",
        )
    ).scalars().all()
    return [{"item": r.metric, "book_value": r.reported_value,
             "adjusted_value": r.reported_value + r.adjustment, "note": r.reason}
            for r in rows]


def compute_readiness(db: Session, case: ValuationCase) -> dict[str, Any]:
    items = db.execute(
        select(FinancialLineItem).where(FinancialLineItem.case_id == case.id)
    ).scalars().all()
    core_metrics = {"revenue", "ebitda", "depreciation", "pbt", "tax", "pat", "net_worth",
                    "total_assets", "cash", "cfo", "receivables", "inventory", "trade_payables"}
    periods = {i.period_label for i in items}
    if periods and items:
        have = {(i.period_label, i.metric) for i in items if
                (i.approved_value is not None or i.python_value is not None)}
        coverage = len([1 for p in periods for m in core_metrics if (p, m) in have]) / (
            len(periods) * len(core_metrics))
        verified = len([i for i in items if i.verification_status == "verified"]) / len(items)
    else:
        coverage, verified = 0.0, 0.0

    a = get_assumptions(db, case.id)
    present = len([k for k in ESSENTIAL_ASSUMPTIONS if a.get(k) is not None])

    session = db.execute(
        select(InterviewSession).where(InterviewSession.case_id == case.id)
        .order_by(InterviewSession.started_at.desc())
    ).scalars().first()
    answered, planned, critical_open = 0, 0, 0
    if session:
        qs = db.execute(
            select(InterviewQuestion).where(InterviewQuestion.session_id == session.id)
        ).scalars().all()
        planned = len(qs)
        answered = len([q for q in qs if q.status == "answered"])
        critical_open = len([q for q in qs if q.priority in ("critical", "high")
                             and q.status not in ("answered", "skipped")])

    triggers = db.execute(
        select(RuleTrigger).where(RuleTrigger.case_id == case.id)
    ).scalars().all()
    risks_total = max(len(triggers), 1)
    risks_covered = len([t for t in triggers if t.status == "addressed"]) or (
        risks_total if not triggers else 0)

    return readiness_score(coverage, verified, present, critical_open,
                           answered, planned, risks_covered, risks_total)


def calculate_and_persist(db: Session, case: ValuationCase, analyst: str = "Arjun Demo",
                          run_label: str = "Base Case") -> ValuationRun:
    """Full valuation run: engine + scenarios + sensitivity + scoring, persisted."""
    inp = build_inputs(db, case)
    result = run_valuation(inp)
    scenarios = run_scenarios(inp)
    heatmap = sensitivity_heatmap(inp)
    tornado = tornado_analysis(inp)
    impacts = assumption_impacts(inp)

    items = db.execute(
        select(FinancialLineItem).where(FinancialLineItem.case_id == case.id)
    ).scalars().all()
    verified_share = (len([i for i in items if i.verification_status == "verified"]) / len(items)
                      if items else 0.0)
    a = get_assumptions(db, case.id)
    present = len([k for k in ESSENTIAL_ASSUMPTIONS if a.get(k) is not None])
    pending_norm = db.execute(
        select(NormalisationAdjustment).where(
            NormalisationAdjustment.case_id == case.id,
            NormalisationAdjustment.status == "proposed",
        )
    ).scalars().all()

    method_evs = {m: r["enterprise_value"] for m, r in result["methods"].items()}
    terminal_share = result["methods"].get("dcf", {}).get("terminal_share_of_ev")
    conf = confidence_score(method_evs, verified_share, present, terminal_share,
                            normalisations_resolved=not pending_norm)
    readiness = compute_readiness(db, case)

    db.execute(update(ValuationRun).where(ValuationRun.case_id == case.id)
               .values(is_current=0))

    run = ValuationRun(
        case_id=case.id,
        run_label=run_label,
        assumptions={k: v for k, v in a.items() if v is not None},
        weights=result["weights"],
        enterprise_value=result["central_estimate_ev"],
        equity_value=result["central_estimate_equity"],
        central_estimate=result["central_estimate_ev"],
        range_low=result["range_low_ev"],
        range_high=result["range_high_ev"],
        per_share_value=result["per_share_value"],
        confidence_label=conf["label"],
        confidence_score=conf["score"],
        readiness_score=readiness["score"],
        analyst=analyst,
        methods_used=sorted(result["methods"], key=lambda m: -result["weights"].get(m, 0)),
        detail={
            "result": result,
            "scenarios": scenarios,
            "sensitivity_heatmap": heatmap,
            "tornado": tornado,
            "assumption_impacts": impacts,
            "confidence": conf,
            "readiness": readiness,
            "inputs": {
                "base_revenue": inp.base_revenue,
                "ebitda_margin": inp.base_ebitda_margin,
                "depreciation_pct": inp.base_depreciation_pct,
                "capex_pct": inp.base_capex_pct,
                "nwc_pct": inp.base_nwc_pct,
                "tax_rate": inp.tax_rate,
                "revenue_growth": inp.revenue_growth,
                "wacc": inp.wacc,
                "terminal_growth": inp.terminal_growth,
                "total_debt": inp.total_debt,
                "cash": inp.cash,
                "shares_outstanding": inp.shares_outstanding,
                "ev_ebitda_multiple": inp.ev_ebitda_multiple,
            },
        },
        is_current=1,
    )
    db.add(run)
    db.flush()

    for method, r in result["methods"].items():
        db.add(ValuationMethodResult(
            run_id=run.id, case_id=case.id, method=method,
            enterprise_value=r.get("enterprise_value"),
            equity_value=r.get("equity_value"),
            per_share_value=r.get("per_share_value"),
            weight=result["weights"].get(method, 0),
            key_driver=r.get("key_driver", ""),
            detail=r,
        ))

    case.status = "completed"
    db.add(AuditLog(case_id=case.id, actor=analyst, action="valuation_run",
                    detail={"run_id": run.id, "ev": result["central_estimate_ev"]}))
    db.commit()
    db.refresh(run)
    return run


def simulate(db: Session, case: ValuationCase, overrides: dict[str, float]) -> dict[str, Any]:
    """Deterministic what-if calculation. Never persisted, never calls the AI."""
    inp = build_inputs(db, case, overrides=overrides)
    result = run_valuation(inp)
    base_run = db.execute(
        select(ValuationRun).where(ValuationRun.case_id == case.id,
                                   ValuationRun.is_current == 1)
    ).scalars().first()
    base_ev = base_run.enterprise_value if base_run else None
    ev = result["central_estimate_ev"]
    return {
        "enterprise_value": ev,
        "equity_value": result["central_estimate_equity"],
        "per_share_value": result["per_share_value"],
        "range_low": result["range_low_ev"],
        "range_high": result["range_high_ev"],
        "methods": {m: {"enterprise_value": r["enterprise_value"],
                        "equity_value": r["equity_value"]}
                    for m, r in result["methods"].items()},
        "bridge": result["bridge"],
        "vs_current_pct": ((ev - base_ev) / base_ev) if base_ev else None,
        "tornado": tornado_analysis(inp),
        "assumption_impacts": assumption_impacts(inp),
        "scenarios": run_scenarios(inp),
    }
