"""Cash flow analysis — Module 2.

Capex is not a direct line item in the canonical schema (the Screener
export's Cash Flow section gives CFO/CFI/CFF/Net totals, not a capex
sub-line). This module estimates it via the standard indirect method:

    Capex (estimated) = (Net Block_end - Net Block_start)
                       + (CWIP_end - CWIP_start)
                       + Depreciation_end

This requires two CONSECUTIVE statements, which is why FCF/Capex here
take a `prior_stmt` argument rather than a single statement — and why,
for the earliest period in a series (no prior year available), these
return status=INSUFFICIENT_HISTORY rather than a fabricated figure.
"""

from __future__ import annotations

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, MetricResult


def compute_cfo(stmt: FinancialStatement) -> MetricResult:
    inputs = {"cash_from_operations": stmt.cash_from_operations}
    if stmt.cash_from_operations is None:
        return MetricResult(
            metric_name="CFO", formula="Cash from Operating Activity (as reported)",
            inputs=inputs, value=None, unit=UnitOfMeasure.INR_CRORE, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    return MetricResult(
        metric_name="CFO", formula="Cash from Operating Activity (as reported)",
        inputs=inputs, value=stmt.cash_from_operations, unit=UnitOfMeasure.INR_CRORE,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_cfo_to_pat(stmt: FinancialStatement) -> MetricResult:
    inputs = {"cash_from_operations": stmt.cash_from_operations, "net_profit": stmt.net_profit}
    if stmt.cash_from_operations is None or not stmt.net_profit:
        return MetricResult(
            metric_name="CFO/PAT", formula="Cash from Operations / Net Profit",
            inputs=inputs, value=None, unit=UnitOfMeasure.RATIO, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    return MetricResult(
        metric_name="CFO/PAT", formula="Cash from Operations / Net Profit",
        inputs=inputs, value=round(stmt.cash_from_operations / stmt.net_profit, 4),
        unit=UnitOfMeasure.RATIO, period=stmt.period, status=DataStatus.OK,
        interpretation=(
            "A ratio well below 1.0 across multiple periods may indicate "
            "earnings quality concerns (profit not converting to cash); "
            "this is a deterministic flag only, not an interpretive claim."
        ),
    )


def compute_capex_estimated(stmt: FinancialStatement, prior_stmt: FinancialStatement | None) -> MetricResult:
    formula = "(NetBlock_end - NetBlock_start) + (CWIP_end - CWIP_start) + Depreciation_end"
    if prior_stmt is None:
        return MetricResult(
            metric_name="Capex (estimated)", formula=formula, inputs={}, value=None,
            unit=UnitOfMeasure.INR_CRORE, period=stmt.period, status=DataStatus.INSUFFICIENT_HISTORY,
            data_quality_notes=["Requires a prior-period statement; none supplied (earliest period in series)."],
        )
    inputs = {
        "net_block_start": prior_stmt.net_block, "net_block_end": stmt.net_block,
        "cwip_start": prior_stmt.capital_work_in_progress, "cwip_end": stmt.capital_work_in_progress,
        "depreciation_end": stmt.depreciation,
    }
    if None in inputs.values():
        return MetricResult(
            metric_name="Capex (estimated)", formula=formula, inputs=inputs, value=None,
            unit=UnitOfMeasure.INR_CRORE, period=stmt.period, status=DataStatus.MISSING_INPUT,
        )
    value = (
        (stmt.net_block - prior_stmt.net_block)
        + (stmt.capital_work_in_progress - prior_stmt.capital_work_in_progress)
        + stmt.depreciation
    )
    return MetricResult(
        metric_name="Capex (estimated)", formula=formula, inputs=inputs, value=round(value, 2),
        unit=UnitOfMeasure.INR_CRORE, period=stmt.period, status=DataStatus.OK,
        data_quality_notes=[
            "Indirect estimate from balance sheet movement, not a directly reported "
            "capex figure (not broken out separately in the source Cash Flow statement)."
        ],
    )


def compute_fcf(stmt: FinancialStatement, prior_stmt: FinancialStatement | None) -> MetricResult:
    capex = compute_capex_estimated(stmt, prior_stmt)
    inputs = {"cfo": stmt.cash_from_operations, "capex_estimated": capex.value}
    if stmt.cash_from_operations is None or capex.status != DataStatus.OK:
        return MetricResult(
            metric_name="Free Cash Flow", formula="CFO - Capex (estimated)", inputs=inputs,
            value=None, unit=UnitOfMeasure.INR_CRORE, period=stmt.period,
            status=capex.status if capex.status != DataStatus.OK else DataStatus.MISSING_INPUT,
        )
    value = stmt.cash_from_operations - capex.value
    return MetricResult(
        metric_name="Free Cash Flow", formula="CFO - Capex (estimated)", inputs=inputs,
        value=round(value, 2), unit=UnitOfMeasure.INR_CRORE, period=stmt.period, status=DataStatus.OK,
    )


def compute_fcf_conversion(stmt: FinancialStatement, prior_stmt: FinancialStatement | None) -> MetricResult:
    """FCF Conversion = FCF / EBITDA."""
    from app.analysis.fundamentals import compute_ebitda

    fcf = compute_fcf(stmt, prior_stmt)
    ebitda = compute_ebitda(stmt)
    inputs = {"fcf": fcf.value, "ebitda": ebitda.value}
    if fcf.status != DataStatus.OK or ebitda.status != DataStatus.OK or not ebitda.value:
        return MetricResult(
            metric_name="FCF Conversion", formula="FCF / EBITDA", inputs=inputs, value=None,
            unit=UnitOfMeasure.PERCENT, period=stmt.period,
            status=fcf.status if fcf.status != DataStatus.OK else DataStatus.MISSING_INPUT,
        )
    return MetricResult(
        metric_name="FCF Conversion", formula="FCF / EBITDA", inputs=inputs,
        value=round(fcf.value / ebitda.value, 4), unit=UnitOfMeasure.PERCENT,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_all_cashflow_metrics(statements: list[FinancialStatement]) -> list[MetricResult]:
    """Convenience: run every cash-flow metric across a chronologically
    sorted statement series, correctly pairing each period with its
    immediate predecessor for the capex/FCF calculations."""
    ordered = sorted(statements, key=lambda s: s.period_end_date or s.period)
    results: list[MetricResult] = []
    for i, stmt in enumerate(ordered):
        prior = ordered[i - 1] if i > 0 else None
        results.extend(
            [
                compute_cfo(stmt),
                compute_cfo_to_pat(stmt),
                compute_capex_estimated(stmt, prior),
                compute_fcf(stmt, prior),
                compute_fcf_conversion(stmt, prior),
            ]
        )
    return results
