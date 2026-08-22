"""Shared metric pivoting/table logic - framework-agnostic (no
Streamlit dependency), used by BOTH the Financial Dashboard UI
(app/ui/pages/financial_dashboard.py) and the markdown report generator
(app/reports/generator.py), so a metric renders identically whether
you're looking at it in the app or in a downloaded report - one
formatting implementation, not two that could silently drift apart.
"""

from __future__ import annotations

import re

import pandas as pd

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, MetricResult

_FY_PATTERN = re.compile(r"^FY(\d{4})$")


def format_metric_value(m: MetricResult) -> str:
    """Pure function: format one MetricResult's value per its unit."""
    if m.status != DataStatus.OK or m.value is None:
        return "N/A"
    if m.unit.value == "percent":
        return f"{m.value:.2%}"
    if m.unit.value == "ratio":
        return f"{m.value:,.2f}x"
    if m.unit.value == "days":
        return f"{m.value:,.1f}"
    if m.unit.value == "inr_crore":
        return f"\u20b9{m.value:,.2f} cr"
    if m.unit.value == "per_share":
        return f"\u20b9{m.value:,.2f}"
    return f"{m.value:,.2f}"


def period_sort_key(period: str) -> tuple[int, str]:
    """Sort standard 'FYxxxx' periods chronologically first; anything
    else (e.g. a CAGR range like 'FY2023-FY2026') sorts after all
    standard periods."""
    match = _FY_PATTERN.match(period)
    if match:
        return (0, f"{int(match.group(1)):06d}")
    return (1, period)


def pivot_metrics_to_wide_table(metrics: list[MetricResult]) -> pd.DataFrame:
    """Pure function: MetricResult list -> a pivoted DataFrame with one
    row per distinct metric_name and one column per distinct period,
    formatted values as cells. Periods ordered chronologically for
    standard 'FYxxxx' periods, with any other format (e.g. a CAGR
    range) appended after those. If the same (metric_name, period) pair
    appears more than once, the last one wins deterministically."""
    if not metrics:
        return pd.DataFrame()

    metric_order: list[str] = []
    period_set: set[str] = set()
    cell_values: dict[tuple[str, str], str] = {}

    for m in metrics:
        if m.metric_name not in metric_order:
            metric_order.append(m.metric_name)
        period_set.add(m.period)
        cell_values[(m.metric_name, m.period)] = format_metric_value(m)

    periods_sorted = sorted(period_set, key=period_sort_key)

    data = {
        period: [cell_values.get((metric, period), "") for metric in metric_order]
        for period in periods_sorted
    }
    return pd.DataFrame(data, index=metric_order)


def dataframe_to_markdown_table(df: pd.DataFrame, index_label: str = "Metric") -> str:
    """Pure function: convert a pivoted DataFrame into a GitHub-flavored
    markdown pipe table, with the row index as the first column. Blank
    cells (metric doesn't apply to that period) render as an em dash
    rather than an empty cell, for readability in the rendered table."""
    if df.empty:
        return "*No data available.*"

    header = "| " + index_label + " | " + " | ".join(str(c) for c in df.columns) + " |"
    separator = "|" + "---|" * (len(df.columns) + 1)
    rows = []
    for idx, row in df.iterrows():
        cells = [str(idx)] + [str(v) if str(v).strip() else "\u2014" for v in row]
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, separator, *rows])


def build_key_financials_metrics(statements: list[FinancialStatement]) -> list[MetricResult]:
    """Absolute-value key financial figures (Sales/Revenue, Net Profit,
    Total Assets) as MetricResult rows.

    compute_all_fundamentals() only derives RATIOS and MARGINS from
    these figures (EBITDA Margin, ROE, etc.) - the raw absolute figures
    themselves were never separately surfaced as MetricResult objects,
    so they never appeared in the pivoted Fundamentals table or the
    report's Historical Financial Analysis section, even though
    EBITDA/EBIT (also absolute figures) were. This closes that gap.
    """
    results: list[MetricResult] = []
    for stmt in statements:
        for label, value, formula in (
            ("Sales / Revenue", stmt.sales, "Directly from financial statement"),
            ("Net Profit", stmt.net_profit, "Directly from financial statement"),
            ("Total Assets", stmt.total_assets, "Directly from financial statement"),
        ):
            status = DataStatus.OK if value is not None else DataStatus.MISSING_INPUT
            results.append(
                MetricResult(
                    metric_name=label, formula=formula, inputs={}, value=value,
                    unit=UnitOfMeasure.INR_CRORE, period=stmt.period, status=status,
                )
            )
    return results
