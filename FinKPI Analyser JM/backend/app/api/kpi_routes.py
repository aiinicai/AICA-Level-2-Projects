from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TrialBalanceModel, CompanyModel, UserModel
from ..schemas import APIResponse
from ..kpi_engine import KPIEngine
from ..auth import get_current_user
from ..config import config

router = APIRouter(prefix="/api/v1/kpi", tags=["KPI Engine"])

from .financial_routes import get_kpi_engine_cached

def get_kpi_engine_for_company(companyId: str, db: Session) -> KPIEngine:
    return get_kpi_engine_cached(companyId, db)

def format_period_key(period: str, year: str) -> str:
    p_clean = period.upper().strip()
    y_clean = year.upper().replace("FY20", "FY").strip()
    return f"{p_clean}{y_clean}"

@router.get("/{companyId}/profitability", response_model=APIResponse)
def get_profitability_kpi(companyId: str, period: str = Query("Q1"), year: str = Query("FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    p_key = format_period_key(period, year)
    all_kpis = engine.get_all_kpis_for_period(p_key)
    return APIResponse(success=True, statusCode=200, message="Profitability KPIs retrieved", data=all_kpis.get("profitability", {}))

@router.get("/{companyId}/liquidity", response_model=APIResponse)
def get_liquidity_kpi(companyId: str, period: str = Query("Q1"), year: str = Query("FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    p_key = format_period_key(period, year)
    all_kpis = engine.get_all_kpis_for_period(p_key)
    return APIResponse(success=True, statusCode=200, message="Liquidity KPIs retrieved", data=all_kpis.get("liquidity", {}))

@router.get("/{companyId}/solvency", response_model=APIResponse)
def get_solvency_kpi(companyId: str, period: str = Query("Q1"), year: str = Query("FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    p_key = format_period_key(period, year)
    all_kpis = engine.get_all_kpis_for_period(p_key)
    return APIResponse(success=True, statusCode=200, message="Solvency KPIs retrieved", data=all_kpis.get("solvency", {}))

@router.get("/{companyId}/efficiency", response_model=APIResponse)
def get_efficiency_kpi(companyId: str, period: str = Query("Q1"), year: str = Query("FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    p_key = format_period_key(period, year)
    all_kpis = engine.get_all_kpis_for_period(p_key)
    return APIResponse(success=True, statusCode=200, message="Efficiency KPIs retrieved", data=all_kpis.get("efficiency", {}))

@router.get("/{companyId}/growth", response_model=APIResponse)
def get_growth_kpi(companyId: str, period: str = Query("Q1"), year: str = Query("FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    p_key = format_period_key(period, year)
    all_kpis = engine.get_all_kpis_for_period(p_key)
    return APIResponse(success=True, statusCode=200, message="Growth KPIs retrieved", data=all_kpis.get("growth", {}))

@router.get("/{companyId}/all", response_model=APIResponse)
def get_all_kpis(companyId: str, period: str = Query("Q1"), year: str = Query("FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    company = db.query(CompanyModel).filter(CompanyModel.id == companyId).first()
    engine = get_kpi_engine_for_company(companyId, db)
    p_key = format_period_key(period, year)
    all_kpis = engine.get_all_kpis_for_period(p_key)
    
    return APIResponse(
        success=True,
        statusCode=200,
        message="All KPIs retrieved successfully",
        data={
            "companyId": companyId,
            "companyName": company.company_name if company else "Company",
            "period": period,
            "fiscalYear": year,
            "currency": company.currency if company else "USD",
            "unit": company.currency_unit if company else "thousands",
            "kpi": all_kpis
        },
        meta={
            "periodsLoaded": config.PERIOD_ORDER
        }
    )

@router.get("/{companyId}/summary/8quarter", response_model=APIResponse)
def get_8quarter_kpi_summary(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    res = {}
    for q_key in config.QUARTER_ORDER_8Q:
        res[q_key] = engine.get_all_kpis_for_period(q_key)
    return APIResponse(success=True, statusCode=200, message="8-Quarter KPI Summary retrieved", data=res)

@router.get("/{companyId}/summary/annual", response_model=APIResponse)
def get_annual_kpi_summary(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    return APIResponse(
        success=True,
        statusCode=200,
        message="Annual KPI Comparison retrieved",
        data={
            "AnnualFY2023": engine.get_all_kpis_for_period("AnnualFY23"),
            "AnnualFY2024": engine.get_all_kpis_for_period("AnnualFY24")
        }
    )

@router.get("/{companyId}/scorecard", response_model=APIResponse)
def get_kpi_scorecard(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine_for_company(companyId, db)
    scorecard = {}
    for p_key in config.QUARTER_ORDER_8Q + ["AnnualFY23", "AnnualFY24"]:
        kpis = engine.get_all_kpis_for_period(p_key)
        total_metrics = 0
        green_count = 0
        amber_count = 0
        red_count = 0
        
        for cat, items in kpis.items():
            for k, data in items.items():
                total_metrics += 1
                rag = data.get("rag_status", "GREEN")
                if rag == "GREEN": green_count += 1
                elif rag == "AMBER": amber_count += 1
                else: red_count += 1

        scorecard[p_key] = {
            "total_metrics": total_metrics,
            "green": green_count,
            "amber": amber_count,
            "red": red_count,
            "health_score_pct": round((green_count + 0.5 * amber_count) / total_metrics * 100.0, 1) if total_metrics > 0 else 100.0
        }

    return APIResponse(success=True, statusCode=200, message="KPI Scorecard with RAG status retrieved", data=scorecard)
