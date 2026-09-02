from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TrialBalanceModel, CompanyModel, UserModel
from ..schemas import APIResponse
from ..parser import parse_excel_trial_balance
from ..auth import get_current_user, require_role
from ..config import config

router = APIRouter(prefix="/api/v1/trial-balance", tags=["Trial Balance"])

@router.post("/upload", response_model=APIResponse)
async def upload_trial_balance(
    file: UploadFile = File(...),
    companyId: str = Form(...),
    fiscalYearStart: Optional[int] = Form(1),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role(["admin", "analyst"]))
):
    company = db.query(CompanyModel).filter(CompanyModel.id == companyId).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    contents = await file.read()
    try:
        parsed = parse_excel_trial_balance(contents)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # Delete previous trial balance records for this company
    db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == companyId).delete()

    # Bulk insert parsed records
    records_to_insert = [
        TrialBalanceModel(
            company_id=companyId,
            fiscal_year=r["fiscal_year"],
            quarter=r["quarter"],
            period_id=r["period_id"],
            period_sequence=r["period_sequence"],
            account_code=r["account_code"],
            account_name=r["account_name"],
            category=r["category"],
            sub_category=r["sub_category"],
            account_type=r["account_type"],
            normal_balance=r["normal_balance"],
            debit_amount=r["debit_amount"],
            credit_amount=r["credit_amount"],
            net_balance=r["net_balance"]
        )
        for r in parsed["records"]
    ]
    db.bulk_save_objects(records_to_insert)
    db.commit()

    return APIResponse(
        success=True,
        statusCode=200,
        message="Trial Balance uploaded, validated, and processed successfully",
        data={
            "validationReport": parsed["validation_report"],
            "periodsDetected": parsed["periods_detected"],
            "totalRecords": parsed["total_records"],
            "allPeriodsBalanced": parsed["all_periods_balanced"],
            "errors": parsed["errors"]
        }
    )

@router.post("/validate", response_model=APIResponse)
def validate_trial_balance(companyId: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    tbs = db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == companyId).all()
    if not tbs:
        raise HTTPException(status_code=404, detail="No trial balance records found for company")

    details = {}
    for sheet, meta in config.SHEET_MAP.items():
        q, fy = meta["quarter"], meta["year"]
        recs = [t for t in tbs if t.quarter == q and t.fiscal_year == fy]
        debit_sum = sum(t.debit_amount for t in recs)
        credit_sum = sum(t.credit_amount for t in recs)
        net_sum = sum(t.net_balance for t in recs)
        balanced = abs(debit_sum - credit_sum) < 5.0 or abs(net_sum) < 5.0
        
        details[sheet] = {
            "period": f"{q} {fy}",
            "rows": len(recs),
            "total_debit": round(debit_sum, 2),
            "total_credit": round(credit_sum, 2),
            "is_balanced": balanced
        }

    all_balanced = all(d["is_balanced"] for d in details.values())
    return APIResponse(
        success=True,
        statusCode=200,
        message="Validation executed",
        data={"allPeriodsBalanced": all_balanced, "details": details}
    )

@router.get("/{companyId}", response_model=APIResponse)
def get_trial_balance(
    companyId: str,
    period: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == companyId)
    if period:
        query = query.filter(TrialBalanceModel.quarter == period)
    if year:
        query = query.filter(TrialBalanceModel.fiscal_year == year)

    records = query.all()
    res = [
        {
            "id": r.id,
            "account_code": r.account_code,
            "account_name": r.account_name,
            "category": r.category,
            "sub_category": r.sub_category,
            "account_type": r.account_type,
            "normal_balance": r.normal_balance,
            "debit_amount": r.debit_amount,
            "credit_amount": r.credit_amount,
            "net_balance": r.net_balance,
            "quarter": r.quarter,
            "fiscal_year": r.fiscal_year,
            "period_id": r.period_id
        }
        for r in records
    ]
    return APIResponse(
        success=True,
        statusCode=200,
        message="Trial Balance records retrieved",
        data={"count": len(res), "records": res}
    )

@router.delete("/{companyId}", response_model=APIResponse)
def delete_trial_balance(
    companyId: str,
    year: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role(["admin"]))
):
    query = db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == companyId)
    if year:
        query = query.filter(TrialBalanceModel.fiscal_year == year)
    
    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    return APIResponse(
        success=True,
        statusCode=200,
        message=f"Deleted {deleted_count} trial balance records",
        data={"deletedCount": deleted_count}
    )
