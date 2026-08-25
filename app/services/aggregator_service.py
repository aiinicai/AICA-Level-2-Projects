from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.settlement import SettlementBatch, AggregatorDeduction
from app.models.aggregator import Aggregator
from app.models.branch import Branch
from app.models.accounting_head import AccountingHead
from app.models.daily_sales import DailySale
from app.models.payment_channel import PaymentChannel
from app.services.audit_service import log_action

def get_aggregator_sales_for_period(
    db: Session,
    aggregator_id: int,
    branch_id: int,
    start_date: date,
    end_date: date
) -> float:
    aggregator = db.query(Aggregator).filter(Aggregator.id == aggregator_id).first()
    if not aggregator:
        return 0.0

    channels = db.query(PaymentChannel).filter(
        PaymentChannel.is_active == True,
        PaymentChannel.name.ilike(f"%{aggregator.code}%") | PaymentChannel.name.ilike(f"%{aggregator.name}%")
    ).all()
    channel_ids = [c.id for c in channels]

    if not channel_ids:
        return 0.0

    sales = db.query(DailySale).filter(
        DailySale.branch_id == branch_id,
        DailySale.payment_channel_id.in_(channel_ids),
        DailySale.sale_date >= start_date,
        DailySale.sale_date <= end_date
    ).all()

    return sum(s.amount for s in sales)

def calculate_settlement_batch_totals(batch: SettlementBatch) -> Dict[str, float]:
    # Sum actual deductions (Online Platform Charges, Business Promotion, TCS, TDS, Misc) EXCLUDING GST 9(5) and Packing
    actual_deduction_types = {"COMMISSION", "PROMOTION", "TCS", "TDS", "MISC"}
    total_deductions = sum(d.amount for d in batch.deductions if d.deduction_type in actual_deduction_types)
    actual_diff = round((batch.gross_sales or 0.0) - (batch.payout or 0.0), 2)
    diff_adj = round(actual_diff - total_deductions, 2)

    return {
        "total_deductions": round(total_deductions, 2),
        "actual_difference": actual_diff,
        "difference_adjustment": diff_adj
    }

def create_or_update_settlement_batch(
    db: Session,
    batch_no: str,
    aggregator_id: int,
    branch_id: int,
    period_start_date: date,
    period_end_date: date,
    gross_sales: float,
    payout: float,
    settlement_date: Optional[date] = None,
    deductions_data: Optional[List[Dict[str, Any]]] = None,
    import_batch_id: Optional[int] = None,
    user=None
) -> SettlementBatch:
    batch = db.query(SettlementBatch).filter(
        SettlementBatch.aggregator_id == aggregator_id,
        SettlementBatch.branch_id == branch_id,
        SettlementBatch.period_start_date == period_start_date,
        SettlementBatch.period_end_date == period_end_date
    ).first()

    if not batch:
        batch = SettlementBatch(
            batch_no=batch_no,
            aggregator_id=aggregator_id,
            branch_id=branch_id,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            import_batch_id=import_batch_id
        )
        db.add(batch)

    batch.settlement_date = settlement_date or period_end_date
    batch.gross_sales = gross_sales
    batch.payout = payout

    # If deductions data provided, replace deductions
    if deductions_data is not None:
        db.query(AggregatorDeduction).filter(AggregatorDeduction.settlement_batch_id == batch.id).delete()
        
        # Default head map
        heads = db.query(AccountingHead).all()
        head_code_map = {h.code.upper(): h.id for h in heads}

        for ded_item in deductions_data:
            ded_type = ded_item.get("deduction_type", "MISC").upper()
            head_id = ded_item.get("accounting_head_id")
            
            if not head_id:
                # Match default head codes
                if "COMMISSION" in ded_type:
                    head_id = head_code_map.get("COMMISSION_EXP")
                elif "PROMOTION" in ded_type:
                    head_id = head_code_map.get("PROMO_EXP")
                elif "TCS" in ded_type:
                    head_id = head_code_map.get("TCS_REC")
                elif "TDS" in ded_type:
                    head_id = head_code_map.get("TDS_REC")
                elif "GST" in ded_type:
                    head_id = head_code_map.get("GST_SEC_9_5")
                elif "PACKING" in ded_type:
                    head_id = head_code_map.get("PACKING_CHARGES")
                else:
                    head_id = head_code_map.get("MISC_EXP")

            ded = AggregatorDeduction(
                settlement_batch=batch,
                deduction_type=ded_type,
                description=ded_item.get("description", ded_type),
                amount=float(ded_item.get("amount", 0.0)),
                accounting_head_id=head_id
            )
            db.add(ded)

    db.flush()

    # Calculate formulas
    totals = calculate_settlement_batch_totals(batch)
    batch.total_deductions = totals["total_deductions"]
    batch.actual_difference = totals["actual_difference"]
    batch.difference_adjustment = totals["difference_adjustment"]

    if abs(batch.difference_adjustment) < 1.0:
        batch.status = "RECONCILED"
    else:
        batch.status = "DIFFERENCE"

    db.commit()
    db.refresh(batch)

    log_action(db, "SAVE_SETTLEMENT_BATCH", "SettlementBatch", batch.id, None, {
        "gross_sales": batch.gross_sales,
        "payout": batch.payout,
        "actual_diff": batch.actual_difference,
        "diff_adj": batch.difference_adjustment,
        "status": batch.status
    }, user=user)

    return batch

def _payout_row_templates() -> List[Dict[str, Any]]:
    return [
        {"s_no": 1, "code": "TOTAL_SALE", "particular": "Total Sale / Commissionable Value"},
        {"s_no": 2, "code": "PAYOUT", "particular": "Payout (Net Amount Received)"},
        {"s_no": 3, "code": "DIFFERENCE", "particular": "Difference (Total Sale − Payout)", "theme_row": True},
        {"s_no": 4, "code": "COMMISSION", "particular": "Online Platform Charges", "is_deduction": True},
        {"s_no": 5, "code": "PROMOTION", "particular": "Business Promotion", "is_deduction": True},
        {"s_no": 6, "code": "TCS", "particular": "TCS", "is_deduction": True},
        {"s_no": 7, "code": "TDS", "particular": "TDS Receivable", "is_deduction": True},
        {"s_no": 8, "code": "MISC", "particular": "Miscellaneous", "is_deduction": True},
        {"s_no": 9, "code": "TOTAL_DEDUCTIONS", "particular": "Total Deductions", "theme_row": True},
        {"s_no": 10, "code": "DIFFERENCE_ADJUSTMENT", "particular": "Unresolved Difference", "theme_row": True, "highlight": True},
        {"s_no": 11, "code": "GST_9_5", "particular": "GST Paid by Zomato / Swiggy under Section 9(5)", "is_info": True},
        {"s_no": 12, "code": "PACKING_CHARGES", "particular": "Packing Charges", "is_info": True},
    ]


def _cycle_meta(start: date, end: date) -> Dict[str, str]:
    return {
        "key": f"cycle_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}",
        "label": f"{start.strftime('%d/%m')} - {end.strftime('%d/%m')}",
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
    }


def _batch_row_value(batch: SettlementBatch, code: str) -> float:
    ded_map = {d.deduction_type: d.amount for d in batch.deductions}
    if code == "TOTAL_SALE":
        val = batch.gross_sales
    elif code == "PAYOUT":
        val = batch.payout
    elif code == "DIFFERENCE":
        val = batch.actual_difference
    elif code == "TOTAL_DEDUCTIONS":
        val = batch.total_deductions
    elif code == "DIFFERENCE_ADJUSTMENT":
        val = batch.difference_adjustment
    else:
        val = ded_map.get(code, 0.0)
    return round(val or 0.0, 2)


def get_aggregator_payout_matrix(
    db: Session,
    aggregator_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    query = db.query(SettlementBatch).join(Branch, SettlementBatch.branch_id == Branch.id)
    if aggregator_id:
        query = query.filter(SettlementBatch.aggregator_id == aggregator_id)
    if branch_id:
        query = query.filter(SettlementBatch.branch_id == branch_id)
    if start_date:
        query = query.filter(SettlementBatch.period_start_date >= start_date)
    if end_date:
        query = query.filter(SettlementBatch.period_end_date <= end_date)

    batches = query.order_by(Branch.name.asc(), SettlementBatch.period_start_date.asc()).all()

    matrix_rows = _payout_row_templates()
    cycle_map: Dict[str, Dict[str, Any]] = {}
    for b in batches:
        meta = _cycle_meta(b.period_start_date, b.period_end_date)
        cycle_map.setdefault(meta["key"], meta)

    for row in matrix_rows:
        for c_key in cycle_map:
            row[c_key] = 0.0
        row["total"] = 0.0

    columns = []
    groups: Dict[int, Dict[str, Any]] = {}

    for idx, b in enumerate(batches, start=1):
        col_key = f"batch_{b.id}"
        col_label = f"Batch {idx}: {b.branch.name} ({b.period_start_date.strftime('%d/%m')} - {b.period_end_date.strftime('%d/%m')})"
        columns.append({
            "key": col_key,
            "label": col_label,
            "batch_id": b.id,
            "status": b.status,
            "aggregator": b.aggregator.name,
            "branch_id": b.branch_id,
            "branch_name": b.branch.name,
        })

        if b.branch_id not in groups:
            groups[b.branch_id] = {
                "branch_id": b.branch_id,
                "branch_name": b.branch.name,
                "branch_code": b.branch.code,
                "cycle_map": {},
                "rows": _payout_row_templates(),
                "columns": [],
            }
            for row in groups[b.branch_id]["rows"]:
                row["total"] = 0.0

        group = groups[b.branch_id]
        meta = _cycle_meta(b.period_start_date, b.period_end_date)
        group["cycle_map"].setdefault(meta["key"], meta)
        for row in group["rows"]:
            row.setdefault(meta["key"], 0.0)

        group["columns"].append({
            "key": col_key,
            "label": f"{b.period_start_date.strftime('%d/%m')} - {b.period_end_date.strftime('%d/%m')}",
            "batch_id": b.id,
            "status": b.status,
            "aggregator": b.aggregator.name,
            "branch_id": b.branch_id,
            "branch_name": b.branch.name,
        })

        c_bucket = meta["key"]
        for row in matrix_rows:
            val = _batch_row_value(b, row["code"])
            row[col_key] = val
            row[c_bucket] = round(row.get(c_bucket, 0.0) + val, 2)
            row["total"] = round(row["total"] + val, 2)

        for row in group["rows"]:
            val = _batch_row_value(b, row["code"])
            row[col_key] = val
            row[c_bucket] = round(row.get(c_bucket, 0.0) + val, 2)
            row["total"] = round(row["total"] + val, 2)

    cycle_columns = list(cycle_map.values())
    if not cycle_columns:
        cycle_columns = [
            {"key": "c_1_5", "label": "1-5"},
            {"key": "c_6_12", "label": "6-12"},
            {"key": "c_13_19", "label": "13-19"},
            {"key": "c_20_26", "label": "20-26"},
            {"key": "c_27_31", "label": "27-31"},
        ]
        for row in matrix_rows:
            for ck in [c["key"] for c in cycle_columns]:
                row[ck] = 0.0

    cycle_columns.append({"key": "total", "label": "Total"})

    branch_groups = []
    for group in groups.values():
        g_cycles = list(group["cycle_map"].values())
        if not g_cycles:
            g_cycles = list(cycle_columns)
        else:
            g_cycles.append({"key": "total", "label": "Total"})
        branch_groups.append({
            "branch_id": group["branch_id"],
            "branch_name": group["branch_name"],
            "branch_code": group["branch_code"],
            "cycle_columns": g_cycles,
            "rows": group["rows"],
            "columns": group["columns"],
        })

    month_q = db.query(SettlementBatch)
    if aggregator_id:
        month_q = month_q.filter(SettlementBatch.aggregator_id == aggregator_id)
    if branch_id:
        month_q = month_q.filter(SettlementBatch.branch_id == branch_id)
    available_months = sorted({
        b.period_start_date.strftime("%Y-%m")
        for b in month_q.all()
        if b.period_start_date
    })

    return {
        "columns": columns,
        "cycle_columns": cycle_columns,
        "rows": matrix_rows,
        "branch_groups": branch_groups,
        "available_months": available_months,
    }

def delete_settlement_batch(db: Session, batch_id: int, user=None) -> bool:
    from app.models.import_batch import ImportBatch
    batch = db.query(SettlementBatch).filter(SettlementBatch.id == batch_id).first()
    if not batch:
        return False

    db.query(AggregatorDeduction).filter(AggregatorDeduction.settlement_batch_id == batch.id).delete()
    
    if batch.import_batch_id:
        db.query(ImportBatch).filter(ImportBatch.id == batch.import_batch_id).delete()

    batch_no = batch.batch_no
    db.delete(batch)
    db.commit()

    log_action(db, "DELETE_SETTLEMENT_BATCH", "SettlementBatch", batch_id, None, {"batch_no": batch_no}, user=user)
    return True
