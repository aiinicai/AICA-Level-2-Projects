from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.card_qr_rec import CardQrReconciliation
from app.models.daily_sales import DailySale
from app.models.payment_channel import PaymentChannel
from app.models.branch import Branch

def sync_card_qr_sales_from_daybook(db: Session, branch_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None):
    # Find channels representing Card/QR
    card_channels = db.query(PaymentChannel).filter(
        PaymentChannel.is_active == True,
        PaymentChannel.channel_type.in_(["BANK", "OTHER"])
    ).all()
    channel_ids = [c.id for c in card_channels if "card" in c.name.lower() or "qr" in c.name.lower() or "upi" in c.name.lower()]

    if not channel_ids:
        channel_ids = [c.id for c in card_channels]

    # Query daily sales grouped by branch and date
    query = db.query(
        DailySale.branch_id,
        DailySale.sale_date,
        DailySale.amount
    ).filter(DailySale.payment_channel_id.in_(channel_ids))

    if branch_id:
        query = query.filter(DailySale.branch_id == branch_id)
    if start_date:
        query = query.filter(DailySale.sale_date >= start_date)
    if end_date:
        query = query.filter(DailySale.sale_date <= end_date)

    sales = query.all()

    # Aggregate by (branch_id, sale_date)
    matrix: Dict[tuple, float] = {}
    for b_id, s_date, amt in sales:
        key = (b_id, s_date)
        matrix[key] = matrix.get(key, 0.0) + float(amt or 0.0)

    for (b_id, s_date), total_amt in matrix.items():
        rec = db.query(CardQrReconciliation).filter(
            CardQrReconciliation.branch_id == b_id,
            CardQrReconciliation.sale_date == s_date
        ).first()

        if not rec:
            rec = CardQrReconciliation(
                branch_id=b_id,
                sale_date=s_date,
                card_qr_sales_amount=total_amt,
                received_amount=0.0,
                difference=total_amt,
                status="PENDING"
            )
            db.add(rec)
        else:
            rec.card_qr_sales_amount = total_amt
            rec.difference = round(rec.card_qr_sales_amount - rec.received_amount, 2)
            if rec.status == "PENDING" and rec.received_amount > 0:
                rec.status = "MATCHED" if abs(rec.difference) < 0.01 else "DIFFERENCE"

    db.commit()


def save_manual_card_qr_entry(
    db: Session,
    branch_id: int,
    sale_date: date,
    card_qr_sales_amount: float,
    received_amount: float = 0.0,
    remarks: Optional[str] = None,
    user=None,
    original_branch_id: Optional[int] = None,
    original_sale_date: Optional[date] = None,
) -> CardQrReconciliation:
    from app.services.daybook_service import upsert_channel_amount

    moving = bool(
        original_branch_id
        and original_sale_date
        and (original_branch_id, original_sale_date) != (branch_id, sale_date)
    )
    if moving:
        db.query(CardQrReconciliation).filter(
            CardQrReconciliation.branch_id == original_branch_id,
            CardQrReconciliation.sale_date == original_sale_date,
        ).delete(synchronize_session=False)
        upsert_channel_amount(db, original_branch_id, original_sale_date, "CARD_QR", 0)

    upsert_channel_amount(db, branch_id, sale_date, "CARD_QR", card_qr_sales_amount)
    rec = db.query(CardQrReconciliation).filter(
        CardQrReconciliation.branch_id == branch_id,
        CardQrReconciliation.sale_date == sale_date,
    ).first()
    if not rec:
        rec = CardQrReconciliation(branch_id=branch_id, sale_date=sale_date)
        db.add(rec)
    rec.card_qr_sales_amount = float(card_qr_sales_amount or 0)
    rec.received_amount = float(received_amount or 0)
    rec.difference = round(rec.card_qr_sales_amount - rec.received_amount, 2)
    rec.match_method = "MANUAL"
    if remarks is not None:
        rec.remarks = remarks
    if rec.received_amount <= 0:
        rec.status = "PENDING"
    elif abs(rec.difference) < 0.01:
        rec.status = "MATCHED"
    else:
        rec.status = "DIFFERENCE"
    db.commit()
    db.refresh(rec)
    return rec


def get_card_qr_reconciliations(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None
) -> List[CardQrReconciliation]:
    sync_card_qr_sales_from_daybook(db, branch_id, start_date, end_date)

    query = db.query(CardQrReconciliation)
    if branch_id:
        query = query.filter(CardQrReconciliation.branch_id == branch_id)
    if start_date:
        query = query.filter(CardQrReconciliation.sale_date >= start_date)
    if end_date:
        query = query.filter(CardQrReconciliation.sale_date <= end_date)
    if status:
        query = query.filter(CardQrReconciliation.status == status)

    return query.order_by(CardQrReconciliation.sale_date.desc()).all()


def get_card_qr_settlement_matrix(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    recs = get_card_qr_reconciliations(db, branch_id, start_date, end_date, status)
    month_q = db.query(CardQrReconciliation.sale_date)
    if branch_id:
        month_q = month_q.filter(CardQrReconciliation.branch_id == branch_id)
    available_months = sorted({
        d.strftime("%Y-%m") for (d,) in month_q.all() if d
    })

    branch_map: Dict[int, Dict[str, Any]] = {}
    dates = []
    seen_dates = set()
    cells: Dict[str, Dict[int, Dict[str, Any]]] = {}

    for r in sorted(recs, key=lambda x: (x.sale_date, x.branch.name if x.branch else "")):
        key = r.sale_date.strftime("%Y-%m-%d")
        if key not in seen_dates:
            seen_dates.add(key)
            dates.append(key)
        if r.branch_id not in branch_map:
            branch_map[r.branch_id] = {
                "id": r.branch_id,
                "name": r.branch.name if r.branch else "Branch",
                "code": r.branch.code if r.branch else "",
            }
        cells.setdefault(key, {})[str(r.branch_id)] = {
            "id": r.id,
            "sales": round(float(r.card_qr_sales_amount or 0), 2),
            "received": round(float(r.received_amount or 0), 2),
            "difference": round(float(r.difference or 0), 2),
            "status": r.status,
            "match_method": r.match_method,
            "settlement_date": r.settlement_date.strftime("%Y-%m-%d") if r.settlement_date else None,
            "bank_reference": r.bank_reference,
            "bank_account": r.bank_account,
        }

    branches = list(branch_map.values())
    totals = {}
    for b in branches:
        sales = received = difference = 0.0
        for day_cells in cells.values():
            cell = day_cells.get(str(b["id"]))
            if not cell:
                continue
            sales += cell["sales"]
            received += cell["received"]
            difference += cell["difference"]
        totals[str(b["id"])] = {
            "sales": round(sales, 2),
            "received": round(received, 2),
            "difference": round(difference, 2),
        }

    from app.models.bank_transaction import BankTransaction
    unmatched_bank = db.query(BankTransaction).filter(
        BankTransaction.is_matched == False,
        BankTransaction.credit_amount > 0
    ).count()

    return {
        "branches": branches,
        "dates": dates,
        "cells": cells,
        "totals": totals,
        "available_months": available_months,
        "unmatched_bank_count": unmatched_bank,
    }
