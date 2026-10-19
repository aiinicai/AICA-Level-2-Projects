from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/p2p", tags=["Procurement (P2P)"])

# Purchase Requisitions
@router.get("/prs", response_model=List[schemas.PRResponse])
def get_prs(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.PurchaseRequisition)
    if status:
        q = q.filter(models.PurchaseRequisition.status == status)
    return q.order_by(models.PurchaseRequisition.id.desc()).all()

@router.post("/prs", response_model=schemas.PRResponse)
def create_pr(
    pr_in: schemas.PRCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Operations"),
    db: Session = Depends(get_db)
):
    if not pr_in.lines:
        raise HTTPException(status_code=400, detail="PR must have at least one line item")

    total_amt = 0.0
    pr_lines = []

    for idx, l in enumerate(pr_in.lines, start=1):
        line_tot = round(l.quantity * l.unit_price, 2)
        total_amt += line_tot

        # Real-time budget check
        chk = crud.check_budget_availability(db, l.account_code, line_tot)
        if not chk.passed:
            raise HTTPException(
                status_code=400,
                detail=f"Budget Check Failed for account {l.account_code} ({chk.account_name}): Available budget is ${chk.available_budget:,.2f}, line requires ${line_tot:,.2f}. Exceeds by ${abs(chk.variance):,.2f}."
            )

        pr_lines.append(models.PRLine(
            line_no=idx,
            description=l.description,
            account_code=l.account_code,
            quantity=l.quantity,
            unit_price=l.unit_price,
            total_amount=line_tot
        ))

    pr_num = crud.get_next_sequence_number(db, "PR-2026", models.PurchaseRequisition, "pr_number")
    pr = models.PurchaseRequisition(
        pr_number=pr_num,
        pr_date=pr_in.pr_date,
        department=pr_in.department,
        status=status,
        total_amount=round(total_amt, 2),
        budget_override=False,
        created_by=created_by,
        approved_by=created_by if status == "Approved" else None,
        notes=pr_in.notes,
        lines=pr_lines
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr

@router.post("/prs/{pr_id}/convert-to-po", response_model=schemas.POResponse)
def convert_pr_endpoint(
    pr_id: int,
    vendor_code: str = Query(...),
    tax_code: str = Query("VAT-STD-5"),
    db: Session = Depends(get_db)
):
    try:
        po = crud.convert_pr_to_po(db, pr_id, vendor_code, tax_code)
        po.status = "Approved"
        po.approved_by = "Owner / Operations"
        db.commit()
        db.refresh(po)
        po.vendor_name = po.vendor.name if po.vendor else ""
        return po
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Purchase Orders
@router.get("/pos", response_model=List[schemas.POResponse])
def get_pos(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.PurchaseOrder)
    if status:
        q = q.filter(models.PurchaseOrder.status == status)
    pos = q.order_by(models.PurchaseOrder.id.desc()).all()
    # Populate vendor name
    for p in pos:
        p.vendor_name = p.vendor.name if p.vendor else ""
    return pos

@router.post("/pos", response_model=schemas.POResponse)
def create_po(
    po_in: schemas.POCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Operations"),
    db: Session = Depends(get_db)
):
    if not po_in.lines:
        raise HTTPException(status_code=400, detail="PO must have at least one line item")

    tax = db.query(models.TaxCode).filter(models.TaxCode.code == po_in.tax_code).first()
    tax_rate = tax.rate if tax else 5.0

    subtotal = 0.0
    tax_total = 0.0
    po_lines = []

    for idx, l in enumerate(po_in.lines, start=1):
        line_sub = round(l.quantity * l.unit_price, 2)
        line_tax = round(line_sub * (tax_rate / 100.0), 2)
        line_tot = round(line_sub + line_tax, 2)
        subtotal += line_sub
        tax_total += line_tax

        po_lines.append(models.POLine(
            line_no=idx,
            item_code=l.item_code,
            description=l.description,
            account_code=l.account_code,
            quantity=l.quantity,
            unit_price=l.unit_price,
            received_qty=0.0,
            invoiced_qty=0.0,
            line_subtotal=line_sub,
            tax_amount=line_tax,
            line_total=line_tot
        ))

    po_num = crud.get_next_sequence_number(db, "PO-2026", models.PurchaseOrder, "po_number")
    po = models.PurchaseOrder(
        po_number=po_num,
        pr_number=po_in.pr_number,
        po_date=po_in.po_date,
        delivery_date=po_in.delivery_date,
        vendor_code=po_in.vendor_code,
        tax_code=po_in.tax_code,
        subtotal=round(subtotal, 2),
        tax_amount=round(tax_total, 2),
        total_amount=round(subtotal + tax_total, 2),
        status=status,
        created_by=created_by,
        approved_by=created_by if status == "Approved" else None,
        notes=po_in.notes,
        lines=po_lines
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    po.vendor_name = po.vendor.name if po.vendor else ""
    return po

# Goods Receipt Notes
@router.get("/grns", response_model=List[schemas.GRNResponse])
def get_grns(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.GoodsReceiptNote)
    if status:
        q = q.filter(models.GoodsReceiptNote.status == status)
    grns = q.order_by(models.GoodsReceiptNote.id.desc()).all()
    for g in grns:
        g.total_amount = sum(l.line_amount for l in g.lines)
    return grns

@router.post("/grns", response_model=schemas.GRNResponse)
def create_grn(
    grn_in: schemas.GRNCreate,
    status: str = Query("Approved", description="Draft or Approved"),
    created_by: str = Query("Owner / Operations"),
    db: Session = Depends(get_db)
):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_number == grn_in.po_number).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if po.status not in ["Approved", "Partially Received"]:
        raise HTTPException(status_code=400, detail="GRN can only be raised against an Approved Purchase Order")

    if not grn_in.lines:
        raise HTTPException(status_code=400, detail="GRN must have at least one line item")

    grn_lines = []
    tot_amount = 0.0

    for l in grn_in.lines:
        amt = round(l.received_qty * l.unit_price, 2)
        tot_amount += amt
        grn_lines.append(models.GRNLine(
            po_line_id=l.po_line_id,
            item_code=l.item_code,
            account_code=l.account_code,
            description=l.description,
            received_qty=l.received_qty,
            unit_price=l.unit_price,
            line_amount=amt
        ))

    grn_num = crud.get_next_sequence_number(db, "GRN-2026", models.GoodsReceiptNote, "grn_number")
    grn = models.GoodsReceiptNote(
        grn_number=grn_num,
        po_number=grn_in.po_number,
        grn_date=grn_in.grn_date,
        vendor_delivery_ref=grn_in.vendor_delivery_ref,
        status="Draft" if status == "Draft" else "Pending Approval",
        created_by=created_by,
        notes=grn_in.notes,
        lines=grn_lines
    )
    db.add(grn)
    db.commit()
    db.refresh(grn)

    if status == "Approved":
        grn = crud.approve_grn_and_post_gl(db, grn.id, approver=created_by)

    grn.total_amount = round(sum(l.line_amount for l in grn.lines), 2)
    return grn
