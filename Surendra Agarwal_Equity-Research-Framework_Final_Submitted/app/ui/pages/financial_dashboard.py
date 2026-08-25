"""Financial Dashboard page - Revenue, EBITDA, PAT, EPS, ROE, ROCE, D/E, FCF.

Metrics render as a pivot table (metric names as rows, periods as
columns). Pivoting/formatting logic lives in app/reports/metric_tables.py
(framework-agnostic, no Streamlit dependency) and is re-exported here so
this page and the markdown report generator render identically — one
implementation, not two that could silently drift apart.
"""

from __future__ import annotations

import streamlit as st

from app.core.enums import DataStatus
from app.reports.metric_tables import (
    build_key_financials_metrics,
    format_metric_value as _format_value,
    period_sort_key as _period_sort_key,
    pivot_metrics_to_wide_table,
)


def metrics_to_rows(metrics: list) -> list[dict]:
    """Pure function: MetricResult list -> long-format table rows
    (Metric, Period, Value, Status). Kept for callers that still want
    the one-row-per-(metric,period) shape; the page itself uses
    pivot_metrics_to_wide_table() instead."""
    return [
        {
            "Metric": m.metric_name, "Period": m.period,
            "Value": _format_value(m),
            "Status": m.status.value,
        }
        for m in metrics
    ]


def render() -> None:
    st.header("Financial Dashboard")

    company = st.session_state.get("company")
    if company is None:
        st.info("Load a company on the Company Input page first.")
        return

    st.subheader(f"{company.name} ({company.ticker})")

    statements = st.session_state.get("statements", [])
    if statements:
        latest = statements[-1]
        cols = st.columns(4)
        cols[0].metric("Sales", f"₹{latest.sales:,.0f} cr" if latest.sales else "N/A")
        cols[1].metric("Net Profit", f"₹{latest.net_profit:,.0f} cr" if latest.net_profit else "N/A")
        cols[2].metric("Total Assets", f"₹{latest.total_assets:,.0f} cr" if latest.total_assets else "N/A")
        cols[3].metric("Period", latest.period)

        st.subheader("Key Financials")
        st.dataframe(
            pivot_metrics_to_wide_table(build_key_financials_metrics(statements)),
            use_container_width=True,
        )

    fundamental_metrics = st.session_state.get("fundamental_metrics", [])
    if fundamental_metrics:
        st.subheader("Fundamentals")
        st.dataframe(pivot_metrics_to_wide_table(fundamental_metrics), use_container_width=True)
    else:
        st.info("No fundamentals computed yet.")

    cashflow_metrics = st.session_state.get("cashflow_metrics", [])
    if cashflow_metrics:
        st.subheader("Cash Flow")
        st.dataframe(pivot_metrics_to_wide_table(cashflow_metrics), use_container_width=True)

    working_capital_metrics = st.session_state.get("working_capital_metrics", [])
    if working_capital_metrics:
        st.subheader("Working Capital")
        st.dataframe(pivot_metrics_to_wide_table(working_capital_metrics), use_container_width=True)

    shareholder_metrics = st.session_state.get("shareholder_metrics", [])
    if shareholder_metrics:
        st.subheader("Shareholder Metrics")
        st.caption(
            "Promoter Holding/Pledge show 'unavailable' unless manually entered "
            "on the Company Input page — not present in the Screener export."
        )
        st.dataframe(pivot_metrics_to_wide_table(shareholder_metrics), use_container_width=True)

    trends = st.session_state.get("trends", [])
    if trends:
        st.subheader("Trends")
        for t in trends:
            st.write(f"**{t.metric_name}**: {t.direction.value.upper()} "
                     f"(significance: {t.significance.value})")
