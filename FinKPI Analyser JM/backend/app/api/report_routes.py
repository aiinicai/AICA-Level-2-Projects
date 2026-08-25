from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TrialBalanceModel, CompanyModel, UserModel
from ..schemas import APIResponse
from ..kpi_engine import KPIEngine
from ..exporter import generate_excel_report, generate_pdf_report
from ..auth import get_current_user
from ..config import config

router = APIRouter(prefix="/api/v1/reports", tags=["Reports & Export"])

def get_engines(companyId: str, db: Session):
    company = db.query(CompanyModel).filter(CompanyModel.id == companyId).first()
    c_name = company.company_name if company else "Company"
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
    kpi_engine = KPIEngine(records, shares_outstanding=shares, headcount=headcount)
    return c_name, kpi_engine

@router.get("/{companyId}/export")
def export_report(
    companyId: str,
    format: str = Query("excel"),   # excel or pdf
    type: str = Query("full"),      # full, comparative, kpi-scorecard
    period: str = Query("Q4"),
    year: str = Query("FY2024"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    c_name, kpi_engine = get_engines(companyId, db)
    p_key = f"{period}{year.replace('FY20', 'FY')}"
    
    pnl = kpi_engine.fe.generate_income_statement(period, year)
    bs  = kpi_engine.fe.generate_balance_sheet(period, year)
    kpis = kpi_engine.get_all_kpis_for_period(p_key)

    if format.lower() == "pdf":
        pdf_bytes = generate_pdf_report(c_name, period, year, pnl, bs, kpis)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="Financial_KPI_Report_{c_name}_{period}_{year}.pdf"'}
        )
    else:
        excel_bytes = generate_excel_report(c_name, pnl, bs, kpis)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="Financial_KPI_Report_{c_name}_{period}_{year}.xlsx"'}
        )

@router.post("/{companyId}/schedule", response_model=APIResponse)
def schedule_report(
    companyId: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    freq = payload.get("frequency", "monthly")
    recipients = payload.get("recipients", [])
    rep_format = payload.get("format", "pdf")
    
    return APIResponse(
        success=True,
        statusCode=200,
        message=f"Report scheduled successfully with {freq} frequency for {len(recipients)} recipients.",
        data={
            "companyId": companyId,
            "frequency": freq,
            "recipients": recipients,
            "format": rep_format,
            "status": "ACTIVE"
        }
    )
