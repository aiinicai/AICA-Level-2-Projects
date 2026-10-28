import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud, seed_data, company_manager

router = APIRouter(prefix="/api", tags=["Approvals & System"])

class GlobalApprovalAction(BaseModel):
    module: str  # GL, PR, PO, GRN, AP-INV, AP-PMT, AR-INV, AR-RCPT
    document_id: int
    action: str  # "approve" or "reject"
    comment: Optional[str] = ""
    budget_override: Optional[bool] = False
    approved_by: Optional[str] = "Checker (Finance Manager)"

@router.get("/approvals/pending", response_model=List[schemas.ApprovalItemResponse])
def get_pending_approvals(db: Session = Depends(get_db)):
    return crud.get_all_pending_approvals(db)

@router.post("/approvals/action")
def process_approval_action(req: GlobalApprovalAction, db: Session = Depends(get_db)):
    if req.action == "reject" and not req.comment.strip():
        raise HTTPException(status_code=400, detail="Rejection comment is mandatory when rejecting a document")

    mod = req.module.upper()
    doc_id = req.document_id

    if mod == "GL":
        jv = db.query(models.JournalVoucher).filter(models.JournalVoucher.id == doc_id).first()
        if not jv:
            raise HTTPException(status_code=404, detail="Journal voucher not found")
        if req.action == "approve":
            jv.status = "Approved"
            jv.approved_by = req.approved_by
            jv.approved_at = datetime.datetime.utcnow()
        else:
            jv.status = "Rejected"
            jv.rejection_comment = req.comment
        db.commit()
        return {"status": "success", "message": f"GL Voucher {jv.voucher_no} {req.action}d"}

    elif mod == "PR":
        pr = db.query(models.PurchaseRequisition).filter(models.PurchaseRequisition.id == doc_id).first()
        if not pr:
            raise HTTPException(status_code=404, detail="PR not found")
        if req.action == "approve":
            pr.status = "Approved"
            pr.approved_by = req.approved_by
            if req.budget_override:
                pr.budget_override = True
        else:
            pr.status = "Rejected"
            pr.rejection_comment = req.comment
        db.commit()
        return {"status": "success", "message": f"PR {pr.pr_number} {req.action}d"}

    elif mod == "PO":
        po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == doc_id).first()
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        if req.action == "approve":
            po.status = "Approved"
            po.approved_by = req.approved_by
            crud.apply_po_inventory_receipt(db, po)
        else:
            po.status = "Rejected"
            po.rejection_comment = req.comment
        db.commit()
        return {"status": "success", "message": f"PO {po.po_number} {req.action}d"}

    elif mod == "GRN":
        if req.action == "approve":
            grn = crud.approve_grn_and_post_gl(db, doc_id, approver=req.approved_by)
            return {"status": "success", "message": f"GRN {grn.grn_number} approved and GL voucher {grn.voucher_no} posted"}
        else:
            grn = db.query(models.GoodsReceiptNote).filter(models.GoodsReceiptNote.id == doc_id).first()
            if not grn:
                raise HTTPException(status_code=404, detail="GRN not found")
            grn.status = "Rejected"
            grn.rejection_comment = req.comment
            db.commit()
            return {"status": "success", "message": f"GRN {grn.grn_number} rejected"}

    elif mod in ["AP-INV", "AP_INV"]:
        if req.action == "approve":
            inv = crud.approve_ap_invoice_and_post_gl(db, doc_id, approver=req.approved_by)
            return {"status": "success", "message": f"AP Invoice {inv.invoice_number} approved and GL voucher {inv.voucher_no} posted"}
        else:
            inv = db.query(models.APInvoice).filter(models.APInvoice.id == doc_id).first()
            if not inv:
                raise HTTPException(status_code=404, detail="AP Invoice not found")
            inv.status = "Rejected"
            inv.rejection_comment = req.comment
            db.commit()
            return {"status": "success", "message": f"AP Invoice {inv.invoice_number} rejected"}

    elif mod in ["AP-PMT", "AP_PMT"]:
        if req.action == "approve":
            pmt = crud.approve_ap_payment_and_post_gl(db, doc_id, approver=req.approved_by)
            return {"status": "success", "message": f"AP Payment {pmt.payment_number} approved and GL voucher {pmt.voucher_no} posted"}
        else:
            pmt = db.query(models.APPayment).filter(models.APPayment.id == doc_id).first()
            if not pmt:
                raise HTTPException(status_code=404, detail="AP Payment not found")
            pmt.status = "Rejected"
            pmt.rejection_comment = req.comment
            db.commit()
            return {"status": "success", "message": f"AP Payment {pmt.payment_number} rejected"}

    elif mod in ["AR-INV", "AR_INV"]:
        if req.action == "approve":
            inv = crud.approve_ar_invoice_and_post_gl(db, doc_id, approver=req.approved_by)
            return {"status": "success", "message": f"AR Invoice {inv.invoice_number} approved and GL voucher {inv.voucher_no} posted"}
        else:
            inv = db.query(models.ARInvoice).filter(models.ARInvoice.id == doc_id).first()
            if not inv:
                raise HTTPException(status_code=404, detail="AR Invoice not found")
            inv.status = "Rejected"
            inv.rejection_comment = req.comment
            db.commit()
            return {"status": "success", "message": f"AR Invoice {inv.invoice_number} rejected"}

    elif mod in ["AR-RCPT", "AR_RCPT"]:
        if req.action == "approve":
            rcpt = crud.approve_ar_receipt_and_post_gl(db, doc_id, approver=req.approved_by)
            return {"status": "success", "message": f"AR Receipt {rcpt.receipt_number} approved and GL voucher {rcpt.voucher_no} posted"}
        else:
            rcpt = db.query(models.ARReceipt).filter(models.ARReceipt.id == doc_id).first()
            if not rcpt:
                raise HTTPException(status_code=404, detail="AR Receipt not found")
            rcpt.status = "Rejected"
            rcpt.rejection_comment = req.comment
            db.commit()
            return {"status": "success", "message": f"AR Receipt {rcpt.receipt_number} rejected"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown module {req.module}")

class DatabaseResetRequest(BaseModel):
    pin: str

@router.post("/system/reset-clean")
@router.post("/system/reset-db")
def reset_clean_database(req: DatabaseResetRequest, db: Session = Depends(get_db)):
    pin_str = str(req.pin).strip()
    active_comp = company_manager.get_active_company()
    if not company_manager.verify_company_pin(active_comp["id"], pin_str):
        raise HTTPException(
            status_code=401,
            detail="Invalid 4-digit security PIN for this company. Database reset aborted."
        )
    seed_data.init_clean_database(db, force_reset=True)
    return {
        "status": "success",
        "message": f"Database for '{active_comp.get('company_name')}' was successfully reset to a clean production slate with ZERO transactions! Ready for your company data and opening balance migration."
    }

@router.post("/system/seed-demo")
def seed_demo_database(req: DatabaseResetRequest, db: Session = Depends(get_db)):
    pin_str = str(req.pin).strip()
    active_comp = company_manager.get_active_company()
    if not company_manager.verify_company_pin(active_comp["id"], pin_str):
        raise HTTPException(
            status_code=401,
            detail="Invalid 4-digit security PIN for this company. Demo load aborted."
        )
    seed_data.seed_demo_data(db)
    return {
        "status": "success",
        "message": f"Sample supermarket demo dataset loaded for '{active_comp.get('company_name')}' with retail products, vendors, customers, and transactions!"
    }


