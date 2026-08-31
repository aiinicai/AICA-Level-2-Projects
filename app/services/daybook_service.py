from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.daily_sales import DailySale
from app.models.branch import Branch
from app.models.payment_channel import PaymentChannel
from app.models.cash_rec import CashReconciliation

def get_consolidated_daybook(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    aggregate_branches: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    # Get all active payment channels
    channels = db.query(PaymentChannel).filter(PaymentChannel.is_active == True).order_by(PaymentChannel.id).all()
    channel_ids = [c.id for c in channels]
    channel_dict = {c.id: c.name for c in channels}

    # Query daily sales
    query = db.query(
        DailySale.branch_id,
        DailySale.sale_date,
        DailySale.payment_channel_id,
        func.sum(DailySale.amount).label("total_amount")
    ).group_by(DailySale.branch_id, DailySale.sale_date, DailySale.payment_channel_id)

    if branch_id:
        query = query.filter(DailySale.branch_id == branch_id)
    if start_date:
        query = query.filter(DailySale.sale_date >= start_date)
    if end_date:
        query = query.filter(DailySale.sale_date <= end_date)

    results = query.all()

    # Get branches map
    branches = db.query(Branch).all()
    branch_map = {b.id: b.name for b in branches}

    # Structure data by (branch_id, sale_date)
    matrix: Dict[tuple, Dict[str, Any]] = {}
    for b_id, s_date, ch_id, amt in results:
        key = (b_id, s_date)
        if key not in matrix:
            matrix[key] = {
                "branch_id": b_id,
                "branch_name": branch_map.get(b_id, "Unknown"),
                "date": s_date,
                "cash": 0.0,
                "card_qr": 0.0,
                "zomato": 0.0,
                "swiggy": 0.0,
                "dineout": 0.0,
                "other_channels": 0.0,
                "online_payment": 0.0,
                "total_sales": 0.0,
                "cash_balance": 0.0,
                "opening_balance": 0.0,
                "status": "COMPLETED",
                "is_aggregate": False,
            }
        
        ch_name = channel_dict.get(ch_id, "").lower()
        amount_val = float(amt or 0.0)
        
        if "cash" in ch_name and "zomato" not in ch_name and "swiggy" not in ch_name:
            matrix[key]["cash"] += amount_val
        elif "card" in ch_name or "qr" in ch_name or "upi" in ch_name:
            matrix[key]["card_qr"] += amount_val
            matrix[key]["online_payment"] += amount_val
        elif "zomato" in ch_name:
            matrix[key]["zomato"] += amount_val
            matrix[key]["online_payment"] += amount_val
        elif "swiggy" in ch_name:
            matrix[key]["swiggy"] += amount_val
            matrix[key]["online_payment"] += amount_val
        elif "dineout" in ch_name:
            matrix[key]["dineout"] += amount_val
            matrix[key]["online_payment"] += amount_val
        else:
            matrix[key]["other_channels"] += amount_val
            matrix[key]["online_payment"] += amount_val

        matrix[key]["total_sales"] += amount_val

    # Fetch cash reconciliation closing balances where available
    for (b_id, s_date), item in matrix.items():
        cash_rec = db.query(CashReconciliation).filter(
            CashReconciliation.branch_id == b_id,
            CashReconciliation.rec_date == s_date
        ).first()
        if cash_rec:
            item["opening_balance"] = float(cash_rec.opening_balance or 0)
            item["cash_balance"] = cash_rec.actual_closing_balance
            item["status"] = cash_rec.status
        else:
            item["opening_balance"] = 0.0
            item["cash_balance"] = 0.0
            item["status"] = "PENDING"

    # Convert to sorted list by date desc
    daybook_rows = list(matrix.values())
    daybook_rows.sort(key=lambda x: (x["date"], x["branch_name"]), reverse=True)
    should_aggregate = aggregate_branches if aggregate_branches is not None else not branch_id
    if should_aggregate:
        return aggregate_daybook_by_date(daybook_rows)
    return daybook_rows


def _roll_day_status(statuses: List[str]) -> str:
    if any(status == "DIFFERENCE" for status in statuses):
        return "DIFFERENCE"
    if statuses and all(status == "RECONCILED" for status in statuses):
        return "RECONCILED"
    return "PENDING"


def aggregate_daybook_by_date(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Any, Dict[str, Any]] = {}
    money_fields = (
        "cash", "card_qr", "zomato", "swiggy", "dineout",
        "other_channels", "online_payment", "total_sales",
    )
    for row in rows:
        key = row["date"]
        if key not in grouped:
            grouped[key] = {
                "branch_id": None,
                "branch_name": "All Branches",
                "date": row["date"],
                "cash": 0.0,
                "card_qr": 0.0,
                "zomato": 0.0,
                "swiggy": 0.0,
                "dineout": 0.0,
                "other_channels": 0.0,
                "online_payment": 0.0,
                "total_sales": 0.0,
                "cash_balance": 0.0,
                "opening_balance": 0.0,
                "status": "PENDING",
                "is_aggregate": True,
                "_statuses": [],
            }
        item = grouped[key]
        for field in money_fields:
            item[field] += float(row.get(field) or 0)
        opening = float(row.get("opening_balance") or 0)
        item["opening_balance"] += opening
        item["cash_balance"] += opening
        item["_statuses"].append(row.get("status") or "PENDING")
    out = []
    for item in grouped.values():
        item["status"] = _roll_day_status(item.pop("_statuses"))
        out.append(item)
    out.sort(key=lambda x: x["date"], reverse=True)
    return out

def upsert_channel_amount(
    db: Session,
    branch_id: int,
    sale_date: date,
    channel_code: str,
    amount: float,
) -> None:
    channel = (
        db.query(PaymentChannel)
        .filter(PaymentChannel.code == channel_code, PaymentChannel.is_active == True)
        .first()
    )
    if not channel:
        return
    rec = (
        db.query(DailySale)
        .filter(
            DailySale.branch_id == branch_id,
            DailySale.sale_date == sale_date,
            DailySale.payment_channel_id == channel.id,
        )
        .first()
    )
    if rec:
        rec.amount = float(amount or 0)
        return
    db.add(DailySale(
        branch_id=branch_id,
        sale_date=sale_date,
        payment_channel_id=channel.id,
        amount=float(amount or 0),
    ))


def delete_daybook_day(db: Session, branch_id: int, sale_date: date) -> None:
    db.query(DailySale).filter(
        DailySale.branch_id == branch_id,
        DailySale.sale_date == sale_date,
    ).delete(synchronize_session=False)
    from app.models.card_qr_rec import CardQrReconciliation
    from app.services.cash_service import delete_cash_reconciliation
    delete_cash_reconciliation(db, branch_id, sale_date)
    db.query(CardQrReconciliation).filter(
        CardQrReconciliation.branch_id == branch_id,
        CardQrReconciliation.sale_date == sale_date,
    ).delete(synchronize_session=False)
    db.flush()


def save_manual_daybook_entry(
    db: Session,
    branch_id: int,
    sale_date: date,
    cash: float = 0.0,
    card_qr: float = 0.0,
    zomato: float = 0.0,
    swiggy: float = 0.0,
    dineout: float = 0.0,
    user=None,
    original_branch_id: Optional[int] = None,
    original_sale_date: Optional[date] = None,
) -> Dict[str, Any]:
    moving = bool(
        original_branch_id
        and original_sale_date
        and (original_branch_id, original_sale_date) != (branch_id, sale_date)
    )
    if moving:
        delete_daybook_day(db, original_branch_id, original_sale_date)
        from app.services.attendance_service import replace_salary_advances_for_date
        replace_salary_advances_for_date(db, original_branch_id, original_sale_date, [])
    upsert_channel_amount(db, branch_id, sale_date, "CASH", cash)
    upsert_channel_amount(db, branch_id, sale_date, "CARD_QR", card_qr)
    upsert_channel_amount(db, branch_id, sale_date, "ZOMATO", zomato)
    upsert_channel_amount(db, branch_id, sale_date, "SWIGGY", swiggy)
    upsert_channel_amount(db, branch_id, sale_date, "DINEOUT", dineout)
    db.commit()
    from app.services.cash_service import post_daybook_to_related_tabs
    post_daybook_to_related_tabs(db, branch_id, sale_date, sale_date, user=user)
    rows = get_consolidated_daybook(db, branch_id, sale_date, sale_date)
    return rows[0] if rows else {"branch_id": branch_id, "date": sale_date}


def get_daybook_totals(daybook_rows: List[Dict[str, Any]]) -> Dict[str, float]:
    totals = {
        "cash": sum(r["cash"] for r in daybook_rows),
        "card_qr": sum(r["card_qr"] for r in daybook_rows),
        "zomato": sum(r["zomato"] for r in daybook_rows),
        "swiggy": sum(r["swiggy"] for r in daybook_rows),
        "dineout": sum(r["dineout"] for r in daybook_rows),
        "other_channels": sum(r["other_channels"] for r in daybook_rows),
        "online_payment": sum(r["online_payment"] for r in daybook_rows),
        "total_sales": sum(r["total_sales"] for r in daybook_rows),
        "cash_balance": sum(float(r.get("cash_balance") or 0) for r in daybook_rows),
    }
    return totals
