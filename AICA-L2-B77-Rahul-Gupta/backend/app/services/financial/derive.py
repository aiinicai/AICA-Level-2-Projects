"""Derive canonical metrics that a statement states only implicitly.

A Schedule III P&L never prints "EBITDA" or "EBIT", and Division I balance sheets
print shareholders' funds as a section rather than a "Net worth" line. Those
metrics were therefore unreachable from a real uploaded document — and because
the valuation falls back to hardcoded defaults for anything missing
(``ebitda_margin or 0.15`` in orchestrator.build_inputs), a DCF built from real
statements silently ran on an assumed 15% margin instead of the company's own.

Deriving them from components that *do* extract is more robust than trying to
regex every possible wording, and the arithmetic is standard:

    EBIT      = PBT + finance cost          (interest added back)
    EBITDA    = EBIT + depreciation         (and amortisation)
    net worth = share capital + reserves    (shareholders' funds)

Derived rows are marked in ``original_label`` so the review UI shows how the
number was arrived at, and never overwrite a value read off the statement.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import FinancialLineItem
from .canonical import STATEMENT_OF

# metric -> (component metrics, how to combine, human-readable formula)
DERIVATIONS: list[tuple[str, tuple[str, ...], str]] = [
    ("ebit", ("pbt", "finance_cost"), "PBT + Finance Costs"),
    ("ebitda", ("ebit", "depreciation"), "EBIT + Depreciation & Amortisation"),
    ("net_worth", ("share_capital", "reserves"), "Share Capital + Reserves & Surplus"),
    ("total_liabilities", ("total_assets", "-net_worth"), "Total Assets − Net Worth"),
]


def _value_of(row: FinancialLineItem | None) -> float | None:
    if row is None:
        return None
    return row.approved_value if row.approved_value is not None else row.python_value


def derive_missing_metrics(db: Session, case_id: str) -> int:
    """Fill derivable metrics for every period of a case. Returns rows created."""
    rows = db.execute(select(FinancialLineItem).where(
        FinancialLineItem.case_id == case_id)).scalars().all()

    by_period: dict[str, dict[str, FinancialLineItem]] = {}
    for r in rows:
        by_period.setdefault(r.period_label, {})[r.metric] = r

    created = 0
    for period, metrics in by_period.items():
        # ordered: ebit feeds ebitda, net_worth feeds total_liabilities
        for target, components, formula in DERIVATIONS:
            existing = metrics.get(target)
            if _value_of(existing) is not None:
                continue  # never override what the statement actually says

            total = 0.0
            complete = True
            for comp in components:
                negate = comp.startswith("-")
                value = _value_of(metrics.get(comp.lstrip("-")))
                if value is None:
                    complete = False
                    break
                total += -value if negate else value
            if not complete:
                continue

            if existing is not None:
                existing.python_value = total
                existing.original_label = f"Derived: {formula}"
            else:
                row = FinancialLineItem(
                    case_id=case_id, period_label=period,
                    statement=STATEMENT_OF.get(target, "pnl"), metric=target,
                    python_value=total, original_label=f"Derived: {formula}",
                    original_display="", unit="INR", source_page=0,
                    verification_status="unverified", confidence=0.0,
                )
                db.add(row)
                metrics[target] = row
                created += 1
            # make the new value visible to later derivations in this loop
            metrics[target].python_value = total

    if created:
        db.commit()
    return created
