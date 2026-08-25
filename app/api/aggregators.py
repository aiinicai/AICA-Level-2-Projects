from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Union
from datetime import date
from app.core.database import get_db
from app.core.dependencies import require_any_staff
from app.services.permission_service import assert_write
from app.services import aggregator_service, master_service
from app.models.user import User
def parse_int_param(val: Optional[Union[int, str]]) -> Optional[int]:
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        return int(val_str)
    except ValueError:
        return None

def parse_date_param(val: Optional[Union[date, str]]) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        return date.fromisoformat(val_str)
    except ValueError:
        return None

router = APIRouter(prefix="/api/aggregators", tags=["Online Aggregators"])

@router.get("/master")
def get_aggregators_list(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    return master_service.get_aggregators(db)

@router.get("/payout-breakup")
def get_payout_matrix(
    aggregator_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    a_id = parse_int_param(aggregator_id)
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    matrix = aggregator_service.get_aggregator_payout_matrix(db, a_id, b_id, s_dt, e_dt)
    return matrix

from app.models.settlement import SettlementBatch

@router.post("/batch")
def save_settlement_batch(
    batch_no: str = Body(...),
    aggregator_id: int = Body(...),
    branch_id: int = Body(...),
    period_start_date: date = Body(...),
    period_end_date: date = Body(...),
    gross_sales: float = Body(...),
    payout: float = Body(...),
    deductions: Optional[List[Dict[str, Any]]] = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    existing = db.query(SettlementBatch).filter(SettlementBatch.batch_no == batch_no).first()
    assert_write(user, "aggregators", bool(existing))
    batch = aggregator_service.create_or_update_settlement_batch(
        db=db,
        batch_no=batch_no,
        aggregator_id=aggregator_id,
        branch_id=branch_id,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        gross_sales=gross_sales,
        payout=payout,
        deductions_data=deductions,
        user=user
    )
    return batch

@router.put("/batch/{batch_id}")
def update_settlement_batch_endpoint(
    batch_id: int,
    gross_sales: float = Body(...),
    payout: float = Body(...),
    commission: float = Body(0.0),
    promotion: float = Body(0.0),
    tcs: float = Body(0.0),
    tds: float = Body(0.0),
    gst_9_5: float = Body(0.0),
    misc: float = Body(0.0),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    assert_write(user, "aggregators", True)
    batch = db.query(SettlementBatch).filter(SettlementBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Settlement batch not found.")

    deductions_data = [
        {"deduction_type": "COMMISSION", "description": "Online Platform Charges", "amount": commission},
        {"deduction_type": "PROMOTION", "description": "Business Promotion", "amount": promotion},
        {"deduction_type": "TCS", "description": "TCS", "amount": tcs},
        {"deduction_type": "TDS", "description": "TDS 194O", "amount": tds},
        {"deduction_type": "GST_9_5", "description": "GST Sec 9(5)", "amount": gst_9_5},
        {"deduction_type": "MISC", "description": "Miscellaneous Adjustments", "amount": misc}
    ]

    updated = aggregator_service.create_or_update_settlement_batch(
        db=db,
        batch_no=batch.batch_no,
        aggregator_id=batch.aggregator_id,
        branch_id=batch.branch_id,
        period_start_date=batch.period_start_date,
        period_end_date=batch.period_end_date,
        gross_sales=gross_sales,
        payout=payout,
        deductions_data=deductions_data,
        user=user
    )
    return updated

@router.delete("/batch/{batch_id}")
def delete_settlement_batch_endpoint(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    assert_write(user, "aggregators", True)
    success = aggregator_service.delete_settlement_batch(db, batch_id, user=user)
    if not success:
        raise HTTPException(status_code=404, detail="Settlement batch not found.")
    return {"message": f"Settlement batch {batch_id} deleted successfully!"}
