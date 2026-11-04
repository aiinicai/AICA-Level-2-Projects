from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/ar", tags=["Accounts Receivable (AR) & Billing"])

# Customers
@router.get("/customers", response_model=List[schemas.CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    return db.query(models.Customer).order_by(models.Customer.customer_code).all()

@router.post("/customers", response_model=schemas.CustomerResponse)
def create_customer(cust_in: schemas.CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Customer).filter(models.Customer.customer_code == cust_in.customer_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Customer code already exists")
    c = models.Customer(**cust_in.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.put("/customers/{customer_code}", response_model=schemas.CustomerResponse)
def update_customer(customer_code: str, cust_in: schemas.CustomerUpdate, db: Session = Depends(get_db)):
    c = db.query(models.Customer).filter(models.Customer.customer_code == customer_code).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    data = cust_in.model_dump(exclude_unset=True)
    for k, val in data.items():
        if val is not None:
            setattr(c, k, val)
    db.commit()
    db.refresh(c)
    return c

@router.get("/customers/{customer_code}/statement")
def get_customer_statement(customer_code: str, db: Session = Depends(get_db)):
    c = db.query(models.Customer).filter(models.Customer.customer_code == customer_code).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    invoices = db.query(models.ARInvoice).filter(models.ARInvoice.customer_code == customer_code).order_by(models.ARInvoice.invoice_date.desc()).all()
    receipts = db.query(models.ARReceipt).filter(models.ARReceipt.customer_code == customer_code).order_by(models.ARReceipt.receipt_date.desc()).all()
    
    tot_invoiced = sum(i.total_amount for i in invoices if i.status == "Approved")
    tot_collected = sum(r.total_amount for r in receipts if r.status == "Approved")
    balance = round(tot_invoiced - tot_collected, 2)
    
    return {
        "customer": {
            "customer_code": c.customer_code,
            "name": c.name,
            "trn": c.trn,
            "billing_address": c.billing_address,
            "credit_limit": c.credit_limit,
            "email": c.email,
            "phone": c.phone
        },
        "total_invoiced": round(tot_invoiced, 2),
        "total_collected": round(tot_collected, 2),
        "outstanding_balance": balance,
        "invoices": [
            {
                "invoice_number": i.invoice_number,
                "invoice_date": str(i.invoice_date),
                "total_amount": i.total_amount,
                "paid_amount": i.paid_amount,
                "remaining_balance": round(i.total_amount - i.paid_amount, 2),
                "status": i.status,
                "payment_status": i.payment_status
            }
            for i in invoices
        ],
        "receipts": [
            {
                "receipt_number": r.receipt_number,
                "receipt_date": str(r.receipt_date),
                "receipt_ref": r.receipt_ref,
                "bank_account_code": r.bank_account_code,
                "total_amount": r.total_amount,
                "status": r.status
            }
            for r in receipts
        ]
    }

# AR Invoices
@router.get("/invoices", response_model=List[schemas.ARInvoiceResponse])
def get_ar_invoices(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    customer_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.ARInvoice)
    if status:
        q = q.filter(models.ARInvoice.status == status)
    if payment_status:
        q = q.filter(models.ARInvoice.payment_status == payment_status)
    if customer_code:
        q = q.filter(models.ARInvoice.customer_code == customer_code)

    invoices = q.order_by(models.ARInvoice.id.desc()).all()
    for inv in invoices:
        inv.customer_name = inv.customer.name if inv.customer else ""
        inv.customer_trn = inv.customer.trn if inv.customer else ""
        inv.customer_address = inv.customer.billing_address if inv.customer else ""
        inv.remaining_balance = round(inv.total_amount - inv.paid_amount, 2)
    return invoices

@router.post("/invoices", response_model=schemas.ARInvoiceResponse)
def create_ar_invoice(
    inv_in: schemas.ARInvoiceCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Accountant"),
    db: Session = Depends(get_db)
):
    if not inv_in.lines:
        raise HTTPException(status_code=400, detail="Invoice must have at least one line item")

    subtotal = 0.0
    discount_total = 0.0
    tax_total = 0.0
    ar_lines = []

    for idx, l in enumerate(inv_in.lines, start=1):
        line_sub = round(l.quantity * l.unit_price, 2)
        net_amt = round(line_sub - l.discount_amount, 2)
        
        tax = db.query(models.TaxCode).filter(models.TaxCode.code == l.tax_code).first()
        rate = tax.rate if tax else 5.0
        line_tax = round(net_amt * (rate / 100.0), 2)
        line_tot = round(net_amt + line_tax, 2)

        subtotal += line_sub
        discount_total += l.discount_amount
        tax_total += line_tax

        ar_lines.append(models.ARInvoiceLine(
            line_no=idx,
            item_code=l.item_code,
            description=l.description,
            revenue_account_code=l.revenue_account_code,
            quantity=l.quantity,
            unit_price=l.unit_price,
            discount_amount=l.discount_amount,
            tax_code=l.tax_code,
            net_amount=net_amt,
            tax_amount=line_tax,
            total_amount=line_tot
        ))

    inv_num = crud.get_next_sequence_number(db, "INV-2026", models.ARInvoice, "invoice_number")
    tot_amt = round(subtotal - discount_total + tax_total, 2)

    inv = models.ARInvoice(
        invoice_number=inv_num,
        customer_code=inv_in.customer_code,
        invoice_date=inv_in.invoice_date,
        due_date=inv_in.due_date,
        subtotal=round(subtotal, 2),
        discount_total=round(discount_total, 2),
        tax_amount=round(tax_total, 2),
        total_amount=tot_amt,
        paid_amount=0.0,
        status="Draft" if status == "Draft" else "Pending Approval",
        payment_status="Unpaid",
        created_by=created_by,
        notes=inv_in.notes,
        lines=ar_lines
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    if status == "Approved":
        inv = crud.approve_ar_invoice_and_post_gl(db, inv.id, approver=created_by)

    inv.customer_name = inv.customer.name if inv.customer else ""
    inv.customer_trn = inv.customer.trn if inv.customer else ""
    inv.customer_address = inv.customer.billing_address if inv.customer else ""
    inv.remaining_balance = round(inv.total_amount - inv.paid_amount, 2)
    return inv

# AR Receipts
@router.get("/receipts", response_model=List[schemas.ARReceiptResponse])
def get_ar_receipts(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.ARReceipt)
    if status:
        q = q.filter(models.ARReceipt.status == status)
    rcpts = q.order_by(models.ARReceipt.id.desc()).all()
    for r in rcpts:
        r.customer_name = r.customer.name if r.customer else ""
    return rcpts

@router.post("/receipts", response_model=schemas.ARReceiptResponse)
def create_ar_receipt(
    rcpt_in: schemas.ARReceiptCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Accountant"),
    db: Session = Depends(get_db)
):
    if not rcpt_in.lines:
        raise HTTPException(status_code=400, detail="Receipt must specify at least one invoice")

    tot_received = round(sum(l.amount_received for l in rcpt_in.lines), 2)
    rcpt_num = crud.get_next_sequence_number(db, "REC-2026", models.ARReceipt, "receipt_number")

    rcpt = models.ARReceipt(
        receipt_number=rcpt_num,
        receipt_date=rcpt_in.receipt_date,
        customer_code=rcpt_in.customer_code,
        bank_account_code=rcpt_in.bank_account_code,
        receipt_ref=rcpt_in.receipt_ref,
        receipt_method=rcpt_in.receipt_method,
        total_amount=tot_received,
        status="Draft" if status == "Draft" else "Pending Approval",
        created_by=created_by,
        notes=rcpt_in.notes
    )
    db.add(rcpt)
    db.flush()

    for l in rcpt_in.lines:
        db.add(models.ARReceiptLine(
            receipt_id=rcpt.id,
            ar_invoice_id=l.ar_invoice_id,
            invoice_number=l.invoice_number,
            amount_received=l.amount_received
        ))

    db.commit()
    db.refresh(rcpt)

    if status == "Approved":
        rcpt = crud.approve_ar_receipt_and_post_gl(db, rcpt.id, approver=created_by)

    rcpt.customer_name = rcpt.customer.name if rcpt.customer else ""
    return rcpt

# AR Credit Notes
@router.get("/credit-notes", response_model=List[schemas.ARCreditNoteResponse])
def get_ar_credit_notes(customer_code: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.ARCreditNote)
    if customer_code:
        q = q.filter(models.ARCreditNote.customer_code == customer_code)
    notes = q.order_by(models.ARCreditNote.id.desc()).all()
    for n in notes:
        n.customer_name = n.customer.name if n.customer else ""
    return notes

@router.post("/credit-notes", response_model=schemas.ARCreditNoteResponse)
def create_ar_credit_note(
    cn_in: schemas.ARCreditNoteCreate,
    created_by: str = Query("Owner / Accountant"),
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(models.Customer.customer_code == cn_in.customer_code).first()
    if not customer:
        raise HTTPException(status_code=400, detail="Customer not found")
    if cn_in.subtotal <= 0:
        raise HTTPException(status_code=400, detail="Credit note subtotal must be greater than zero")

    cn = crud.create_ar_credit_note_and_post_gl(db, cn_in, created_by=created_by)
    cn.customer_name = customer.name
    return cn

