"""
capex_npv.dashboard
====================
Interactive Streamlit dashboard for the Capex NPV model.

Run with:
    capex-npv-dashboard
or:
    streamlit run capex_npv/dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from capex_npv.model import CapexNPVModel


TEAL = "#0E9F6E"
AMBER = "#D97706"
INK = "#1A2433"
MUTED = "#64748B"
BORDER = "#E2E8F0"


def _money(x, currency):
    sign = "-" if x < 0 else ""
    return f"{sign}{currency}{abs(x):,.0f}"


def _kpi_card(label, value, positive=True, help_text=""):
    color = TEAL if positive else AMBER
    return f"""
    <div style="background:#FFFFFF; border:1px solid {BORDER}; border-radius:12px;
                padding:16px 18px; height:100%;">
        <div style="font-size:12px; color:{MUTED}; text-transform:uppercase;
                    letter-spacing:0.04em; margin-bottom:8px;">{label}</div>
        <div style="font-family:'IBM Plex Mono', monospace; font-size:22px;
                    font-weight:600; color:{color}; white-space:nowrap;">{value}</div>
        <div style="font-size:11.5px; color:{MUTED}; margin-top:4px;">{help_text}</div>
    </div>
    """


def run():
    st.set_page_config(page_title="Capex Ledger — NPV Dashboard", layout="wide")

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');
        .stApp {{ background-color: #F7F9FB; }}
        html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {INK}; }}
        section[data-testid="stSidebar"] {{ background-color: #FFFFFF; border-right: 1px solid {BORDER}; }}
        section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] label {{
            color: {INK} !important; font-weight: 500; font-size: 13px;
        }}
        h1, h2, h3 {{ color: {INK}; font-weight: 700; }}
        .stAlert {{ border-radius: 10px; }}
        .block-container {{ padding-top: 2rem; }}
        [data-testid="stExpander"] {{ background-color: #FFFFFF; border: 1px solid {BORDER}; border-radius: 10px; }}
        .helper {{ color: {MUTED}; font-size: 13.5px; margin-top: -8px; margin-bottom: 12px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("💡 Capex Ledger — NPV Appraisal Dashboard")
    st.markdown(
        "<p class='helper'>Adjust the assumptions on the left. Every chart and number updates instantly — "
        "nothing to click or run.</p>",
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------
    # SIDEBAR INPUTS
    # -----------------------------------------------------------------
    with st.sidebar:
        st.header("⚙️ Assumptions")

        currency = st.text_input("Currency symbol", value="₹")
        initial_capex = st.number_input(
            "Initial Capex", value=500_000, step=10_000,
            help="The upfront investment required for the project (Year 0 outflow)."
        )
        base_revenue = st.number_input(
            "Base Year Revenue", value=400_000, step=10_000,
            help="Current revenue before the project starts growing it."
        )

        with st.expander("📈 Growth & Margin", expanded=True):
            growth_mode = st.radio("Sales growth", ["Same rate every year", "Different rate per year"], horizontal=False, index=1)
            if growth_mode == "Same rate every year":
                growth_flat = st.slider("Sales growth % (all 10 yrs)", -20.0, 40.0, 8.0, 0.5)
                sales_growth = growth_flat / 100
            else:
                st.caption("Enter a growth rate for each of the 10 years.")
                default_growth = [15.0, 10.0, 10.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0]
                sales_growth = []
                cols = st.columns(5)
                for i in range(10):
                    with cols[i % 5]:
                        sales_growth.append(
                            st.number_input(f"Y{i+1} %", value=default_growth[i], step=0.5, key=f"g{i}") / 100
                        )

            margin_mode = st.radio("EBITDA margin", ["Same rate every year", "Different rate per year"], horizontal=False)
            if margin_mode == "Same rate every year":
                margin_flat = st.slider("EBITDA margin %", 0.0, 60.0, 20.0, 0.5)
                ebitda_margin = margin_flat / 100
            else:
                st.caption("Enter a margin for each of the 10 years.")
                ebitda_margin = []
                cols = st.columns(5)
                for i in range(10):
                    with cols[i % 5]:
                        ebitda_margin.append(
                            st.number_input(f"Y{i+1} %", value=20.0, step=0.5, key=f"m{i}") / 100
                        )

        with st.expander("🏦 Financing & Tax", expanded=False):
            wacc = st.slider("Discount Rate / WACC %", 1.0, 30.0, 12.0, 0.5,
                              help="Your required rate of return — higher WACC discounts future cash flows more heavily.")
            tax_rate = st.slider("Tax Rate %", 0.0, 45.0, 25.0, 0.5)
            useful_life = st.slider("Useful Life of Asset (yrs)", 1, 10, 10,
                                     help="Number of years the capex is depreciated over.")

        with st.expander("💰 Working Capital & Capex", expanded=False):
            maintenance_capex_pct = st.slider("Maintenance Capex % of Revenue", 0.0, 15.0, 2.0, 0.5)
            wc_pct_of_sales = st.slider("Working Capital % of Δ Sales", 0.0, 25.0, 5.0, 0.5)

        with st.expander("🔭 Terminal Value", expanded=False):
            terminal_growth = st.slider("Terminal Growth %", 0.0, 8.0, 0.0, 0.25,
                                         help="Perpetual growth assumed after Year 10. Leave at 0 to ignore.")
            salvage_value = st.number_input("Salvage Value (Yr 10)", value=0, step=10_000)

            if wacc / 100 <= terminal_growth / 100 and terminal_growth > 0:
                st.warning("WACC must be higher than the terminal growth rate.")

    # -----------------------------------------------------------------
    # BUILD MODEL
    # -----------------------------------------------------------------
    model = CapexNPVModel(
        initial_capex=initial_capex,
        base_revenue=base_revenue,
        sales_growth=sales_growth,
        ebitda_margin=ebitda_margin,
        tax_rate=tax_rate / 100,
        discount_rate=wacc / 100,
        useful_life=useful_life,
        maintenance_capex_pct=maintenance_capex_pct / 100,
        wc_pct_of_sales=wc_pct_of_sales / 100,
        terminal_growth=terminal_growth / 100,
        salvage_value=salvage_value,
    )
    projection = model.build_projection()
    npv_val = model.npv()
    irr_val = model.irr()
    payback = model.payback_period()
    pi = model.profitability_index()
    pv_inflows = npv_val + initial_capex

    # -----------------------------------------------------------------
    # DECISION BANNER
    # -----------------------------------------------------------------
    if npv_val >= 0:
        st.success(f"✅ **ACCEPT** — this project is expected to create {_money(npv_val, currency)} of value in today's terms.")
    else:
        st.error(f"❌ **REJECT** — this project is expected to destroy {_money(abs(npv_val), currency)} of value in today's terms.")

    # -----------------------------------------------------------------
    # KPI CARDS (custom HTML — avoids Streamlit's metric truncation)
    # -----------------------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(_kpi_card("NPV", _money(npv_val, currency), npv_val >= 0, "Net Present Value"), unsafe_allow_html=True)
    with c2:
        irr_text = f"{irr_val:.1%}" if irr_val is not None else "n/a"
        st.markdown(_kpi_card("IRR", irr_text, irr_val is not None and irr_val >= wacc/100, f"vs. WACC {wacc:.1f}%"), unsafe_allow_html=True)
    with c3:
        pb_text = f"{payback:.2f} yrs" if payback else "> 10 yrs"
        st.markdown(_kpi_card("Payback", pb_text, payback is not None, "Time to recover outlay"), unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi_card("Profitability Index", f"{pi:.2f}x", pi >= 1, "PV inflows ÷ Capex"), unsafe_allow_html=True)
    with c5:
        st.markdown(_kpi_card("Total PV Inflows", _money(pv_inflows, currency), True, "Present value of all inflows"), unsafe_allow_html=True)

    st.write("")

    # -----------------------------------------------------------------
    # TABS: chart / table / sensitivity
    # -----------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(["📊 Cash Flow Chart", "📋 10-Year Projection", "🌡️ Sensitivity"])

    with tab1:
        cum_pv = projection["PV of FCF"].cumsum() - initial_capex

        fig = go.Figure()
        fig.add_bar(
            x=projection["Year"], y=projection["FCF"], name="Free Cash Flow",
            marker_color=[TEAL if v >= 0 else AMBER for v in projection["FCF"]],
        )
        fig.add_scatter(
            x=projection["Year"], y=cum_pv, name="Cumulative PV (vs. outlay)",
            mode="lines+markers", line=dict(color="#2563EB", width=2.5), yaxis="y2",
        )
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font=dict(family="Inter", color=INK),
            yaxis=dict(title="Free Cash Flow", gridcolor=BORDER),
            yaxis2=dict(title="Cumulative PV", overlaying="y", side="right", showgrid=False),
            xaxis=dict(gridcolor=BORDER),
            legend=dict(orientation="h", y=1.12),
            margin=dict(t=20, b=10, l=10, r=10),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Bars show each year's free cash flow. The line shows cumulative present value against your "
                   "initial outlay — where it crosses zero is your payback point.")

    with tab2:
        display_df = projection.drop(columns=["Discount Factor"]).copy()
        for col in display_df.columns:
            if col != "Year":
                display_df[col] = display_df[col].map(lambda x: f"{x:,.0f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab3:
        st.caption("Rows: WACC. Columns: flat sales growth rate (overrides any custom per-year growth for this grid only).")
        base_growth = (sales_growth if isinstance(sales_growth, float) else 0.08)
        wacc_range = [max(0.01, wacc/100 - 0.04), max(0.01, wacc/100 - 0.02), wacc/100,
                      wacc/100 + 0.02, wacc/100 + 0.04]
        growth_range = [max(-0.1, base_growth - 0.08), base_growth - 0.04, base_growth,
                         base_growth + 0.04, base_growth + 0.08]
        sens = model.sensitivity_table(wacc_range, growth_range)
        st.dataframe(
            sens.style.background_gradient(cmap="RdYlGn", axis=None).format("{:,.0f}"),
            use_container_width=True,
        )


if __name__ == "__main__":
    run()
