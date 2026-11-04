from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/ap", tags=["Accounts Payable (AP)"])

# Vendors
@router.get("/vendors", response_model=List[schemas.VendorResponse])
def get_vendors(db: Session = Depends(get_db)):
    return db.query(models.Vendor).order_by(models.Vendor.vendor_code).all()

@router.post("/vendors", response_model=schemas.VendorResponse)
def create_vendor(vendor_in: schemas.VendorCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Vendor).filter(models.Vendor.vendor_code == vendor_in.vendor_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vendor code already exists")
    v = models.Vendor(**vendor_in.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v

@router.put("/vendors/{vendor_code}", response_model=schemas.VendorResponse)
def update_vendor(vendor_code: str, vendor_in: schemas.VendorUpdate, db: Session = Depends(get_db)):
    v = db.query(models.Vendor).filter(models.Vendor.vendor_code == vendor_code).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    data = vendor_in.model_dump(exclude_unset=True)
    for k, val in data.items():
        if val is not None:
            setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return v

@router.get("/vendors/{vendor_code}/statement")
def get_vendor_statement(vendor_code: str, db: Session = Depends(get_db)):
    v = db.query(models.Vendor).filter(models.Vendor.vendor_code == vendor_code).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    invoices = db.query(models.APInvoice).filter(models.APInvoice.vendor_code == vendor_code).order_by(models.APInvoice.invoice_date.desc()).all()
    payments = db.query(models.APPayment).filter(models.APPayment.vendor_code == vendor_code).order_by(models.APPayment.payment_date.desc()).all()
    
    tot_billed = sum(i.total_amount for i in invoices if i.status == "Approved")
    tot_paid = sum(p.total_amount for p in payments if p.status == "Approved")
    balance = round(tot_billed - tot_paid, 2)
    
    return {
        "vendor": {
            "vendor_code": v.vendor_code,
            "name": v.name,
            "trn": v.trn,
            "payment_terms": v.payment_terms,
            "bank_details": v.bank_details,
            "email": v.email,
            "phone": v.phone
        },
        "total_billed": round(tot_billed, 2),
        "total_paid": round(tot_paid, 2),
        "outstanding_balance": balance,
        "invoices": [
            {
                "invoice_number": i.invoice_number,
                "invoice_date": str(i.invoice_date),
                "vendor_invoice_ref": i.vendor_invoice_ref,
                "total_amount": i.total_amount,
                "paid_amount": i.paid_amount,
                "remaining_balance": round(i.total_amount - i.paid_amount, 2),
                "status": i.status,
                "payment_status": i.payment_status
            }
            for i in invoices
        ],
        "payments": [
            {
                "payment_number": p.payment_number,
                "payment_date": str(p.payment_date),
                "payment_ref": p.payment_ref,
                "bank_account_code": p.bank_account_code,
                "total_amount": p.total_amount,
                "status": p.status
            }
            for p in payments
        ]
    }

# AP Invoices
@router.get("/invoices", response_model=List[schemas.APInvoiceResponse])
def get_ap_invoices(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    vendor_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.APInvoice)
    if status:
        q = q.filter(models.APInvoice.status == status)
    if payment_status:
        q = q.filter(models.APInvoice.payment_status == payment_status)
    if vendor_code:
        q = q.filter(models.APInvoice.vendor_code == vendor_code)

    invoices = q.order_by(models.APInvoice.id.desc()).all()
    for inv in invoices:
        inv.vendor_name = inv.vendor.name if inv.vendor else ""
        inv.remaining_balance = round(inv.total_amount - inv.paid_amount, 2)
    return invoices

@router.post("/invoices", response_model=schemas.APInvoiceResponse)
def create_ap_invoice(
    inv_in: schemas.APInvoiceCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Accountant"),
    db: Session = Depends(get_db)
):
    # Mode B Direct Expense Budget Check
    if inv_in.invoice_mode == "Mode_B_Direct":
        if not inv_in.expense_account_code:
            raise HTTPException(status_code=400, detail="Expense account is required for direct expense invoices")
        chk = crud.check_budget_availability(db, inv_in.expense_account_code, inv_in.subtotal)
        if not chk.passed:
            raise HTTPException(
                status_code=400,
                detail=f"Budget Check Failed for account {inv_in.expense_account_code} ({chk.account_name}): Available budget is ${chk.available_budget:,.2f}, invoice requires ${inv_in.subtotal:,.2f}."
            )

    # 3-Way Match Check for GRN / PO Mode
    if inv_in.grn_number:
        grn = db.query(models.GoodsReceiptNote).filter(models.GoodsReceiptNote.grn_number == inv_in.grn_number).first()
        if not grn:
            raise HTTPException(status_code=400, detail=f"Goods Receipt Note {inv_in.grn_number} not found.")
        grn_val = sum(l.line_amount for l in grn.lines)
        already_invoiced = sum(
            i.subtotal for i in db.query(models.APInvoice).filter(
                models.APInvoice.grn_number == inv_in.grn_number,
                models.APInvoice.status != "Rejected"
            ).all()
        )
        max_allowed = round(grn_val - already_invoiced, 2)
        if round(inv_in.subtotal, 2) > max_allowed + 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"3-Way Match Validation Failed: Invoice subtotal (${inv_in.subtotal:,.2f}) exceeds the maximum allowable received value for GRN {inv_in.grn_number} (${max_allowed:,.2f}). Total GRN value is ${grn_val:,.2f}, previously invoiced: ${already_invoiced:,.2f}."
            )

    inv_num = crud.get_next_sequence_number(db, "AP-INV-2026", models.APInvoice, "invoice_number")
    inv = models.APInvoice(
        invoice_number=inv_num,
        invoice_mode=inv_in.invoice_mode,
        vendor_code=inv_in.vendor_code,
        vendor_invoice_ref=inv_in.vendor_invoice_ref,
        po_number=inv_in.po_number,
        grn_number=inv_in.grn_number,
        invoice_date=inv_in.invoice_date,
        due_date=inv_in.due_date,
        expense_account_code=inv_in.expense_account_code,
        tax_code=inv_in.tax_code,
        subtotal=round(inv_in.subtotal, 2),
        tax_amount=round(inv_in.tax_amount, 2),
        total_amount=round(inv_in.total_amount, 2),
        paid_amount=0.0,
        status="Draft" if status == "Draft" else "Pending Approval",
        payment_status="Unpaid",
        created_by=created_by,
        notes=inv_in.notes
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    if status == "Approved":
        inv = crud.approve_ap_invoice_and_post_gl(db, inv.id, approver=created_by)

    inv.vendor_name = inv.vendor.name if inv.vendor else ""
    inv.remaining_balance = round(inv.total_amount - inv.paid_amount, 2)
    return inv

# AP Payments
@router.get("/payments", response_model=List[schemas.APPaymentResponse])
def get_ap_payments(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.APPayment)
    if status:
        q = q.filter(models.APPayment.status == status)
    pmts = q.order_by(models.APPayment.id.desc()).all()
    for p in pmts:
        p.vendor_name = p.vendor.name if p.vendor else ""
    return pmts

@router.post("/payments", response_model=schemas.APPaymentResponse)
def create_ap_payment(
    pmt_in: schemas.APPaymentCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Accountant"),
    db: Session = Depends(get_db)
):
    if not pmt_in.lines:
        raise HTTPException(status_code=400, detail="Payment proposal must select at least one invoice")

    tot_paid = round(sum(l.amount_paid for l in pmt_in.lines), 2)
    pmt_num = crud.get_next_sequence_number(db, "AP-PMT-2026", models.APPayment, "payment_number")

    pmt = models.APPayment(
        payment_number=pmt_num,
        payment_date=pmt_in.payment_date,
        vendor_code=pmt_in.vendor_code,
        bank_account_code=pmt_in.bank_account_code,
        payment_ref=pmt_in.payment_ref,
        payment_method=pmt_in.payment_method,
        total_amount=tot_paid,
        status="Draft" if status == "Draft" else "Pending Approval",
        created_by=created_by,
        notes=pmt_in.notes
    )
    db.add(pmt)
    db.flush()

    for l in pmt_in.lines:
        db.add(models.APPaymentLine(
            payment_id=pmt.id,
            ap_invoice_id=l.ap_invoice_id,
            invoice_number=l.invoice_number,
            amount_paid=l.amount_paid
        ))

    db.commit()
    db.refresh(pmt)

    if status == "Approved":
        pmt = crud.approve_ap_payment_and_post_gl(db, pmt.id, approver=created_by)

    pmt.vendor_name = pmt.vendor.name if pmt.vendor else ""
    return pmt

# AP Credit Notes
@router.get("/credit-notes", response_model=List[schemas.APCreditNoteResponse])
def get_ap_credit_notes(vendor_code: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.APCreditNote)
    if vendor_code:
        q = q.filter(models.APCreditNote.vendor_code == vendor_code)
    notes = q.order_by(models.APCreditNote.id.desc()).all()
    for n in notes:
        n.vendor_name = n.vendor.name if n.vendor else ""
    return notes

@router.post("/credit-notes", response_model=schemas.APCreditNoteResponse)
def create_ap_credit_note(
    cn_in: schemas.APCreditNoteCreate,
    created_by: str = Query("Owner / Accountant"),
    db: Session = Depends(get_db)
):
    vendor = db.query(models.Vendor).filter(models.Vendor.vendor_code == cn_in.vendor_code).first()
    if not vendor:
        raise HTTPException(status_code=400, detail="Vendor not found")
    if cn_in.subtotal <= 0:
        raise HTTPException(status_code=400, detail="Credit note subtotal must be greater than zero")

    cn = crud.create_ap_credit_note_and_post_gl(db, cn_in, created_by=created_by)
    cn.vendor_name = vendor.name
    return cn

