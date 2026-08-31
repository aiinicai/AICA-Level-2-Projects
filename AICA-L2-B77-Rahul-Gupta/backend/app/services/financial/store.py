"""Load canonical financial data from DB into engine-friendly structures."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import FinancialLineItem, FinancialPeriod, NormalisationAdjustment, Ratio
from .analytics import compute_analytics


def get_periods(db: Session, case_id: str) -> list[str]:
    rows = db.execute(
        select(FinancialPeriod).where(FinancialPeriod.case_id == case_id)
        .order_by(FinancialPeriod.order_index)
    ).scalars().all()
    return [r.label for r in rows]


def load_financial_data(db: Session, case_id: str, use_approved: bool = True) -> tuple[dict, list[str]]:
    """Returns (data[period][metric] = value_inr, ordered periods)."""
    periods = get_periods(db, case_id)
    items = db.execute(
        select(FinancialLineItem).where(FinancialLineItem.case_id == case_id)
    ).scalars().all()
    data: dict[str, dict[str, float]] = {p: {} for p in periods}
    for it in items:
        val = it.approved_value if use_approved and it.approved_value is not None else it.python_value
        if val is None:
            continue
        data.setdefault(it.period_label, {})[it.metric] = float(val)
    return data, periods


def load_normalised_data(db: Session, case_id: str) -> tuple[dict, list[str]]:
    """Approved financials with approved normalisation adjustments applied."""
    data, periods = load_financial_data(db, case_id)
    adjustments = db.execute(
        select(NormalisationAdjustment).where(
            NormalisationAdjustment.case_id == case_id,
            NormalisationAdjustment.status == "approved",
        )
    ).scalars().all()
    for adj in adjustments:
        pd = data.get(adj.period_label)
        if pd is None or adj.metric not in pd:
            continue
        pd[adj.metric] = pd[adj.metric] + adj.adjustment
        # cascade simple derived metrics for P&L adjustments
        if adj.metric == "revenue" and "ebitda" in pd:
            # a revenue normalisation flows to EBITDA at the period margin unless
            # a matching EBITDA adjustment exists
            has_ebitda_adj = any(a.metric == "ebitda" and a.period_label == adj.period_label
                                 for a in adjustments)
            if not has_ebitda_adj:
                margin = pd["ebitda"] / (pd["revenue"] - adj.adjustment) if (pd["revenue"] - adj.adjustment) else 0
                pd["ebitda"] += adj.adjustment * margin
    return data, periods


def compute_case_analytics(db: Session, case_id: str, normalised: bool = True) -> dict:
    data, periods = (load_normalised_data(db, case_id) if normalised
                     else load_financial_data(db, case_id))
    if not periods:
        return {"per_period": {}, "summary": {}, "periods": []}
    return compute_analytics(data, periods)


def persist_ratios(db: Session, case_id: str, analytics: dict) -> None:
    """Cache computed ratios in the ratios table (idempotent upsert)."""
    from sqlalchemy import delete
    db.execute(delete(Ratio).where(Ratio.case_id == case_id))
    for period, ratios in analytics.get("per_period", {}).items():
        for name, value in ratios.items():
            if value is None:
                continue
            db.add(Ratio(case_id=case_id, period_label=period, name=name, value=float(value)))
    db.commit()
