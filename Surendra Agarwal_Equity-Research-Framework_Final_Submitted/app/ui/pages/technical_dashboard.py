"""Technical Dashboard page - price, SMA, RSI, MACD, volume.

Charts are built with Plotly (already a pinned dependency) via pure,
Streamlit-free functions that return go.Figure objects - testable by
inspecting the figure's trace data directly, not just "did it render."
The SMA/RSI series plotted here come from app/analysis/technical.py's
compute_sma_series()/compute_rsi_series(), the same functions the
point-in-time metrics use, so the chart and the numeric summary below
it can never disagree.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import streamlit as st

from app.core.enums import DataStatus

_SMA_COLORS = {20: "#1f77b4", 50: "#ff7f0e", 100: "#2ca02c", 200: "#d62728"}


def format_technical_summary(metrics: list) -> list[dict]:
    """Pure function: MetricResult list -> table rows."""
    rows = []
    for m in metrics:
        value_str = f"{m.value:,.2f}" if m.value is not None else "N/A"
        rows.append({"Indicator": m.metric_name, "Value": value_str, "Status": m.status.value})
    return rows


def build_candlestick_figure(
    price_df: pd.DataFrame, sma_windows: tuple[int, ...] = (20, 50, 100, 200),
) -> go.Figure:
    """Candlestick price chart with SMA overlays. SMA lines that need
    more history than is available (e.g. SMA 200 on a 100-day series)
    are simply shorter/absent for their leading NaN period, rendered
    that way by Plotly automatically — never backfilled or faked."""
    from app.analysis.technical import compute_sma_series

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=price_df.index, open=price_df["open"], high=price_df["high"],
        low=price_df["low"], close=price_df["close"], name="Price",
    ))
    for window in sma_windows:
        if len(price_df) < window:
            continue  # not enough history for this SMA at all — omit rather than show a broken line
        sma_series = compute_sma_series(price_df["close"], window)
        fig.add_trace(go.Scatter(
            x=price_df.index, y=sma_series, mode="lines", name=f"SMA {window}",
            line=dict(width=1.3, color=_SMA_COLORS.get(window)),
        ))
    fig.update_layout(
        title="Price with Moving Averages", xaxis_title="Date", yaxis_title="Price (₹)",
        xaxis_rangeslider_visible=False, height=450, legend=dict(orientation="h", y=1.02),
    )
    return fig


def build_rsi_figure(price_df: pd.DataFrame, period: int = 14) -> go.Figure:
    """RSI subplot with standard 30/70 overbought/oversold reference lines."""
    from app.analysis.technical import compute_rsi_series

    rsi_series = compute_rsi_series(price_df["close"], period)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=price_df.index, y=rsi_series, mode="lines", name=f"RSI ({period})", line=dict(color="#9467bd")))
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
    fig.update_layout(
        title=f"RSI ({period})", xaxis_title="Date", yaxis_title="RSI",
        yaxis_range=[0, 100], height=250,
    )
    return fig


def build_volume_figure(price_df: pd.DataFrame) -> go.Figure:
    """Volume bars, colored green/red by whether the day closed up or down."""
    colors = [
        "#2ca02c" if c >= o else "#d62728"
        for o, c in zip(price_df["open"], price_df["close"])
    ]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=price_df.index, y=price_df["volume"], marker_color=colors, name="Volume"))
    fig.update_layout(title="Volume", xaxis_title="Date", yaxis_title="Shares Traded", height=200)
    return fig


def render() -> None:
    st.header("Technical Dashboard")

    company = st.session_state.get("company")
    if company is None:
        st.info("Load a company on the Company Input page first.")
        return

    price_df = st.session_state.get("price_df")
    if price_df is None:
        st.info(
            "No price history loaded. Upload an NSE price-history CSV on the "
            "Company Input page to enable technical analysis."
        )
        return

    st.subheader(f"{company.name} ({company.ticker}) — Price History")
    st.caption(f"{len(price_df)} trading days, {price_df.index.min().date()} to {price_df.index.max().date()}")

    st.plotly_chart(build_candlestick_figure(price_df), use_container_width=True)
    st.plotly_chart(build_rsi_figure(price_df), use_container_width=True)
    st.plotly_chart(build_volume_figure(price_df), use_container_width=True)

    technical_metrics = st.session_state.get("technical_metrics", [])
    if technical_metrics:
        st.subheader("Indicators (latest)")
        st.table(format_technical_summary(technical_metrics))
    else:
        st.info("No technical indicators computed yet.")
