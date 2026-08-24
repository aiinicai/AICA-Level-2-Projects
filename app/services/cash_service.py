from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.cash_rec import CashReconciliation, CashTransaction
from app.models.branch import Branch
from app.models.daily_sales import DailySale
from app.models.payment_channel import PaymentChannel
from app.services.audit_service import log_action

def get_salary_advance_bucket(transaction_date: date) -> str:
    day = transaction_date.day
    if 1 <= day <= 5:
        return "SALARY_ADV_1_5"
    elif 6 <= day <= 15:
        return "SALARY_ADV_6_15"
    else:
        return "SALARY_ADV_16_31"

def get_previous_day_closing_balance(db: Session, branch_id: int, target_date: date) -> float:
    prev_date = target_date - timedelta(days=1)
    prev_rec = db.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch_id,
        CashReconciliation.rec_date == prev_date
    ).first()
    
    if prev_rec:
        return prev_rec.actual_closing_balance
    
    # If no previous day rec exists, check any latest rec before target_date
    latest_rec = db.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch_id,
        CashReconciliation.rec_date < target_date
    ).order_by(CashReconciliation.rec_date.desc()).first()

    if latest_rec:
        return latest_rec.actual_closing_balance

    # Default to branch opening cash balance
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    return branch.opening_cash_balance if branch else 0.0

def get_linked_cash_sale_amount(db: Session, branch_id: int, rec_date: date) -> float:
    # Query cash channels
    cash_channels = db.query(PaymentChannel).filter(
        PaymentChannel.is_active == True,
        PaymentChannel.channel_type == "CASH"
    ).all()
    channel_ids = [c.id for c in cash_channels]

    if not channel_ids:
        # Fallback to any channel with 'cash' in name
        all_channels = db.query(PaymentChannel).filter(PaymentChannel.is_active == True).all()
        channel_ids = [c.id for c in all_channels if "cash" in c.name.lower() and "zomato" not in c.name.lower()]

    sales = db.query(DailySale).filter(
        DailySale.branch_id == branch_id,
        DailySale.sale_date == rec_date,
        DailySale.payment_channel_id.in_(channel_ids)
    ).all()

    return sum(s.amount for s in sales)

def calculate_cash_reconciliation_equation(rec: CashReconciliation) -> Dict[str, float]:
    expected = (
        (rec.opening_balance or 0.0) +
        (rec.cash_sale or 0.0) -
        (rec.site_expenses_inv_rec or 0.0) -
        (rec.site_expenses_inv_not_rec or 0.0) -
        (rec.advance_salary_1_5 or 0.0) -
        (rec.advance_salary_6_15 or 0.0) -
        (rec.advance_salary_16_31 or 0.0) -
        (rec.transfer_base_kitchen or 0.0) +
        (rec.service_charge or 0.0) +
        (rec.other_adjustments or 0.0)
    )
    expected = round(expected, 2)
    diff = round((rec.actual_closing_balance or 0.0) - expected, 2)
    return {"expected_closing_balance": expected, "difference": diff}

def delete_cash_reconciliation(db: Session, branch_id: int, rec_date: date) -> bool:
    rec = db.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch_id,
        CashReconciliation.rec_date == rec_date,
    ).first()
    if not rec:
        return False
    db.query(CashTransaction).filter(
        CashTransaction.cash_reconciliation_id == rec.id
    ).delete(synchronize_session=False)
    db.delete(rec)
    db.flush()
    return True


def create_or_update_cash_reconciliation(
    db: Session,
    branch_id: int,
    rec_date: date,
    data: Dict[str, Any],
    user=None
) -> CashReconciliation:
    rec = db.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch_id,
        CashReconciliation.rec_date == rec_date
    ).first()

    # Automatically set opening balance if not provided
    if "opening_balance" not in data or data["opening_balance"] is None:
        data["opening_balance"] = get_previous_day_closing_balance(db, branch_id, rec_date)

    # Automatically link cash sale
    data["cash_sale"] = get_linked_cash_sale_amount(db, branch_id, rec_date)

    if not rec:
        rec = CashReconciliation(branch_id=branch_id, rec_date=rec_date)
        db.add(rec)

    old_values = {"expected": rec.expected_closing_balance, "actual": rec.actual_closing_balance, "diff": rec.difference} if rec.id else None

    # Update attributes
    for key, val in data.items():
        if hasattr(rec, key):
            setattr(rec, key, val)

    # Recalculate equation
    eq_res = calculate_cash_reconciliation_equation(rec)
    rec.expected_closing_balance = eq_res["expected_closing_balance"]
    rec.difference = eq_res["difference"]

    if abs(rec.difference) < 0.01:
        rec.status = "RECONCILED"
    else:
        rec.status = "DIFFERENCE"

    db.commit()
    db.refresh(rec)

    log_action(db, "SAVE_CASH_REC", "CashReconciliation", rec.id, old_values, {
        "expected": rec.expected_closing_balance,
        "actual": rec.actual_closing_balance,
        "diff": rec.difference,
        "status": rec.status
    }, user=user)

    return rec


def sync_cash_recs_from_daybook(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user=None,
    create_missing: bool = True,
) -> int:
    """Create or refresh Cash Rec rows from Day Book cash sales."""
    query = db.query(DailySale.branch_id, DailySale.sale_date).distinct()
    if branch_id:
        query = query.filter(DailySale.branch_id == branch_id)
    if start_date:
        query = query.filter(DailySale.sale_date >= start_date)
    if end_date:
        query = query.filter(DailySale.sale_date <= end_date)

    pairs = sorted(query.all(), key=lambda item: (item[0], item[1]))
    posted = 0
    for b_id, rec_date in pairs:
        cash_sale = get_linked_cash_sale_amount(db, b_id, rec_date)
        rec = db.query(CashReconciliation).filter(
            CashReconciliation.branch_id == b_id,
            CashReconciliation.rec_date == rec_date
        ).first()
        is_new = rec is None
        if is_new and not create_missing:
            continue
        if is_new:
            rec = CashReconciliation(
                branch_id=b_id,
                rec_date=rec_date,
                opening_balance=get_previous_day_closing_balance(db, b_id, rec_date),
                remarks="Auto-posted from Day Book"
            )
            db.add(rec)
        rec.cash_sale = cash_sale
        eq = calculate_cash_reconciliation_equation(rec)
        rec.expected_closing_balance = eq["expected_closing_balance"]
        rec.difference = eq["difference"]
        counted = abs(float(rec.actual_closing_balance or 0)) > 0.009
        if is_new and not counted:
            rec.status = "PENDING"
        elif abs(rec.difference) < 0.01:
            rec.status = "RECONCILED"
        else:
            rec.status = "DIFFERENCE"
        posted += 1

    if posted:
        db.commit()
        log_action(db, "SYNC_CASH_FROM_DAYBOOK", "CashReconciliation", None, None, {
            "posted": posted, "branch_id": branch_id
        }, user=user)
    return posted


def post_daybook_to_related_tabs(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user=None
) -> Dict[str, int]:
    from app.services.card_qr_service import sync_card_qr_sales_from_daybook
    cash_n = sync_cash_recs_from_daybook(db, branch_id, start_date, end_date, user=user)
    sync_card_qr_sales_from_daybook(db, branch_id, start_date, end_date)
    return {"cash_recs": cash_n}
