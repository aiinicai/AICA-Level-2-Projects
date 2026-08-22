"""Shareholder metrics - Module 2.

Promoter holding and promoter pledge are NOT present in the Screener
"Data Sheet" export our loader consumes (that data lives in Screener's
shareholding-pattern page/API, a different source entirely). Rather
than silently omit them or fabricate a plausible-looking number, these
functions read from FinancialStatement.promoter_holding_pct /
promoter_pledge_pct - fields that loaders.py NEVER populates, only a
caller (e.g. a UI manual-entry form) can set explicitly. If unset, the
metric correctly reports status=UNAVAILABLE; if set, it reports the
value with confidence=MEDIUM and a data-quality note flagging it as a
manual entry, not from the primary source - the distinction between
"I don't have this" and "someone told me this" stays visible throughout,
never collapsed into a single silent "here's a number."
"""

from __future__ import annotations

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, MetricResult


def compute_eps(stmt: FinancialStatement) -> MetricResult:
    """EPS = Net Profit (in INR) / Number of Equity Shares.

    Net Profit is stored in INR crore; converted to absolute INR before
    dividing by the (absolute) share count so the result is EPS in
    rupees, not crore.
    """
    inputs = {"net_profit_cr": stmt.net_profit, "num_equity_shares": stmt.num_equity_shares}
    if stmt.net_profit is None or not stmt.num_equity_shares:
        return MetricResult(
            metric_name="EPS", formula="(Net Profit in INR crore * 1e7) / Number of Equity Shares",
            inputs=inputs, value=None, unit=UnitOfMeasure.PER_SHARE, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
        )
    value = (stmt.net_profit * 1e7) / stmt.num_equity_shares
    return MetricResult(
        metric_name="EPS", formula="(Net Profit in INR crore * 1e7) / Number of Equity Shares",
        inputs=inputs, value=round(value, 2), unit=UnitOfMeasure.PER_SHARE, period=stmt.period,
        status=DataStatus.OK,
    )


def compute_dividend_payout(stmt: FinancialStatement) -> MetricResult:
    inputs = {"dividend_amount": stmt.dividend_amount, "net_profit": stmt.net_profit}
    if stmt.dividend_amount is None or not stmt.net_profit:
        return MetricResult(
            metric_name="Dividend Payout Ratio", formula="Dividend Amount / Net Profit",
            inputs=inputs, value=None, unit=UnitOfMeasure.PERCENT, period=stmt.period,
            status=DataStatus.MISSING_INPUT,
            data_quality_notes=["No dividend paid in this period, or Net Profit unavailable."],
        )
    return MetricResult(
        metric_name="Dividend Payout Ratio", formula="Dividend Amount / Net Profit",
        inputs=inputs, value=round(stmt.dividend_amount / stmt.net_profit, 4),
        unit=UnitOfMeasure.PERCENT, period=stmt.period, status=DataStatus.OK,
    )


def compute_promoter_holding(stmt: FinancialStatement) -> MetricResult:
    """Reads FinancialStatement.promoter_holding_pct if a caller set it
    (e.g. via a manual-entry UI form). Never populated by loaders.py —
    see module docstring."""
    if stmt.promoter_holding_pct is None:
        return MetricResult(
            metric_name="Promoter Holding", formula="N/A - requires shareholding pattern data",
            inputs={}, value=None, unit=UnitOfMeasure.PERCENT, period=stmt.period,
            status=DataStatus.UNAVAILABLE,
            data_quality_notes=[
                "Promoter holding is not present in the Screener 'Data Sheet' export "
                "and was not manually entered for this period."
            ],
        )
    return MetricResult(
        metric_name="Promoter Holding", formula="Manually entered (not from primary data source)",
        inputs={"promoter_holding_pct": stmt.promoter_holding_pct},
        value=round(stmt.promoter_holding_pct, 4), unit=UnitOfMeasure.PERCENT, period=stmt.period,
        status=DataStatus.OK,
        data_quality_notes=[
            "This value was manually entered, not sourced from the Screener export "
            "or independently verified by this application. Confirm against a "
            "current shareholding-pattern filing before relying on it."
        ],
    )


def compute_promoter_pledge(stmt: FinancialStatement) -> MetricResult:
    """Reads FinancialStatement.promoter_pledge_pct if a caller set it.
    Never populated by loaders.py — see module docstring."""
    if stmt.promoter_pledge_pct is None:
        return MetricResult(
            metric_name="Promoter Pledge", formula="N/A - requires shareholding pattern data",
            inputs={}, value=None, unit=UnitOfMeasure.PERCENT, period=stmt.period,
            status=DataStatus.UNAVAILABLE,
            data_quality_notes=[
                "Promoter pledge is not present in the Screener 'Data Sheet' export "
                "and was not manually entered for this period."
            ],
        )
    return MetricResult(
        metric_name="Promoter Pledge", formula="Manually entered (not from primary data source)",
        inputs={"promoter_pledge_pct": stmt.promoter_pledge_pct},
        value=round(stmt.promoter_pledge_pct, 4), unit=UnitOfMeasure.PERCENT, period=stmt.period,
        status=DataStatus.OK,
        data_quality_notes=[
            "This value was manually entered, not sourced from the Screener export "
            "or independently verified by this application. Confirm against a "
            "current shareholding-pattern filing before relying on it."
        ],
    )


def compute_all_shareholder_metrics(statements: list[FinancialStatement]) -> list[MetricResult]:
    """Convenience: run every shareholder metric across all statements,
    matching the compute_all_* pattern in fundamentals.py/cashflow.py/
    working_capital.py."""
    results: list[MetricResult] = []
    for stmt in statements:
        results.extend([
            compute_eps(stmt), compute_dividend_payout(stmt),
            compute_promoter_holding(stmt), compute_promoter_pledge(stmt),
        ])
    return results
