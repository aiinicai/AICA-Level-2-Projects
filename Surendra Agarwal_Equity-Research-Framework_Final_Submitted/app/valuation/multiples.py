"""Relative valuation multiples — Module 7.

All multiples here are computed for a single company/period from a
FinancialStatement (which must carry a `price`) plus a back-solved
EBITDA. Peer/historical comparison (median, premium/discount) lives in
app/analysis/peers.py, which consumes these MetricResults rather than
recomputing anything — this module has no knowledge of peers.
"""

from __future__ import annotations

from app.analysis.fundamentals import compute_ebitda
from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, MetricResult


def compute_market_cap(stmt: FinancialStatement) -> MetricResult:
    inputs = {"price": stmt.price, "num_equity_shares": stmt.num_equity_shares}
    if not stmt.price or not stmt.num_equity_shares:
        return MetricResult(
            metric_name="Market Capitalization", formula="Price * Number of Equity Shares",
            inputs=inputs, value=None, unit=UnitOfMeasure.INR_CRORE, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    value = (stmt.price * stmt.num_equity_shares) / 1e7  # absolute INR -> crore
    return MetricResult(
        metric_name="Market Capitalization", formula="(Price * Number of Equity Shares) / 1e7",
        inputs=inputs, value=round(value, 2), unit=UnitOfMeasure.INR_CRORE,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_enterprise_value(stmt: FinancialStatement) -> MetricResult:
    market_cap = compute_market_cap(stmt)
    net_debt = None
    if stmt.borrowings is not None and stmt.cash_and_bank is not None:
        net_debt = stmt.borrowings - stmt.cash_and_bank
    inputs = {"market_cap": market_cap.value, "net_debt": net_debt}
    if market_cap.status != DataStatus.OK or net_debt is None:
        return MetricResult(
            metric_name="Enterprise Value", formula="Market Cap + Net Debt", inputs=inputs,
            value=None, unit=UnitOfMeasure.INR_CRORE, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    return MetricResult(
        metric_name="Enterprise Value", formula="Market Cap + (Borrowings - Cash & Bank)",
        inputs=inputs, value=round(market_cap.value + net_debt, 2), unit=UnitOfMeasure.INR_CRORE,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_pe(stmt: FinancialStatement) -> MetricResult:
    from app.analysis.shareholder import compute_eps

    eps = compute_eps(stmt)
    inputs = {"price": stmt.price, "eps": eps.value}
    if not stmt.price or eps.status != DataStatus.OK or not eps.value:
        return MetricResult(
            metric_name="P/E", formula="Price / EPS", inputs=inputs, value=None,
            unit=UnitOfMeasure.RATIO, period=stmt.period, status=DataStatus.MISSING_INPUT,
        )
    return MetricResult(
        metric_name="P/E", formula="Price / EPS", inputs=inputs,
        value=round(stmt.price / eps.value, 2), unit=UnitOfMeasure.RATIO,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_ev_ebitda(stmt: FinancialStatement) -> MetricResult:
    ev = compute_enterprise_value(stmt)
    ebitda = compute_ebitda(stmt)
    inputs = {"enterprise_value": ev.value, "ebitda": ebitda.value}
    if ev.status != DataStatus.OK or ebitda.status != DataStatus.OK or not ebitda.value:
        return MetricResult(
            metric_name="EV/EBITDA", formula="Enterprise Value / EBITDA", inputs=inputs,
            value=None, unit=UnitOfMeasure.RATIO, period=stmt.period, status=DataStatus.MISSING_INPUT,
        )
    return MetricResult(
        metric_name="EV/EBITDA", formula="Enterprise Value / EBITDA", inputs=inputs,
        value=round(ev.value / ebitda.value, 2), unit=UnitOfMeasure.RATIO,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_pb(stmt: FinancialStatement) -> MetricResult:
    """P/B = Price / Book Value Per Share, Book Value = Equity Share
    Capital + Reserves."""
    inputs = {"price": stmt.price, "equity_share_capital": stmt.equity_share_capital,
              "reserves": stmt.reserves, "num_equity_shares": stmt.num_equity_shares}
    if (not stmt.price or stmt.equity_share_capital is None or stmt.reserves is None
            or not stmt.num_equity_shares):
        return MetricResult(
            metric_name="P/B", formula="Price / ((Equity + Reserves) * 1e7 / Shares)",
            inputs=inputs, value=None, unit=UnitOfMeasure.RATIO, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    book_value_per_share = ((stmt.equity_share_capital + stmt.reserves) * 1e7) / stmt.num_equity_shares
    if book_value_per_share <= 0:
        return MetricResult(
            metric_name="P/B", formula="Price / ((Equity + Reserves) * 1e7 / Shares)",
            inputs={**inputs, "book_value_per_share": book_value_per_share}, value=None,
            unit=UnitOfMeasure.RATIO, period=stmt.period, status=DataStatus.CALCULATION_ERROR,
            data_quality_notes=["Book value per share is non-positive; P/B is not meaningful."],
        )
    return MetricResult(
        metric_name="P/B", formula="Price / ((Equity + Reserves) * 1e7 / Shares)",
        inputs={**inputs, "book_value_per_share": round(book_value_per_share, 2)},
        value=round(stmt.price / book_value_per_share, 2), unit=UnitOfMeasure.RATIO,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_ev_sales(stmt: FinancialStatement) -> MetricResult:
    ev = compute_enterprise_value(stmt)
    inputs = {"enterprise_value": ev.value, "sales": stmt.sales}
    if ev.status != DataStatus.OK or not stmt.sales:
        return MetricResult(
            metric_name="EV/Sales", formula="Enterprise Value / Sales", inputs=inputs,
            value=None, unit=UnitOfMeasure.RATIO, period=stmt.period, status=DataStatus.MISSING_INPUT,
        )
    return MetricResult(
        metric_name="EV/Sales", formula="Enterprise Value / Sales", inputs=inputs,
        value=round(ev.value / stmt.sales, 2), unit=UnitOfMeasure.RATIO,
        period=stmt.period, status=DataStatus.OK,
    )


def compute_all_multiples(stmt: FinancialStatement) -> list[MetricResult]:
    return [
        compute_market_cap(stmt), compute_enterprise_value(stmt),
        compute_pe(stmt), compute_ev_ebitda(stmt), compute_pb(stmt), compute_ev_sales(stmt),
    ]
