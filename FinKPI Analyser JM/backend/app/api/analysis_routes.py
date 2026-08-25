from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TrialBalanceModel, CompanyModel, UserModel
from ..schemas import APIResponse
from ..kpi_engine import KPIEngine
from ..financial_engine import FinancialEngine
from ..auth import get_current_user
from ..config import config

router = APIRouter(prefix="/api/v1/analysis", tags=["Comparative Analysis"])

def get_kpi_engine(companyId: str, db: Session) -> KPIEngine:
    company = db.query(CompanyModel).filter(CompanyModel.id == companyId).first()
    shares = company.shares_outstanding if company else 1000000.0
    headcount = company.headcount if company else 500
    tbs = db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == companyId).all()
    records = [
        {
            "account_code": t.account_code, "account_name": t.account_name, "category": t.category,
            "sub_category": t.sub_category, "account_type": t.account_type, "normal_balance": t.normal_balance,
            "debit_amount": t.debit_amount, "credit_amount": t.credit_amount, "net_balance": t.net_balance,
            "quarter": t.quarter, "fiscal_year": t.fiscal_year, "period_id": t.period_id, "period_sequence": t.period_sequence
        }
        for t in tbs
    ]
    return KPIEngine(records, shares_outstanding=shares, headcount=headcount)

@router.get("/{companyId}/qoq", response_model=APIResponse)
def get_qoq_analysis(companyId: str, year: str = Query("FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine(companyId, db)
    q_keys = ["Q1FY24", "Q2FY24", "Q3FY24", "Q4FY24"] if "24" in year else ["Q1FY23", "Q2FY23", "Q3FY23", "Q4FY23"]
    res = {k: engine.get_all_kpis_for_period(k) for k in q_keys}
    return APIResponse(success=True, statusCode=200, message="Sequential QoQ Analysis retrieved", data=res)

@router.get("/{companyId}/qoq/crossyear", response_model=APIResponse)
def get_crossyear_qoq_analysis(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine(companyId, db)
    q4_23 = engine.get_all_kpis_for_period("Q4FY23")
    q1_24 = engine.get_all_kpis_for_period("Q1FY24")
    
    bridge = {}
    if q4_23 and q1_24:
        for cat in ["profitability", "liquidity", "solvency", "efficiency"]:
            bridge[cat] = {}
            for kpi, data_24 in q1_24.get(cat, {}).items():
                data_23 = q4_23.get(cat, {}).get(kpi, {})
                val_23 = data_23.get("value", 0)
                val_24 = data_24.get("value", 0)
                diff = round(val_24 - val_23, 2)
                pct = round(diff / abs(val_23) * 100.0, 2) if val_23 != 0 else 0.0
                bridge[cat][kpi] = {
                    "Q4FY2023": val_23,
                    "Q1FY2024": val_24,
                    "cross_year_delta": diff,
                    "cross_year_pct": pct,
                    "unit": data_24.get("unit", "")
                }

    return APIResponse(success=True, statusCode=200, message="Cross-Year QoQ Bridge (Q4FY23 -> Q1FY24) retrieved", data=bridge)

@router.get("/{companyId}/yoy", response_model=APIResponse)
def get_yoy_analysis(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine(companyId, db)
    yoy_pairs = [("Q1FY24", "Q1FY23"), ("Q2FY24", "Q2FY23"), ("Q3FY24", "Q3FY23"), ("Q4FY24", "Q4FY23")]
    res = {}
    for fy24, fy23 in yoy_pairs:
        k_24 = engine.get_all_kpis_for_period(fy24)
        k_23 = engine.get_all_kpis_for_period(fy23)
        res[f"{fy24}_vs_{fy23}"] = {
            "FY2024": k_24,
            "FY2023": k_23
        }
    return APIResponse(success=True, statusCode=200, message="YoY Quarterly Analysis retrieved", data=res)

@router.get("/{companyId}/annual", response_model=APIResponse)
def get_annual_analysis(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine(companyId, db)
    return APIResponse(
        success=True,
        statusCode=200,
        message="Annual Comparison (FY2023 vs FY2024) retrieved",
        data={
            "AnnualFY2023": engine.get_all_kpis_for_period("AnnualFY23"),
            "AnnualFY2024": engine.get_all_kpis_for_period("AnnualFY24")
        }
    )

@router.get("/{companyId}/halfyear", response_model=APIResponse)
def get_halfyear_analysis(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    fe = get_kpi_engine(companyId, db).fe
    
    # H1 = Q1 + Q2, H2 = Q3 + Q4
    h1_23_pnl1, h1_23_pnl2 = fe.generate_income_statement("Q1", "FY2023"), fe.generate_income_statement("Q2", "FY2023")
    h1_24_pnl1, h1_24_pnl2 = fe.generate_income_statement("Q1", "FY2024"), fe.generate_income_statement("Q2", "FY2024")

    h1_23_rev = h1_23_pnl1.get("net_revenue", 0) + h1_23_pnl2.get("net_revenue", 0)
    h1_24_rev = h1_24_pnl1.get("net_revenue", 0) + h1_24_pnl2.get("net_revenue", 0)
    
    h1_23_ni = h1_23_pnl1.get("net_income", 0) + h1_23_pnl2.get("net_income", 0)
    h1_24_ni = h1_24_pnl1.get("net_income", 0) + h1_24_pnl2.get("net_income", 0)

    return APIResponse(
        success=True,
        statusCode=200,
        message="Half-Year Comparison (H1 & H2) retrieved",
        data={
            "H1FY2023": {"revenue": h1_23_rev, "net_income": h1_23_ni},
            "H1FY2024": {"revenue": h1_24_rev, "net_income": h1_24_ni},
            "H1_growth_pct": round((h1_24_rev - h1_23_rev) / abs(h1_23_rev) * 100.0, 2) if h1_23_rev != 0 else 0.0
        }
    )

@router.get("/{companyId}/trend", response_model=APIResponse)
def get_kpi_trend(companyId: str, kpi: str = Query("grossProfitMargin"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    engine = get_kpi_engine(companyId, db)
    # Convert camelCase to snake_case if needed
    kpi_snake = ''.join(['_' + c.lower() if c.isupper() else c for c in kpi]).lstrip('_')
    
    quarters = config.QUARTER_ORDER_8Q
    trend_series = []
    
    for q_key in quarters:
        kpis = engine.get_all_kpis_for_period(q_key)
        val = 0.0
        for cat in kpis.values():
            if kpi_snake in cat:
                val = cat[kpi_snake].get("value", 0.0)
                break
        trend_series.append({"period": q_key, "value": val})

    return APIResponse(success=True, statusCode=200, message=f"8-Quarter trend series for {kpi} retrieved", data={"kpi": kpi_snake, "trend": trend_series})

@router.get("/{companyId}/waterfall", response_model=APIResponse)
def get_waterfall_bridge(companyId: str, from_p: str = Query("Q1FY2023"), to_p: str = Query("Q4FY2024"), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    fe = get_kpi_engine(companyId, db).fe
    q_start, fy_start = "Q1", "FY2023"
    q_end, fy_end = "Q4", "FY2024"

    pnl_start = fe.generate_income_statement(q_start, fy_start)
    pnl_end = fe.generate_income_statement(q_end, fy_end)

    rev_start = pnl_start.get("net_revenue", 0)
    cogs_start = pnl_start.get("cogs", {}).get("total", 0)
    opex_start = pnl_start.get("opex", {}).get("total", 0)

    rev_end = pnl_end.get("net_revenue", 0)
    cogs_end = pnl_end.get("cogs", {}).get("total", 0)
    opex_end = pnl_end.get("opex", {}).get("total", 0)

    rev_delta = rev_end - rev_start
    cogs_delta = -(cogs_end - cogs_start)  # cost increase reduces profit
    opex_delta = -(opex_end - opex_start)

    waterfall_items = [
        {"name": "Q1 FY23 Net Revenue", "amount": rev_start, "type": "total"},
        {"name": "Volume & Pricing Growth", "amount": round(rev_delta, 2), "type": "delta"},
        {"name": "COGS Variation", "amount": round(cogs_delta, 2), "type": "delta"},
        {"name": "OpEx Variation", "amount": round(opex_delta, 2), "type": "delta"},
        {"name": "Q4 FY24 Net Income", "amount": pnl_end.get("net_income", 0), "type": "total"}
    ]

    return APIResponse(success=True, statusCode=200, message="Waterfall Bridge retrieved", data=waterfall_items)

@router.get("/{companyId}/rolling", response_model=APIResponse)
def get_rolling_ltm(companyId: str, window: int = Query(4), db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    fe = get_kpi_engine(companyId, db).fe
    quarters = config.QUARTER_ORDER_8Q

    ltm_results = {}
    for i in range(3, len(quarters)):
        sub_4q = quarters[i-3:i+1]
        ltm_rev = sum(fe.generate_income_statement(q[:2], "FY20" + q[-2:]).get("net_revenue", 0) for q in sub_4q)
        ltm_ni  = sum(fe.generate_income_statement(q[:2], "FY20" + q[-2:]).get("net_income", 0) for q in sub_4q)
        ltm_ebitda = sum(fe.generate_income_statement(q[:2], "FY20" + q[-2:]).get("ebitda", 0) for q in sub_4q)
        
        ltm_results[quarters[i]] = {
            "sub_quarters": sub_4q,
            "ltm_revenue": round(ltm_rev, 2),
            "ltm_net_income": round(ltm_ni, 2),
            "ltm_ebitda": round(ltm_ebitda, 2),
            "ltm_net_margin_pct": round(ltm_ni / ltm_rev * 100.0, 2) if ltm_rev > 0 else 0.0
        }

    return APIResponse(success=True, statusCode=200, message="Rolling 4-Quarter (LTM) KPIs retrieved", data=ltm_results)
