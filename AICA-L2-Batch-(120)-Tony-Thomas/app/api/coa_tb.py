import io
import csv
import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api", tags=["Chart of Accounts & Opening TB"])

@router.get("/accounts", response_model=List[schemas.AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    return db.query(models.Account).order_by(models.Account.account_code).all()

@router.post("/accounts", response_model=schemas.AccountResponse)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Account).filter(models.Account.account_code == account.account_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account code already exists")
    db_account = models.Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/opening-tb/template")
def download_tb_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["account_code", "account_name", "account_type", "sub_category", "is_control_account", "opening_debit", "opening_credit"])
    
    sample_rows = [
        ["1010", "Cash at Bank - Primary Operating", "Asset", "Bank", "FALSE", "250000.00", "0.00"],
        ["1020", "Cash at Bank - Payroll & Treasury", "Asset", "Bank", "FALSE", "50000.00", "0.00"],
        ["1100", "Accounts Receivable Control", "Asset", "Accounts Receivable", "TRUE", "60000.00", "0.00"],
        ["1200", "Inventory / Goods in Transit", "Asset", "Inventory/GRN", "FALSE", "40000.00", "0.00"],
        ["1500", "Property, Plant & Equipment", "Asset", "Fixed Assets", "FALSE", "100000.00", "0.00"],
        ["2000", "Accounts Payable Control", "Liability", "Accounts Payable", "TRUE", "0.00", "45000.00"],
        ["2020", "Output VAT / Tax Payable", "Liability", "Tax Output", "TRUE", "0.00", "5000.00"],
        ["3000", "Share Capital", "Equity", "Share Capital", "FALSE", "0.00", "300000.00"],
        ["3010", "Retained Earnings", "Equity", "Retained Earnings", "FALSE", "0.00", "150000.00"]
    ]
    for r in sample_rows:
        writer.writerow(r)
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=opening_tb_template.csv"}
    )

@router.post("/opening-tb/validate", response_model=schemas.OpeningTBValidationResponse)
def validate_opening_tb(rows: List[schemas.OpeningTBUploadRow]):
    if not rows:
        return schemas.OpeningTBValidationResponse(
            valid=False,
            total_debit=0.0,
            total_credit=0.0,
            variance=0.0,
            row_count=0,
            message="No rows provided in payload"
        )
    tot_dr = round(sum(r.opening_debit for r in rows), 2)
    tot_cr = round(sum(r.opening_credit for r in rows), 2)
    variance = round(tot_dr - tot_cr, 2)
    is_valid = abs(variance) < 0.01

    if is_valid:
        msg = f"Trial Balance is perfectly balanced! Total Debits: ${tot_dr:,.2f} == Total Credits: ${tot_cr:,.2f}"
    else:
        msg = f"Out of Balance! Total Debits: ${tot_dr:,.2f}, Total Credits: ${tot_cr:,.2f}. Variance: ${abs(variance):,.2f}."

    return schemas.OpeningTBValidationResponse(
        valid=is_valid,
        total_debit=tot_dr,
        total_credit=tot_cr,
        variance=variance,
        row_count=len(rows),
        message=msg
    )

@router.post("/opening-tb/upload")
def upload_opening_tb(rows: List[schemas.OpeningTBUploadRow], db: Session = Depends(get_db)):
    # Validate balance
    tot_dr = round(sum(r.opening_debit for r in rows), 2)
    tot_cr = round(sum(r.opening_credit for r in rows), 2)
    if abs(tot_dr - tot_cr) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot import unbalanced Trial Balance! Total Debits: ${tot_dr:,.2f}, Total Credits: ${tot_cr:,.2f}, Variance: ${abs(tot_dr - tot_cr):,.2f}"
        )

    # Upsert accounts
    for r in rows:
        acc = db.query(models.Account).filter(models.Account.account_code == r.account_code).first()
        if not acc:
            acc = models.Account(
                account_code=r.account_code,
                account_name=r.account_name,
                account_type=r.account_type,
                sub_category=r.sub_category,
                is_control_account=r.is_control_account,
                opening_debit=r.opening_debit,
                opening_credit=r.opening_credit
            )
            db.add(acc)
        else:
            acc.account_name = r.account_name
            acc.account_type = r.account_type
            acc.sub_category = r.sub_category
            acc.is_control_account = r.is_control_account
            acc.opening_debit = r.opening_debit
            acc.opening_credit = r.opening_credit
    db.commit()

    # Create / update OB-0001 voucher in GL
    existing_ob = db.query(models.JournalVoucher).filter(models.JournalVoucher.voucher_no == "OB-0001").first()
    if existing_ob:
        db.delete(existing_ob)
        db.commit()

    ob_lines = []
    for r in rows:
        if r.opening_debit > 0 or r.opening_credit > 0:
            ob_lines.append({
                "account_code": r.account_code,
                "account_name": r.account_name,
                "description": "Opening Trial Balance Migration",
                "debit": r.opening_debit,
                "credit": r.opening_credit
            })

    crud.create_journal_voucher_entry(
        db=db,
        voucher_no="OB-0001",
        posting_date=datetime.date(2026, 1, 1),
        source_module="OB",
        document_ref="OB-UPLOAD",
        description="Opening Trial Balance Import & GL Initialization",
        lines=ob_lines,
        created_by="Submitter (Maker)",
        approved_by="Approver (Finance Manager)",
        status="Approved"
    )

    return {
        "status": "success",
        "message": f"Successfully updated Chart of Accounts and generated approved Opening Balance Voucher OB-0001 (${tot_dr:,.2f})",
        "total_balanced_amount": tot_dr
    }

@router.post("/opening-tb/save")
def save_opening_tb(rows: List[schemas.OpeningTBUploadRow], db: Session = Depends(get_db)):
    """Save opening trial balance from on-screen migration grid or upload."""
    return upload_opening_tb(rows=rows, db=db)

@router.delete("/opening-tb/reset")
def reset_opening_tb(db: Session = Depends(get_db)):
    """Reset all account opening balances to 0.00 and delete OB-0001 voucher."""
    accounts = db.query(models.Account).all()
    for acc in accounts:
        acc.opening_debit = 0.0
        acc.opening_credit = 0.0
    
    existing_ob = db.query(models.JournalVoucher).filter(models.JournalVoucher.voucher_no == "OB-0001").first()
    if existing_ob:
        db.delete(existing_ob)
    
    db.commit()
    return {"status": "success", "message": "Opening Trial Balance cleared. All account opening balances reset to $0.00."}

