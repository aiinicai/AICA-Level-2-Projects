from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.dependencies import require_any_staff
from app.services.permission_service import assert_write
from app.schemas.cash_rec import CashRecCreateUpdate
from app.services import cash_service
from app.services.attendance_service import replace_salary_advances_for_date, salary_advances_grouped
from app.models.cash_rec import CashReconciliation
from app.models.user import User

router = APIRouter(prefix="/api/cash-rec", tags=["Cash Reconciliation"])

@router.get("")
def get_cash_reconciliations(
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    cash_service.sync_cash_recs_from_daybook(
        db, branch_id, start_date, end_date, user=user, create_missing=False
    )
    query = db.query(CashReconciliation)
    if branch_id:
        query = query.filter(CashReconciliation.branch_id == branch_id)
    if start_date:
        query = query.filter(CashReconciliation.rec_date >= start_date)
    if end_date:
        query = query.filter(CashReconciliation.rec_date <= end_date)

    recs = query.order_by(CashReconciliation.rec_date.desc()).all()
    advances = salary_advances_grouped(
        db,
        [r.branch_id for r in recs],
        [r.rec_date for r in recs],
    )

    res = []
    for r in recs:
        res.append({
            "id": r.id,
            "branch_id": r.branch_id,
            "branch_name": r.branch.name if r.branch else "N/A",
            "rec_date": r.rec_date.strftime("%Y-%m-%d"),
            "opening_balance": r.opening_balance,
            "cash_sale": r.cash_sale,
            "site_expenses_inv_rec": r.site_expenses_inv_rec,
            "site_expenses_inv_not_rec": r.site_expenses_inv_not_rec,
            "advance_salary_1_5": r.advance_salary_1_5,
            "advance_salary_6_15": r.advance_salary_6_15,
            "advance_salary_16_31": r.advance_salary_16_31,
            "transfer_base_kitchen": r.transfer_base_kitchen,
            "service_charge": r.service_charge,
            "expected_closing_balance": r.expected_closing_balance,
            "actual_closing_balance": r.actual_closing_balance,
            "difference": r.difference,
            "status": r.status,
            "remarks": r.remarks,
            "salary_advance_splits": advances.get((r.branch_id, r.rec_date), []),
        })
    return res

@router.post("")
def save_cash_reconciliation(
    data: CashRecCreateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    existing = db.query(CashReconciliation).filter(
        CashReconciliation.branch_id == data.branch_id,
        CashReconciliation.rec_date == data.rec_date,
    ).first()
    original_branch_id = data.original_branch_id
    original_rec_date = data.original_rec_date
    moving = bool(
        original_branch_id
        and original_rec_date
        and (original_branch_id, original_rec_date) != (data.branch_id, data.rec_date)
    )
    original = None
    if moving:
        original = db.query(CashReconciliation).filter(
            CashReconciliation.branch_id == original_branch_id,
            CashReconciliation.rec_date == original_rec_date,
        ).first()
    assert_write(user, "cash_rec", bool(existing or original))
    payload = data.dict(exclude_unset=True)
    splits = payload.pop("salary_advance_splits", None)
    payload.pop("original_branch_id", None)
    payload.pop("original_rec_date", None)
    if moving:
        cash_service.delete_cash_reconciliation(db, original_branch_id, original_rec_date)
    rec = cash_service.create_or_update_cash_reconciliation(
        db,
        branch_id=data.branch_id,
        rec_date=data.rec_date,
        data=payload,
        user=user
    )
    if moving:
        replace_salary_advances_for_date(
            db, original_branch_id, original_rec_date, [], source="CASH_REC"
        )
    if splits is not None:
        replace_salary_advances_for_date(
            db, data.branch_id, data.rec_date, splits, source="CASH_REC"
        )
    return rec
