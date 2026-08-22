"""Working capital metrics — Module 2.

Payable Days cannot be computed: the canonical schema has no "Trade
Payables" line (the Screener export's Balance Sheet only breaks out
Receivables, Inventory, and Cash & Bank on the asset side, plus an
undifferentiated "Other Liabilities" on the liability side that is not
exclusively payables). Consequently Cash Conversion Cycle is also
reported unavailable rather than a two-thirds-correct number computed
by silently dropping the payables term — a CCC missing its payables
component is not "CCC minus a piece," it is a different, misleading
metric.
"""

from __future__ import annotations

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, MetricResult

_DAYS_IN_YEAR = 365.0


def compute_receivable_days(stmt: FinancialStatement) -> MetricResult:
    inputs = {"receivables": stmt.receivables, "sales": stmt.sales}
    if stmt.receivables is None or not stmt.sales:
        return MetricResult(
            metric_name="Receivable Days", formula="(Receivables / Sales) * 365",
            inputs=inputs, value=None, unit=UnitOfMeasure.DAYS, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    value = (stmt.receivables / stmt.sales) * _DAYS_IN_YEAR
    return MetricResult(
        metric_name="Receivable Days", formula="(Receivables / Sales) * 365",
        inputs=inputs, value=round(value, 1), unit=UnitOfMeasure.DAYS,
        period=stmt.period, status=DataStatus.OK,
        data_quality_notes=["Uses period-end Receivables, not average Receivables."],
    )


def compute_inventory_days(stmt: FinancialStatement) -> MetricResult:
    """Inventory Days = (Inventory / Raw Material Cost) * 365.

    Uses Raw Material Cost as the COGS proxy (same limitation noted in
    fundamentals.compute_gross_margin — full COGS is not available in
    the canonical schema).
    """
    inputs = {"inventory": stmt.inventory, "raw_material_cost": stmt.raw_material_cost}
    if stmt.inventory is None or not stmt.raw_material_cost:
        return MetricResult(
            metric_name="Inventory Days", formula="(Inventory / Raw Material Cost) * 365",
            inputs=inputs, value=None, unit=UnitOfMeasure.DAYS, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    value = (stmt.inventory / stmt.raw_material_cost) * _DAYS_IN_YEAR
    return MetricResult(
        metric_name="Inventory Days", formula="(Inventory / Raw Material Cost) * 365",
        inputs=inputs, value=round(value, 1), unit=UnitOfMeasure.DAYS,
        period=stmt.period, status=DataStatus.OK,
        data_quality_notes=[
            "Uses Raw Material Cost as a COGS proxy (full COGS is not separately "
            "available); uses period-end Inventory, not average Inventory."
        ],
    )


def compute_payable_days(stmt: FinancialStatement) -> MetricResult:
    return MetricResult(
        metric_name="Payable Days", formula="(Trade Payables / Purchases) * 365",
        inputs={}, value=None, unit=UnitOfMeasure.DAYS, period=stmt.period,
        status=DataStatus.NOT_APPLICABLE,
        data_quality_notes=[
            "Trade Payables is not a separate line item in the canonical schema "
            "(only an undifferentiated 'Other Liabilities' total is available). "
            "Would require a balance sheet with payables broken out, e.g. from "
            "the annual report PDF rather than the Screener export."
        ],
    )


def compute_cash_conversion_cycle(stmt: FinancialStatement) -> MetricResult:
    receivable_days = compute_receivable_days(stmt)
    inventory_days = compute_inventory_days(stmt)
    payable_days = compute_payable_days(stmt)  # always NOT_APPLICABLE currently
    return MetricResult(
        metric_name="Cash Conversion Cycle",
        formula="Receivable Days + Inventory Days - Payable Days",
        inputs={
            "receivable_days": receivable_days.value,
            "inventory_days": inventory_days.value,
            "payable_days": payable_days.value,
        },
        value=None, unit=UnitOfMeasure.DAYS, period=stmt.period,
        status=DataStatus.NOT_APPLICABLE,
        data_quality_notes=[
            "Cannot compute: Payable Days is unavailable (see compute_payable_days). "
            "A CCC omitting the payables term would be a different, misleading "
            "metric, not a valid partial result."
        ],
    )


def compute_all_working_capital_metrics(statements: list[FinancialStatement]) -> list[MetricResult]:
    results: list[MetricResult] = []
    for stmt in statements:
        results.extend(
            [
                compute_receivable_days(stmt),
                compute_inventory_days(stmt),
                compute_payable_days(stmt),
                compute_cash_conversion_cycle(stmt),
            ]
        )
    return results
