"""Valuation engine endpoints: calculate, simulate, runs, scenarios, insights, reports."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AIInsight, Report, ScenarioRun, ValuationCase, ValuationMethodResult,
    ValuationRun,
)
from ..schemas import ReportCreate, ScenarioSaveRequest, SimulateRequest
from ..services.financial.store import compute_case_analytics, persist_ratios
from ..services.insights import refresh_insights
from ..services.reporting.generator import generate_report
from ..services.valuation.orchestrator import (
    build_inputs, calculate_and_persist, compute_readiness, simulate,
)
from ..services.valuation.engine import run_valuation, scenario_inputs

router = APIRouter()


def _case_or_404(db: Session, case_id: str) -> ValuationCase:
    case = db.get(ValuationCase, case_id)
    if case is None:
        raise HTTPException(404, "Valuation case not found")
    return case


def _run_out(db: Session, run: ValuationRun, full: bool = False) -> dict:
    methods = db.execute(select(ValuationMethodResult).where(
        ValuationMethodResult.run_id == run.id)).scalars().all()
    out = {
        "id": run.id, "run_label": run.run_label,
        "enterprise_value": run.enterprise_value,
        "equity_value": run.equity_value,
        "central_estimate": run.central_estimate,
        "range_low": run.range_low, "range_high": run.range_high,
        "per_share_value": run.per_share_value,
        "confidence_label": run.confidence_label,
        "confidence_score": run.confidence_score,
        "readiness_score": run.readiness_score,
        "assumptions": run.assumptions, "weights": run.weights,
        "analyst": run.analyst, "methods_used": run.methods_used,
        "is_current": bool(run.is_current),
        "created_at": run.created_at.isoformat(),
        "methods": {m.method: {
            "enterprise_value": m.enterprise_value,
            "equity_value": m.equity_value,
            "per_share_value": m.per_share_value,
            "weight": m.weight, "key_driver": m.key_driver,
        } for m in methods},
    }
    if full:
        out["detail"] = run.detail
    return out


@router.post("/api/valuations/{case_id}/calculate")
def calculate(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    try:
        run = calculate_and_persist(db, case)
    except ValueError as e:
        raise HTTPException(422, str(e))
    analytics = compute_case_analytics(db, case_id)
    persist_ratios(db, case_id, analytics)
    refresh_insights(db, case, use_ai=False)  # engine insights always fresh
    return _run_out(db, run, full=True)


@router.get("/api/valuations/{case_id}/valuation")
def current_valuation(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    run = db.execute(select(ValuationRun).where(
        ValuationRun.case_id == case_id, ValuationRun.is_current == 1)).scalars().first()
    if run is None:
        return {"run": None, "readiness": compute_readiness(db, case)}
    return {"run": _run_out(db, run, full=True),
            "readiness": compute_readiness(db, case)}


@router.get("/api/valuations/{case_id}/runs")
def list_runs(case_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(ValuationRun).where(ValuationRun.case_id == case_id)
                      .order_by(ValuationRun.created_at.desc()).limit(20)).scalars().all()
    return [_run_out(db, r) for r in rows]


@router.post("/api/valuations/{case_id}/simulate")
def simulate_api(case_id: str, body: SimulateRequest, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    try:
        return simulate(db, case, body.overrides)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/api/valuations/{case_id}/analytics")
def analytics_api(case_id: str, db: Session = Depends(get_db)):
    _case_or_404(db, case_id)
    return compute_case_analytics(db, case_id)


# -- scenarios ---------------------------------------------------------------

@router.post("/api/valuations/{case_id}/scenarios/save", status_code=201)
def save_scenario(case_id: str, body: ScenarioSaveRequest, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    try:
        result = simulate(db, case, body.assumptions)
    except ValueError as e:
        raise HTTPException(422, str(e))
    row = ScenarioRun(case_id=case_id, name=body.name, assumptions=body.assumptions,
                      enterprise_value=result["enterprise_value"],
                      equity_value=result["equity_value"],
                      vs_base_pct=result.get("vs_current_pct"))
    db.add(row)
    db.commit()
    return {"id": row.id, "name": row.name,
            "enterprise_value": row.enterprise_value,
            "equity_value": row.equity_value, "vs_base_pct": row.vs_base_pct}


@router.get("/api/valuations/{case_id}/scenarios")
def list_scenarios(case_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(ScenarioRun).where(ScenarioRun.case_id == case_id)
                      .order_by(ScenarioRun.created_at.desc())).scalars().all()
    return [{"id": r.id, "name": r.name, "assumptions": r.assumptions,
             "enterprise_value": r.enterprise_value, "equity_value": r.equity_value,
             "vs_base_pct": r.vs_base_pct,
             "created_at": r.created_at.isoformat()} for r in rows]


# -- insights ----------------------------------------------------------------

@router.get("/api/valuations/{case_id}/insights")
def get_insights(case_id: str, db: Session = Depends(get_db)):
    _case_or_404(db, case_id)
    rows = db.execute(select(AIInsight).where(AIInsight.case_id == case_id)
                      .order_by(AIInsight.created_at)).scalars().all()
    return [{"id": i.id, "section": i.section, "title": i.title, "body": i.body,
             "severity": i.severity, "source": i.source, "data": i.data} for i in rows]


@router.post("/api/valuations/{case_id}/insights/refresh")
def refresh_insights_api(case_id: str, body: dict | None = None,
                         db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    use_ai = bool((body or {}).get("use_ai", True))
    rows = refresh_insights(db, case, use_ai=use_ai)
    return {"count": len(rows)}


# -- reports -----------------------------------------------------------------

@router.post("/api/valuations/{case_id}/reports", status_code=201)
def create_report(case_id: str, body: ReportCreate, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    try:
        report = generate_report(db, case, template=body.template, options=body.options)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return _report_out(report)


def _report_out(r: Report) -> dict:
    return {"id": r.id, "case_id": r.case_id, "template": r.template,
            "title": r.title, "status": r.status,
            "has_pdf": bool(r.pdf_path and Path(r.pdf_path).exists()),
            "has_html": bool(r.html_path and Path(r.html_path).exists()),
            "created_at": r.created_at.isoformat()}


@router.get("/api/valuations/{case_id}/reports")
def list_reports(case_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(Report).where(Report.case_id == case_id)
                      .order_by(Report.created_at.desc())).scalars().all()
    return [_report_out(r) for r in rows]


@router.get("/api/reports/count")
def report_count(db: Session = Depends(get_db)):
    return {"count": len(db.execute(select(Report)).scalars().all())}


@router.get("/api/reports/{report_id}/download")
def download_report(report_id: str, format: str = "pdf", db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if r is None:
        raise HTTPException(404, "Report not found")
    if format == "pdf" and r.pdf_path and Path(r.pdf_path).exists():
        return FileResponse(r.pdf_path, media_type="application/pdf",
                            filename=f"{r.title or 'valuation-report'}.pdf")
    if r.html_path and Path(r.html_path).exists():
        return FileResponse(r.html_path, media_type="text/html",
                            filename=f"{r.title or 'valuation-report'}.html")
    raise HTTPException(404, "Report file not available")
