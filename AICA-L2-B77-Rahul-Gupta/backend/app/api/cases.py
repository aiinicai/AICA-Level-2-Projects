"""Companies, valuation cases, dashboard aggregates, audit log."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AuditLog, Company, FinancialLineItem, User, ValuationCase,
    ValuationMethodResult, ValuationRun,
)
from ..schemas import ValuationCaseCreate
from ..services.valuation.orchestrator import compute_readiness

router = APIRouter()


def get_demo_user(db: Session) -> User:
    user = db.execute(select(User)).scalars().first()
    if user is None:
        user = User(name="Arjun Demo", role="Analyst", email="arjun.demo@companyval.ai")
        db.add(user)
        db.commit()
    return user


@router.get("/api/auth/me")
def me(db: Session = Depends(get_db)):
    u = get_demo_user(db)
    return {"id": u.id, "name": u.name, "role": u.role, "email": u.email,
            "timezone": u.timezone, "date_format": u.date_format,
            "number_format": u.number_format}


@router.get("/api/companies")
def list_companies(db: Session = Depends(get_db)):
    rows = db.execute(select(Company).order_by(Company.created_at)).scalars().all()
    return [{"id": c.id, "name": c.name, "industry": c.industry,
             "entity_type": c.entity_type, "country": c.country} for c in rows]


def _case_summary(db: Session, case: ValuationCase) -> dict:
    run = db.execute(select(ValuationRun).where(
        ValuationRun.case_id == case.id, ValuationRun.is_current == 1)).scalars().first()
    methods = []
    if run:
        # ordered by weight (highest first) so the primary method leads
        methods = run.methods_used or [m.method for m in db.execute(
            select(ValuationMethodResult).where(
                ValuationMethodResult.run_id == run.id)).scalars()]
    return {
        "id": case.id,
        "company_id": case.company_id,
        "company_name": case.company.name if case.company else "",
        "industry": case.company.industry if case.company else "",
        "entity_type": case.company.entity_type if case.company else "",
        "country": case.company.country if case.company else "",
        "valuation_date": case.valuation_date,
        "currency": case.currency,
        "units": case.units,
        "purpose": case.purpose,
        "promoter_holding_pct": case.promoter_holding_pct,
        "total_shares": case.total_shares,
        "notes": case.notes,
        "status": case.status,
        "financials_locked": bool(case.financials_locked),
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "current_run": ({
            "id": run.id,
            "enterprise_value": run.enterprise_value,
            "equity_value": run.equity_value,
            "central_estimate": run.central_estimate,
            "range_low": run.range_low,
            "range_high": run.range_high,
            "per_share_value": run.per_share_value,
            "confidence_label": run.confidence_label,
            "confidence_score": run.confidence_score,
            "readiness_score": run.readiness_score,
            "methods": methods,
            "created_at": run.created_at.isoformat(),
        } if run else None),
    }


@router.get("/api/valuations")
def list_cases(db: Session = Depends(get_db)):
    rows = db.execute(select(ValuationCase).order_by(
        ValuationCase.created_at)).scalars().all()
    return [_case_summary(db, c) for c in rows]


@router.post("/api/valuations", status_code=201)
def create_case(body: ValuationCaseCreate, db: Session = Depends(get_db)):
    user = get_demo_user(db)
    company = db.execute(select(Company).where(
        Company.name == body.company_name)).scalars().first()
    if company is None:
        company = Company(name=body.company_name, industry=body.industry,
                          entity_type=body.entity_type, country=body.country)
        db.add(company)
        db.flush()
    case = ValuationCase(
        company_id=company.id, created_by=user.id,
        valuation_date=body.valuation_date, currency=body.currency,
        units=body.units, purpose=body.purpose,
        promoter_holding_pct=body.promoter_holding_pct,
        total_shares=body.total_shares, notes=body.notes,
        status="documents",
    )
    db.add(case)
    db.flush()
    db.add(AuditLog(case_id=case.id, actor=user.name, action="case_created",
                    detail={"company": company.name, "purpose": body.purpose}))
    db.commit()
    return _case_summary(db, case)


@router.get("/api/valuations/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.get(ValuationCase, case_id)
    if case is None:
        raise HTTPException(404, "Valuation case not found")
    out = _case_summary(db, case)
    out["readiness"] = compute_readiness(db, case)
    return out


@router.get("/api/valuations/{case_id}/audit")
def get_audit(case_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(AuditLog).where(AuditLog.case_id == case_id)
                      .order_by(AuditLog.created_at.desc()).limit(100)).scalars().all()
    return [{"id": a.id, "actor": a.actor, "action": a.action,
             "detail": a.detail, "created_at": a.created_at.isoformat()} for a in rows]


@router.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    cases = db.execute(select(ValuationCase)).scalars().all()
    summaries = [_case_summary(db, c) for c in cases]
    completed = [s for s in summaries if s["status"] == "completed"]
    in_progress = [s for s in summaries if s["status"] != "completed"]
    valued = [s for s in summaries if s["current_run"]]
    avg_val = (sum(s["current_run"]["enterprise_value"] for s in valued) / len(valued)
               if valued else None)

    runs = db.execute(select(ValuationRun).order_by(ValuationRun.created_at)).scalars().all()
    trend: dict[str, list[float]] = {}
    for r in runs:
        if r.enterprise_value is None:
            continue
        key = r.created_at.strftime("%b '%y")
        trend.setdefault(key, []).append(r.enterprise_value)
    trend_points = [{"month": k, "value": sum(v) / len(v)} for k, v in trend.items()]

    method_avgs: dict[str, list[float]] = {}
    for m in db.execute(select(ValuationMethodResult)).scalars():
        if m.enterprise_value is not None:
            method_avgs.setdefault(m.method, []).append(m.enterprise_value)
    method_comparison = [{"method": k, "value": sum(v) / len(v)}
                         for k, v in method_avgs.items()]

    # readiness of the most recently updated case with a run
    active = max(valued, key=lambda s: s["updated_at"] or "") if valued else None
    return {
        "total_cases": len(summaries),
        "completed": len(completed),
        "in_progress": len(in_progress),
        "avg_valuation": avg_val,
        "readiness": active["current_run"]["readiness_score"] if active else 0,
        "recent": sorted(summaries, key=lambda s: s["updated_at"] or "", reverse=True),
        "trend": trend_points,
        "method_comparison": method_comparison,
        "active_case_id": active["id"] if active else (summaries[0]["id"] if summaries else None),
    }
