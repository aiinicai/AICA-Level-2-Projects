"""Fundamental analysis engine — Module 2 (Growth, Profitability, Balance Sheet).

Every public function here is pure and deterministic: given the same
FinancialStatement inputs it always returns the same MetricResult. No
LLM calls, no network access, no hidden state. This is the layer the
spec's Principle 13 ("prefer deterministic Python calculations") and
Principle 6 ("separate calculations from AI interpretation") describe.

A note on EBITDA/EBIT: the source data (a Screener.in export) does not
provide a direct "Operating Profit" figure for the annual P&L that
reconciles cleanly against the individual expense lines available in
our canonical schema (some expense sub-lines, e.g. Power & Fuel,
Selling & Admin, are not yet mapped into FinancialStatement - see
financial_data.py's _FIELD_MAP). Rather than approximate EBITDA from an
incomplete expense breakdown, this module BACK-SOLVES it from the
figure Screener's own P&L already computed with full information:

    EBITDA = Profit Before Tax - Other Income + Depreciation + Interest
    EBIT   = EBITDA - Depreciation  (equivalently: PBT - Other Income + Interest)

This is an exact identity given how the source P&L is structured (PBT
already nets every expense line, Other Income is added back above PBT,
Depreciation and Interest are subtracted below the operating-profit
line) - not an approximation, and every MetricResult below shows the
formula and inputs used so it is independently checkable.
"""

from __future__ import annotations

import logging

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, MetricResult

logger = logging.getLogger(__name__)


def _missing(metric_name: str, formula: str, period: str, unit: UnitOfMeasure, inputs: dict) -> MetricResult:
    """Standard MISSING_INPUT result — never fabricates a value."""
    return MetricResult(
        metric_name=metric_name, formula=formula, inputs=inputs, value=None,
        unit=unit, period=period, status=DataStatus.MISSING_INPUT,
        data_quality_notes=[
            f"One or more required inputs was None: {', '.join(k for k, v in inputs.items() if v is None)}"
        ],
    )


# --------------------------------------------------------------------------
# EBITDA / EBIT back-solve (foundational — reused across this module and
# cashflow.py)
# --------------------------------------------------------------------------


def compute_ebitda(stmt: FinancialStatement) -> MetricResult:
    """Back-solved EBITDA. See module docstring for the identity used."""
    inputs = {
        "profit_before_tax": stmt.profit_before_tax,
        "other_income": stmt.other_income,
        "depreciation": stmt.depreciation,
        "interest": stmt.interest,
    }
    if stmt.profit_before_tax is None or stmt.depreciation is None or stmt.interest is None:
        return _missing(
            "EBITDA", "PBT - Other Income + Depreciation + Interest", stmt.period,
            UnitOfMeasure.INR_CRORE, inputs,
        )
    other_income = stmt.other_income or 0.0
    value = stmt.profit_before_tax - other_income + stmt.depreciation + stmt.interest
    return MetricResult(
        metric_name="EBITDA", formula="PBT - Other Income + Depreciation + Interest",
        inputs=inputs, value=round(value, 2), unit=UnitOfMeasure.INR_CRORE, period=stmt.period,
        status=DataStatus.OK,
        interpretation="Back-solved from PBT; see fundamentals.py module docstring for the identity.",
    )


def compute_ebit(stmt: FinancialStatement) -> MetricResult:
    """Back-solved EBIT (EBITDA - Depreciation)."""
    ebitda_result = compute_ebitda(stmt)
    inputs = {**ebitda_result.inputs}
    if ebitda_result.status != DataStatus.OK or stmt.depreciation is None:
        return _missing("EBIT", "EBITDA - Depreciation", stmt.period, UnitOfMeasure.INR_CRORE, inputs)
    value = ebitda_result.value - stmt.depreciation
    return MetricResult(
        metric_name="EBIT", formula="EBITDA - Depreciation", inputs=inputs,
        value=round(value, 2), unit=UnitOfMeasure.INR_CRORE, period=stmt.period, status=DataStatus.OK,
    )


# --------------------------------------------------------------------------
# Growth (CAGR)
# --------------------------------------------------------------------------


def _cagr(start_value: float | None, end_value: float | None, years: float) -> float | None:
    if start_value is None or end_value is None or years <= 0:
        return None
    if start_value <= 0 or end_value <= 0:
        # CAGR is undefined/misleading across a sign change (e.g. a loss-
        # making base year) — better to report unavailable than a
        # nonsensical or complex-valued result.
        return None
    return (end_value / start_value) ** (1.0 / years) - 1.0


def compute_revenue_cagr(
    statements: list[FinancialStatement], years: int = 3
) -> MetricResult:
    """CAGR of Sales over the trailing `years`-year window in the series."""
    return _cagr_metric(statements, years, field="sales", metric_name=f"Revenue CAGR ({years}yr)")


def compute_pat_cagr(statements: list[FinancialStatement], years: int = 3) -> MetricResult:
    return _cagr_metric(statements, years, field="net_profit", metric_name=f"PAT CAGR ({years}yr)")


def compute_ebitda_cagr(statements: list[FinancialStatement], years: int = 3) -> MetricResult:
    ordered = sorted(statements, key=lambda s: s.period_end_date or s.period)
    if len(ordered) <= years:
        return _missing(
            f"EBITDA CAGR ({years}yr)", "(EBITDA_end / EBITDA_start)^(1/years) - 1",
            ordered[-1].period if ordered else "unknown", UnitOfMeasure.PERCENT, {},
        )
    start_stmt, end_stmt = ordered[-years - 1], ordered[-1]
    start_ebitda = compute_ebitda(start_stmt)
    end_ebitda = compute_ebitda(end_stmt)
    inputs = {"ebitda_start": start_ebitda.value, "ebitda_end": end_ebitda.value, "years": float(years)}
    value = _cagr(start_ebitda.value, end_ebitda.value, years)
    if value is None:
        return _missing(
            f"EBITDA CAGR ({years}yr)", "(EBITDA_end / EBITDA_start)^(1/years) - 1",
            end_stmt.period, UnitOfMeasure.PERCENT, inputs,
        )
    return MetricResult(
        metric_name=f"EBITDA CAGR ({years}yr)", formula="(EBITDA_end / EBITDA_start)^(1/years) - 1",
        inputs=inputs, value=round(value, 4), unit=UnitOfMeasure.PERCENT,
        period=f"{start_stmt.period}-{end_stmt.period}", status=DataStatus.OK,
    )


def compute_ebit_cagr(statements: list[FinancialStatement], years: int = 3) -> MetricResult:
    ordered = sorted(statements, key=lambda s: s.period_end_date or s.period)
    if len(ordered) <= years:
        return _missing(
            f"EBIT CAGR ({years}yr)", "(EBIT_end / EBIT_start)^(1/years) - 1",
            ordered[-1].period if ordered else "unknown", UnitOfMeasure.PERCENT, {},
        )
    start_stmt, end_stmt = ordered[-years - 1], ordered[-1]
    start_ebit = compute_ebit(start_stmt)
    end_ebit = compute_ebit(end_stmt)
    inputs = {"ebit_start": start_ebit.value, "ebit_end": end_ebit.value, "years": float(years)}
    value = _cagr(start_ebit.value, end_ebit.value, years)
    if value is None:
        return _missing(
            f"EBIT CAGR ({years}yr)", "(EBIT_end / EBIT_start)^(1/years) - 1",
            end_stmt.period, UnitOfMeasure.PERCENT, inputs,
        )
    return MetricResult(
        metric_name=f"EBIT CAGR ({years}yr)", formula="(EBIT_end / EBIT_start)^(1/years) - 1",
        inputs=inputs, value=round(value, 4), unit=UnitOfMeasure.PERCENT,
        period=f"{start_stmt.period}-{end_stmt.period}", status=DataStatus.OK,
    )


def compute_eps_cagr(statements: list[FinancialStatement], years: int = 3) -> MetricResult:
    """EPS CAGR. Note: across a share-count discontinuity (e.g. an IPO,
    as flagged by validators.check_share_count_discontinuity), EPS CAGR
    can be materially distorted even though the calculation itself is
    correct — this is a data-quality caveat, not a bug, and is exactly
    why that validator exists."""
    from app.analysis.shareholder import compute_eps

    ordered = sorted(statements, key=lambda s: s.period_end_date or s.period)
    if len(ordered) <= years:
        return _missing(
            f"EPS CAGR ({years}yr)", "(EPS_end / EPS_start)^(1/years) - 1",
            ordered[-1].period if ordered else "unknown", UnitOfMeasure.PERCENT, {},
        )
    start_stmt, end_stmt = ordered[-years - 1], ordered[-1]
    start_eps = compute_eps(start_stmt)
    end_eps = compute_eps(end_stmt)
    inputs = {"eps_start": start_eps.value, "eps_end": end_eps.value, "years": float(years)}
    value = _cagr(start_eps.value, end_eps.value, years)
    notes = []
    if value is None:
        return _missing(
            f"EPS CAGR ({years}yr)", "(EPS_end / EPS_start)^(1/years) - 1",
            end_stmt.period, UnitOfMeasure.PERCENT, inputs,
        )
    return MetricResult(
        metric_name=f"EPS CAGR ({years}yr)", formula="(EPS_end / EPS_start)^(1/years) - 1",
        inputs=inputs, value=round(value, 4), unit=UnitOfMeasure.PERCENT,
        period=f"{start_stmt.period}-{end_stmt.period}", status=DataStatus.OK,
        data_quality_notes=notes,
    )


def _cagr_metric(
    statements: list[FinancialStatement], years: int, *, field: str, metric_name: str
) -> MetricResult:
    ordered = sorted(statements, key=lambda s: s.period_end_date or s.period)
    formula = f"({field}_end / {field}_start)^(1/years) - 1"
    if len(ordered) <= years:
        return _missing(
            metric_name, formula, ordered[-1].period if ordered else "unknown",
            UnitOfMeasure.PERCENT, {},
        )
    start_stmt, end_stmt = ordered[-years - 1], ordered[-1]
    start_val, end_val = getattr(start_stmt, field), getattr(end_stmt, field)
    inputs = {f"{field}_start": start_val, f"{field}_end": end_val, "years": float(years)}
    value = _cagr(start_val, end_val, years)
    if value is None:
        return _missing(metric_name, formula, end_stmt.period, UnitOfMeasure.PERCENT, inputs)
    return MetricResult(
        metric_name=metric_name, formula=formula, inputs=inputs, value=round(value, 4),
        unit=UnitOfMeasure.PERCENT, period=f"{start_stmt.period}-{end_stmt.period}", status=DataStatus.OK,
    )


# --------------------------------------------------------------------------
# Profitability
# --------------------------------------------------------------------------


def compute_ebitda_margin(stmt: FinancialStatement) -> MetricResult:
    ebitda = compute_ebitda(stmt)
    inputs = {"ebitda": ebitda.value, "sales": stmt.sales}
    if ebitda.status != DataStatus.OK or not stmt.sales:
        return _missing("EBITDA Margin", "EBITDA / Sales", stmt.period, UnitOfMeasure.PERCENT, inputs)
    return MetricResult(
        metric_name="EBITDA Margin", formula="EBITDA / Sales", inputs=inputs,
        value=round(ebitda.value / stmt.sales, 4), unit=UnitOfMeasure.PERCENT,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_ebit_margin(stmt: FinancialStatement) -> MetricResult:
    ebit = compute_ebit(stmt)
    inputs = {"ebit": ebit.value, "sales": stmt.sales}
    if ebit.status != DataStatus.OK or not stmt.sales:
        return _missing("EBIT Margin", "EBIT / Sales", stmt.period, UnitOfMeasure.PERCENT, inputs)
    return MetricResult(
        metric_name="EBIT Margin", formula="EBIT / Sales", inputs=inputs,
        value=round(ebit.value / stmt.sales, 4), unit=UnitOfMeasure.PERCENT,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_pat_margin(stmt: FinancialStatement) -> MetricResult:
    inputs = {"net_profit": stmt.net_profit, "sales": stmt.sales}
    if stmt.net_profit is None or not stmt.sales:
        return _missing("PAT Margin", "Net Profit / Sales", stmt.period, UnitOfMeasure.PERCENT, inputs)
    return MetricResult(
        metric_name="PAT Margin", formula="Net Profit / Sales", inputs=inputs,
        value=round(stmt.net_profit / stmt.sales, 4), unit=UnitOfMeasure.PERCENT,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_gross_margin(stmt: FinancialStatement) -> MetricResult:
    """Gross Margin = (Sales - Raw Material Cost) / Sales.

    Note: this treats Raw Material Cost as the full COGS proxy, since
    the canonical schema does not separately break out other
    directly-attributable production costs (power & fuel, other mfr.
    exp are in the source but not yet mapped — see financial_data.py).
    This is therefore a labeled approximation, not full COGS-based gross
    margin — flagged in data_quality_notes rather than silently treated
    as exact.
    """
    inputs = {"sales": stmt.sales, "raw_material_cost": stmt.raw_material_cost}
    if stmt.sales is None or stmt.raw_material_cost is None:
        return _missing(
            "Gross Margin (RM-cost basis)", "(Sales - Raw Material Cost) / Sales",
            stmt.period, UnitOfMeasure.PERCENT, inputs,
        )
    value = (stmt.sales - stmt.raw_material_cost) / stmt.sales
    return MetricResult(
        metric_name="Gross Margin (RM-cost basis)", formula="(Sales - Raw Material Cost) / Sales",
        inputs=inputs, value=round(value, 4), unit=UnitOfMeasure.PERCENT, period=stmt.period,
        status=DataStatus.OK,
        data_quality_notes=[
            "Approximation: uses Raw Material Cost only as the COGS proxy; other "
            "direct production costs (power & fuel, other mfr. expenses) are not "
            "included because they are not yet mapped into the canonical schema."
        ],
    )


def compute_roe(stmt: FinancialStatement) -> MetricResult:
    """Return on Equity = Net Profit / (Equity Share Capital + Reserves).

    Uses period-end equity, not average equity — a simplification flagged
    here rather than silently treated as the more standard average-equity
    convention. Switch to average-equity if two consecutive statements
    are available and greater precision is wanted.
    """
    equity = None
    if stmt.equity_share_capital is not None and stmt.reserves is not None:
        equity = stmt.equity_share_capital + stmt.reserves
    inputs = {"net_profit": stmt.net_profit, "equity_period_end": equity}
    if stmt.net_profit is None or not equity:
        return _missing("ROE", "Net Profit / (Equity Share Capital + Reserves)", stmt.period, UnitOfMeasure.PERCENT, inputs)
    return MetricResult(
        metric_name="ROE", formula="Net Profit / (Equity Share Capital + Reserves)",
        inputs=inputs, value=round(stmt.net_profit / equity, 4), unit=UnitOfMeasure.PERCENT,
        period=stmt.period, status=DataStatus.OK,
        data_quality_notes=["Uses period-end equity, not average equity."],
    )


def compute_roce(stmt: FinancialStatement) -> MetricResult:
    """Return on Capital Employed = EBIT / (Equity + Borrowings).

    Capital Employed is approximated as Equity + Borrowings (a common
    practical proxy for Total Assets - Current Liabilities) because the
    canonical schema does not separate current from non-current
    liabilities within "Other Liabilities" — flagged explicitly rather
    than silently assumed precise.
    """
    ebit = compute_ebit(stmt)
    capital_employed = None
    if stmt.equity_share_capital is not None and stmt.reserves is not None and stmt.borrowings is not None:
        capital_employed = stmt.equity_share_capital + stmt.reserves + stmt.borrowings
    inputs = {"ebit": ebit.value, "capital_employed_approx": capital_employed}
    if ebit.status != DataStatus.OK or not capital_employed:
        return _missing("ROCE", "EBIT / (Equity + Borrowings)", stmt.period, UnitOfMeasure.PERCENT, inputs)
    return MetricResult(
        metric_name="ROCE", formula="EBIT / (Equity + Borrowings)", inputs=inputs,
        value=round(ebit.value / capital_employed, 4), unit=UnitOfMeasure.PERCENT,
        period=stmt.period, status=DataStatus.OK,
        data_quality_notes=[
            "Capital Employed approximated as Equity + Borrowings (Total Assets minus "
            "Current Liabilities is not directly available in the canonical schema)."
        ],
    )


# --------------------------------------------------------------------------
# Balance Sheet
# --------------------------------------------------------------------------


def compute_debt_to_equity(stmt: FinancialStatement) -> MetricResult:
    equity = None
    if stmt.equity_share_capital is not None and stmt.reserves is not None:
        equity = stmt.equity_share_capital + stmt.reserves
    inputs = {"borrowings": stmt.borrowings, "equity": equity}
    if stmt.borrowings is None or not equity:
        return _missing("Debt/Equity", "Borrowings / (Equity Share Capital + Reserves)", stmt.period, UnitOfMeasure.RATIO, inputs)
    return MetricResult(
        metric_name="Debt/Equity", formula="Borrowings / (Equity Share Capital + Reserves)",
        inputs=inputs, value=round(stmt.borrowings / equity, 4), unit=UnitOfMeasure.RATIO,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_net_debt_to_ebitda(stmt: FinancialStatement) -> MetricResult:
    ebitda = compute_ebitda(stmt)
    net_debt = None
    if stmt.borrowings is not None and stmt.cash_and_bank is not None:
        net_debt = stmt.borrowings - stmt.cash_and_bank
    inputs = {"net_debt": net_debt, "ebitda": ebitda.value}
    if net_debt is None or ebitda.status != DataStatus.OK or ebitda.value == 0:
        return _missing("Net Debt/EBITDA", "(Borrowings - Cash & Bank) / EBITDA", stmt.period, UnitOfMeasure.RATIO, inputs)
    return MetricResult(
        metric_name="Net Debt/EBITDA", formula="(Borrowings - Cash & Bank) / EBITDA",
        inputs=inputs, value=round(net_debt / ebitda.value, 4), unit=UnitOfMeasure.RATIO,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_current_ratio(stmt: FinancialStatement) -> MetricResult:
    """Not computable from the canonical schema: current assets and
    current liabilities are not broken out separately (Screener's export
    provides asset/liability totals, not a current/non-current split).
    Returns NOT_APPLICABLE explicitly rather than approximating with a
    misleading substitute — per Principle 9, handle missing data
    explicitly rather than silently guess.
    """
    return MetricResult(
        metric_name="Current Ratio", formula="Current Assets / Current Liabilities",
        inputs={}, value=None, unit=UnitOfMeasure.RATIO, period=stmt.period,
        status=DataStatus.NOT_APPLICABLE,
        data_quality_notes=[
            "Current assets/current liabilities are not separated in the canonical "
            "schema (source data provides only asset/liability totals). Would "
            "require a balance sheet with a current/non-current split, e.g. from "
            "the annual report PDF rather than the Screener export."
        ],
    )


def compute_asset_turnover(stmt: FinancialStatement) -> MetricResult:
    inputs = {"sales": stmt.sales, "total_assets": stmt.total_assets}
    if not stmt.sales or not stmt.total_assets:
        return _missing("Asset Turnover", "Sales / Total Assets", stmt.period, UnitOfMeasure.RATIO, inputs)
    return MetricResult(
        metric_name="Asset Turnover", formula="Sales / Total Assets", inputs=inputs,
        value=round(stmt.sales / stmt.total_assets, 4), unit=UnitOfMeasure.RATIO,
        period=stmt.period, status=DataStatus.OK,
        data_quality_notes=["Uses period-end Total Assets, not average Total Assets."],
    )


# --------------------------------------------------------------------------
# Batch helper
# --------------------------------------------------------------------------


def compute_all_fundamentals(
    statements: list[FinancialStatement], *, cagr_years: int = 3
) -> list[MetricResult]:
    """Convenience: run every per-period metric across all statements, plus
    the trailing CAGR metrics against the full series."""
    results: list[MetricResult] = []
    for stmt in statements:
        results.extend(
            [
                compute_ebitda(stmt), compute_ebit(stmt),
                compute_ebitda_margin(stmt), compute_ebit_margin(stmt), compute_pat_margin(stmt),
                compute_gross_margin(stmt), compute_roe(stmt), compute_roce(stmt),
                compute_debt_to_equity(stmt), compute_net_debt_to_ebitda(stmt),
                compute_current_ratio(stmt), compute_asset_turnover(stmt),
            ]
        )
    results.extend(
        [
            compute_revenue_cagr(statements, cagr_years),
            compute_ebitda_cagr(statements, cagr_years),
            compute_ebit_cagr(statements, cagr_years),
            compute_pat_cagr(statements, cagr_years),
            compute_eps_cagr(statements, cagr_years),
        ]
    )
    return results
