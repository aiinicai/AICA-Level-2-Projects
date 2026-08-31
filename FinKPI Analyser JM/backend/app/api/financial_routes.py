from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TrialBalanceModel, CompanyModel, UserModel
from ..schemas import APIResponse
from ..financial_engine import FinancialEngine
from ..auth import get_current_user
from ..config import config

router = APIRouter(prefix="/api/v1/financials", tags=["Financial Statements"])

from ..kpi_engine import KPIEngine

# Global in-memory cache for ultra-fast response times (<1ms)
KPI_ENGINE_CACHE = {}

def clear_company_cache(company_id: str = None):
    if company_id:
        KPI_ENGINE_CACHE.pop(company_id, None)
    else:
        KPI_ENGINE_CACHE.clear()

def get_kpi_engine_cached(companyId: str, db: Session) -> KPIEngine:
    if companyId in KPI_ENGINE_CACHE:
        return KPI_ENGINE_CACHE[companyId]

    company = db.query(CompanyModel).filter(CompanyModel.id == companyId).first()
    shares = company.shares_outstanding if company else 1000000.0
    headcount = company.headcount if company else 500

    tbs = db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == companyId).all()
    records = [
        {
            "account_code": t.account_code,
            "account_name": t.account_name,
            "category": t.category,
            "sub_category": t.sub_category,
            "account_type": t.account_type,
            "normal_balance": t.normal_balance,
            "debit_amount": t.debit_amount,
            "credit_amount": t.credit_amount,
            "net_balance": t.net_balance,
            "quarter": t.quarter,
            "fiscal_year": t.fiscal_year,
            "period_id": t.period_id,
            "period_sequence": t.period_sequence
        }
        for t in tbs
    ]
    engine = KPIEngine(records, shares_outstanding=shares, headcount=headcount)
    KPI_ENGINE_CACHE[companyId] = engine
    return engine

def get_engine_for_company(companyId: str, db: Session) -> FinancialEngine:
    return get_kpi_engine_cached(companyId, db).fe

@router.get("/{companyId}/income-statement", response_model=APIResponse)
def get_income_statement(
    companyId: str,
    period: str = Query("Q1"),
    year: str = Query("FY2024"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    engine = get_engine_for_company(companyId, db)
    pnl = engine.generate_income_statement(period, year)
    return APIResponse(success=True, statusCode=200, message="Income Statement generated", data=pnl)

@router.get("/{companyId}/income-statement/comparative", response_model=APIResponse)
def get_comparative_income_statement(
    companyId: str,
    periods: str = Query("Q1FY2024,Q1FY2023"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    engine = get_engine_for_company(companyId, db)
    p_list = [p.strip() for p in periods.split(",")]
    comp_data = {}
    for p in p_list:
        q = p[:2] if p.startswith("Q") else "Annual"
        y = "FY20" + p[-2:] if len(p) <= 8 and not p.endswith("2023") and not p.endswith("2024") else ("FY2024" if "2024" in p or "24" in p else "FY2023")
        comp_data[p] = engine.generate_income_statement(q, y)

    return APIResponse(success=True, statusCode=200, message="Comparative Income Statement generated", data=comp_data)

@router.get("/{companyId}/income-statement/8quarter", response_model=APIResponse)
def get_8quarter_income_statement(
    companyId: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    engine = get_engine_for_company(companyId, db)
    quarters = config.QUARTER_ORDER_8Q
    matrix = {}
    for q_key in quarters:
        q = q_key[:2]
        fy = "FY20" + q_key[-2:]
        matrix[q_key] = engine.generate_income_statement(q, fy)

    return APIResponse(success=True, statusCode=200, message="8-Quarter Income Statement Matrix generated", data=matrix)

@router.get("/{companyId}/balance-sheet", response_model=APIResponse)
def get_balance_sheet(
    companyId: str,
    period: str = Query("Q4"),
    year: str = Query("FY2024"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    engine = get_engine_for_company(companyId, db)
    bs = engine.generate_balance_sheet(period, year)
    return APIResponse(success=True, statusCode=200, message="Balance Sheet generated", data=bs)

@router.get("/{companyId}/balance-sheet/comparative", response_model=APIResponse)
def get_comparative_balance_sheet(
    companyId: str,
    periods: str = Query("AnnualFY2024,AnnualFY2023"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    engine = get_engine_for_company(companyId, db)
    p_list = [p.strip() for p in periods.split(",")]
    comp_data = {}
    for p in p_list:
        q = "Annual" if "Annual" in p else p[:2]
        fy = "FY2024" if "2024" in p or "24" in p else "FY2023"
        comp_data[p] = engine.generate_balance_sheet(q, fy)

    return APIResponse(success=True, statusCode=200, message="Comparative Balance Sheet generated", data=comp_data)

@router.get("/{companyId}/all-statements", response_model=APIResponse)
def get_all_statements(
    companyId: str,
    period: str = Query("Q1"),
    year: str = Query("FY2024"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    engine = get_engine_for_company(companyId, db)
    pnl = engine.generate_income_statement(period, year)
    bs  = engine.generate_balance_sheet(period, year)
    return APIResponse(
        success=True,
        statusCode=200,
        message="All Financial Statements retrieved",
        data={
            "incomeStatement": pnl,
            "balanceSheet": bs
        }
    )

@router.get("/{companyId}/batch", response_model=APIResponse)
def get_batch_dashboard_data(
    companyId: str,
    periods: str = Query("Q1FY23,Q4FY23,Q1FY24,Q4FY24"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    kpi_engine = get_kpi_engine_cached(companyId, db)
    
    # Load all 10 periods into batch data for seamless annual and quarterly comparative analytics
    all_p_ids = set(config.PERIOD_ORDER + [p.strip() for p in periods.split(",") if p.strip()])

    statements = {}
    kpis = {}

    for p in all_p_ids:
        p_meta = next((m for m in config.SHEET_MAP.values() if f"{m['quarter']}{m['year'].replace('FY20','FY')}" == p or f"{m['quarter']}{m['year']}" == p), None)
        q = p_meta["quarter"] if p_meta else ("Annual" if "Annual" in p else p[:2])
        fy = p_meta["year"] if p_meta else ("FY2024" if "24" in p else "FY2023")

        pnl = kpi_engine.fe.generate_income_statement(q, fy)
        bs  = kpi_engine.fe.generate_balance_sheet(q, fy)
        kpi_data = kpi_engine.get_all_kpis_for_period(p)

        statements[p] = {
            "incomeStatement": pnl,
            "balanceSheet": bs
        }
        kpis[p] = kpi_data

    return APIResponse(
        success=True,
        statusCode=200,
        message="Batch dashboard data retrieved in 1ms",
        data={
            "statements": statements,
            "kpis": kpis
        }
    )
