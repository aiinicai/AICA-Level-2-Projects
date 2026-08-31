from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.dependencies import require_any_staff
from app.services.permission_service import assert_write
from app.services import card_qr_service, matching_engine
from app.models.user import User
from app.models.bank_transaction import BankTransaction
from app.models.card_qr_rec import CardQrReconciliation
from app.api.reports import parse_int_param, parse_date_param, parse_str_param

router = APIRouter(prefix="/api/card-qr", tags=["Card/QR Reconciliation"])

@router.get("")
def get_card_qr_records(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    recs = card_qr_service.get_card_qr_reconciliations(
        db, parse_int_param(branch_id), parse_date_param(start_date), parse_date_param(end_date), parse_str_param(status)
    )
    res = []
    for r in recs:
        res.append({
            "id": r.id,
            "branch_id": r.branch_id,
            "branch_name": r.branch.name if r.branch else "N/A",
            "sale_date": r.sale_date.strftime("%Y-%m-%d"),
            "card_qr_sales_amount": r.card_qr_sales_amount,
            "received_amount": r.received_amount,
            "difference": r.difference,
            "settlement_date": r.settlement_date.strftime("%Y-%m-%d") if r.settlement_date else None,
            "bank_reference": r.bank_reference,
            "bank_account": r.bank_account,
            "status": r.status,
            "match_method": r.match_method,
            "remarks": r.remarks
        })
    return res


@router.get("/settlement-matrix")
def get_card_qr_settlement_matrix(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    return card_qr_service.get_card_qr_settlement_matrix(
        db, parse_int_param(branch_id), parse_date_param(start_date), parse_date_param(end_date), parse_str_param(status)
    )


@router.post("/entry")
def save_card_qr_entry(
    branch_id: int = Body(...),
    sale_date: date = Body(...),
    card_qr_sales_amount: float = Body(0.0),
    received_amount: float = Body(0.0),
    remarks: Optional[str] = Body(None),
    original_branch_id: Optional[int] = Body(None),
    original_sale_date: Optional[date] = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    existing = db.query(CardQrReconciliation).filter(
        CardQrReconciliation.branch_id == branch_id,
        CardQrReconciliation.sale_date == sale_date,
    ).first()
    original = None
    if original_branch_id and original_sale_date and (original_branch_id, original_sale_date) != (branch_id, sale_date):
        original = db.query(CardQrReconciliation).filter(
            CardQrReconciliation.branch_id == original_branch_id,
            CardQrReconciliation.sale_date == original_sale_date,
        ).first()
    assert_write(user, "card_qr", bool(existing or original))
    rec = card_qr_service.save_manual_card_qr_entry(
        db, branch_id, sale_date, card_qr_sales_amount, received_amount, remarks,
        user=user,
        original_branch_id=original_branch_id,
        original_sale_date=original_sale_date,
    )
    return {
        "id": rec.id,
        "branch_id": rec.branch_id,
        "sale_date": rec.sale_date.strftime("%Y-%m-%d"),
        "card_qr_sales_amount": rec.card_qr_sales_amount,
        "received_amount": rec.received_amount,
        "difference": rec.difference,
        "status": rec.status,
    }


@router.post("/auto-match")
def auto_match_card_qr(
    tolerance_days: int = 3,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    assert_write(user, "card_qr", False)
    result = matching_engine.run_card_qr_auto_matching(db, tolerance_days, user=user)
    return result

@router.post("/manual-match")
def manual_match(
    card_qr_rec_id: int = Body(...),
    bank_tx_id: int = Body(...),
    reason: str = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    assert_write(user, "card_qr", True)
    try:
        rec = matching_engine.manual_match_card_qr(db, card_qr_rec_id, bank_tx_id, reason, user=user)
        return rec
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/unmatched-bank-txs")
def get_unmatched_bank_txs(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    txs = db.query(BankTransaction).filter(
        BankTransaction.is_matched == False,
        BankTransaction.credit_amount > 0
    ).order_by(BankTransaction.tx_date.desc()).limit(100).all()
    
    return [
        {
            "id": t.id,
            "tx_date": t.tx_date.strftime("%Y-%m-%d"),
            "description": t.description,
            "reference_no": t.reference_no,
            "credit_amount": t.credit_amount,
            "bank_account": t.bank_account
        }
        for t in txs
    ]
