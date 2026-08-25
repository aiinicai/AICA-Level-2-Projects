from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import date
from app.core.database import get_db
from app.core.dependencies import require_any_staff
from app.services.permission_service import assert_write
from app.services import daybook_service
from app.models.user import User
from app.models.daily_sales import DailySale

router = APIRouter(prefix="/api/daybook", tags=["Day Book"])

@router.get("/consolidated")
def get_daybook(
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    rows = daybook_service.get_consolidated_daybook(db, branch_id, start_date, end_date)
    totals = daybook_service.get_daybook_totals(rows)
    return {"rows": rows, "totals": totals}


@router.post("/entry")
def save_daybook_entry(
    branch_id: int = Body(...),
    sale_date: date = Body(...),
    cash: float = Body(0.0),
    card_qr: float = Body(0.0),
    zomato: float = Body(0.0),
    swiggy: float = Body(0.0),
    dineout: float = Body(0.0),
    original_branch_id: Optional[int] = Body(None),
    original_sale_date: Optional[date] = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    already = db.query(DailySale).filter(
        DailySale.branch_id == branch_id, DailySale.sale_date == sale_date
    ).first()
    original = None
    if original_branch_id and original_sale_date and (original_branch_id, original_sale_date) != (branch_id, sale_date):
        original = db.query(DailySale).filter(
            DailySale.branch_id == original_branch_id, DailySale.sale_date == original_sale_date
        ).first()
    assert_write(user, "daybook", bool(already or original))
    return daybook_service.save_manual_daybook_entry(
        db, branch_id, sale_date, cash, card_qr, zomato, swiggy, dineout,
        user=user,
        original_branch_id=original_branch_id,
        original_sale_date=original_sale_date,
    )
