import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/gl", tags=["General Ledger"])

@router.get("/vouchers", response_model=List[schemas.JournalVoucherResponse])
def get_vouchers(
    source_module: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[datetime.date] = Query(None),
    to_date: Optional[datetime.date] = Query(None),
    account_code: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.JournalVoucher)

    if source_module:
        query = query.filter(models.JournalVoucher.source_module == source_module)
    if status:
        query = query.filter(models.JournalVoucher.status == status)
    if from_date:
        query = query.filter(models.JournalVoucher.posting_date >= from_date)
    if to_date:
        query = query.filter(models.JournalVoucher.posting_date <= to_date)
    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                models.JournalVoucher.voucher_no.ilike(s),
                models.JournalVoucher.document_ref.ilike(s),
                models.JournalVoucher.description.ilike(s)
            )
        )
    if account_code:
        query = query.join(models.VoucherLine).filter(models.VoucherLine.account_code == account_code)

    return query.order_by(models.JournalVoucher.posting_date.desc(), models.JournalVoucher.id.desc()).all()

@router.get("/vouchers/{voucher_no}", response_model=schemas.JournalVoucherResponse)
def get_voucher_detail(voucher_no: str, db: Session = Depends(get_db)):
    jv = db.query(models.JournalVoucher).filter(models.JournalVoucher.voucher_no == voucher_no).first()
    if not jv:
        raise HTTPException(status_code=404, detail="Journal Voucher not found")
    return jv

@router.post("/vouchers", response_model=schemas.JournalVoucherResponse)
def create_manual_journal_voucher(
    voucher_in: schemas.JournalVoucherCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Accountant"),
    db: Session = Depends(get_db)
):
    tot_dr = round(sum(l.debit for l in voucher_in.lines), 2)
    tot_cr = round(sum(l.credit for l in voucher_in.lines), 2)

    if tot_dr <= 0 or tot_cr <= 0:
        raise HTTPException(status_code=400, detail="Journal voucher must have debits and credits greater than zero")

    if abs(tot_dr - tot_cr) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Out of Balance! Total Debit (${tot_dr:,.2f}) must equal Total Credit (${tot_cr:,.2f}). Variance: ${abs(tot_dr - tot_cr):,.2f}"
        )

    voucher_no = crud.get_next_sequence_number(db, "JV-2026", models.JournalVoucher, "voucher_no")
    lines_data = [l.model_dump() for l in voucher_in.lines]

    jv = crud.create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=voucher_in.posting_date,
        source_module="GL-JV",
        document_ref=voucher_in.document_ref,
        description=voucher_in.description,
        lines=lines_data,
        created_by=created_by,
        approved_by=created_by if status == "Approved" else None,
        status=status
    )
    return jv
