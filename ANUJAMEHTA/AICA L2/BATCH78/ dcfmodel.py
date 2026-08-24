import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io
import json
from fpdf import FPDF

# Page Configuration
st.set_page_config(
    page_title="Institutional DCF Valuation Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Executive CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .undervalued-badge {
        background-color: #DEF7EC;
        color: #03543F;
        font-weight: bold;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .overvalued-badge {
        background-color: #FDE8E8;
        color: #9B1C1C;
        font-weight: bold;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .fair-badge {
        background-color: #FEF08A;
        color: #713F12;
        font-weight: bold;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# Helper Functions: Sample CSV, Excel, and PDF Generator
# ----------------------------------------------------
def generate_sample_csv():
    """Generates a sample template containing all 5 Core Data Areas in Rs (₹)."""
    data = {
        "Parameter_Group": [
            "1_Historical_Financials", "1_Historical_Financials", "1_Historical_Financials", "1_Historical_Financials", "1_Historical_Financials", "1_Historical_Financials", "1_Historical_Financials", "1_Historical_Financials",
            "2_Financial_Projections", "2_Financial_Projections", "2_Financial_Projections", "2_Financial_Projections",
            "3_Capital_Structure", "3_Capital_Structure", "3_Capital_Structure", "3_Capital_Structure", "3_Capital_Structure",
            "4_Cost_of_Capital", "4_Cost_of_Capital", "4_Cost_of_Capital", "4_Cost_of_Capital", "4_Cost_of_Capital",
            "5_Terminal_Value_Scenarios", "5_Terminal_Value_Scenarios", "5_Terminal_Value_Scenarios", "5_Terminal_Value_Scenarios"
        ],
        "Parameter_Name": [
            "Company Name", "Currency", "Current Stock Price", "Shares Outstanding (Millions)", "Last FY Revenue (Millions)", "Operating Margin EBIT (%)", "Effective Tax Rate (%)", "CapEx % of Revenue",
            "Forecast Horizon (Years)", "Revenue Growth Rate Y1-Y5 (%)", "Terminal Operating Margin (%)", "Reinvestment Rate (%)",
            "Total Debt (Millions)", "Cash & Cash Equivalents (Millions)", "Preferred Stock (Millions)", "Non-Controlling Interest (Millions)", "Non-Operating Assets (Millions)",
            "Risk Free Rate (%)", "Beta", "Equity Risk Premium (%)", "Cost of Debt Pre-Tax (%)", "Target Debt Weight (%)",
            "Perpetual Terminal Growth Rate (%)", "Exit Multiple EV/EBITDA", "Bull Case Growth Adjustment (+%)", "Bear Case Growth Adjustment (-%)"
        ],
        "Value": [
            "Reliance Industries Ltd", "₹", 2500.0, 6760.0, 900000.0, 16.5, 25.0, 6.0,
            5, 11.5, 18.0, 30.0,
            300000.0, 200000.0, 0.0, 0.0, 15000.0,
            7.1, 1.05, 5.5, 7.5, 25.0,
            3.0, 12.5, 3.0, 3.0
        ]
    }
    return pd.DataFrame(data)

def export_to_excel(summary_df, fcff_df, wacc_breakdown, sensitivity_df):
    """Exports full valuation data to Excel with multiple sheets."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Valuation Summary', index=False)
        fcff_df.to_excel(writer, sheet_name='Cash Flow Projections', index=False)
        pd.DataFrame([wacc_breakdown]).to_excel(writer, sheet_name='WACC Derivation', index=False)
        sensitivity_df.to_excel(writer, sheet_name='Sensitivity Analysis')
    return output.getvalue()

def generate_pdf_report(company, currency, current_price, intrinsic_val, status, upside, wacc, base_val, bull_val, bear_val, proj_df):
    """Generates an executive PDF report for the DCF valuation."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, f"DCF Equity Valuation Report", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 11)
    pdf.cell(0, 8, f"Company: {company} | Valuation Currency: {currency}", ln=True, align="C")
    pdf.ln(5)

    # Executive Summary Box
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(240, 244, 248)
    pdf.cell(0, 8, "1. Executive Summary", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 7, f"Current Market Price: {currency} {current_price:.2f}", border=1)
    pdf.cell(95, 7, f"Weighted Intrinsic Value: {currency} {intrinsic_val:.2f}", border=1, ln=True)
    pdf.cell(95, 7, f"Valuation Status: {status}", border=1)
    pdf.cell(95, 7, f"Implied Upside / Downside: {upside:.1f}%", border=1, ln=True)
    pdf.cell(190, 7, f"Discount Rate (WACC): {wacc:.2f}%", border=1, ln=True)
    pdf.ln(5)

    # Multi-Scenario Valuation Table
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2. Multi-Scenario Valuation Breakdown", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(63, 7, f"Bear Case: {currency} {bear_val:.2f}", border=1)
    pdf.cell(64, 7, f"Base Case: {currency} {base_val:.2f}", border=1)
    pdf.cell(63, 7, f"Bull Case: {currency} {bull_val:.2f}", border=1, ln=True)
    pdf.ln(5)

    # Financial Projections Table
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "3. Explicit Cash Flow Projections", ln=True, fill=True)
    pdf.set_font("Helvetica", "B", 9)
    cols = list(proj_df.columns)
    pdf.cell(30, 7, cols[0], border=1)
    pdf.cell(40, 7, cols[1], border=1)
    pdf.cell(40, 7, cols[2], border=1)
    pdf.cell(40, 7, cols[3], border=1)
    pdf.cell(40, 7, cols[4], border=1, ln=True)

    pdf.set_font("Helvetica", "", 9)
    for _, row in proj_df.iterrows():
        pdf.cell(30, 6, str(row[cols[0]]), border=1)
        pdf.cell(40, 6, f"{row[cols[1]]:,.2f}", border=1)
        pdf.cell(40, 6, f"{row[cols[2]]:,.2f}", border=1)
        pdf.cell(40, 6, f"{row[cols[3]]:,.2f}", border=1)
        pdf.cell(40, 6, f"{row[cols[4]]:,.2f}", border=1, ln=True)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Generated by Institutional DCF Valuation Engine. Strictly for analysis and educational purposes.", align="C")
    
    return bytes(pdf.output())

# ----------------------------------------------------
# Session State Initialization & Clear Data Function
# ----------------------------------------------------
if "analysis_run" not in st.session_state:
    st.session_state.analysis_run = False

def clear_all_data():
    """Resets all input parameters and clears analysis state."""
    st.session_state.uploaded_params = {}
    st.session_state.analysis_run = False
    st.rerun()

if "uploaded_params" not in st.session_state:
    st.session_state.uploaded_params = {}

# ----------------------------------------------------
# Title & Header
# ----------------------------------------------------
st.markdown('<div class="main-header">📈 DCF Valuation & Intrinsic Value Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Institutional-Grade Share Valuation Framework with Interactive Controls & Reports (in ₹ / INR)</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# Sidebar Controls & File Upload
# ----------------------------------------------------
st.sidebar.title("🎛️ Model Controls")

model_template = st.sidebar.selectbox(
    "Valuation Template",
    ["FCFF (Free Cash Flow to Firm)", "FCFE (Free Cash Flow to Equity)"],
    help="FCFF evaluates overall firm enterprise value; FCFE evaluates direct cash flow to equity holders."
)

data_input_mode = st.sidebar.radio(
    "Data Source Mode",
    ["Interactive UI Form", "Upload File (CSV/Excel)"]
)

if data_input_mode == "Upload File (CSV/Excel)":
    uploaded_file = st.sidebar.file_uploader("Upload 5-Area Data File", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
            st.sidebar.success(f"Loaded {len(df_upload)} records.")
            for _, row in df_upload.iterrows():
                st.session_state.uploaded_params[str(row["Parameter_Name"]).strip()] = row["Value"]
        except Exception as e:
            st.sidebar.error(f"Error parsing file: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("Actions & Controls")

col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
        st.session_state.analysis_run = True
with col_btn2:
    if st.button("🧹 Clear Data", use_container_width=True):
        clear_all_data()

st.sidebar.markdown("---")
sample_csv_bytes = generate_sample_csv().to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    "📥 Download CSV Template (₹)",
    data=sample_csv_bytes,
    file_name="dcf_valuation_template_inr.csv",
    mime="text/csv",
    use_container_width=True
)

# Helper getter
def get_val(param_name, default_val):
    if param_name in st.session_state.uploaded_params:
        try:
            return type(default_val)(st.session_state.uploaded_params[param_name])
        except:
            return default_val
    return default_val

# ----------------------------------------------------
# Main UI Navigation Tabs (Includes Tab 6 for Export)
# ----------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ Base Financials",
    "2️⃣ Projections",
    "3️⃣ Capital Structure",
    "4️⃣ Cost of Capital (WACC)",
    "5️⃣ Scenarios & Terminal Value",
    "6️⃣ Valuation & Export Report"
])

with tab1:
    st.markdown("#### Core Area 1: Historical Financial Statements & Base Metrics")
    c1, c2, c3, c4 = st.columns(4)
    company_name = c1.text_input("Company Name", get_val("Company Name", "Reliance Industries Ltd"))
    currency = c2.text_input("Currency Symbol", get_val("Currency", "₹"))
    current_price = c3.number_input(f"Current Stock Price ({currency})", value=float(get_val("Current Stock Price", 2500.0)), min_value=0.01)
    shares_outstanding = c4.number_input("Shares Outstanding (Millions)", value=float(get_val("Shares Outstanding (Millions)", 6760.0)), min_value=0.01)

    c5, c6, c7, c8 = st.columns(4)
    base_revenue = c5.number_input(f"Last FY Revenue ({currency} M)", value=float(get_val("Last FY Revenue (Millions)", 900000.0)), min_value=0.0)
    ebit_margin = c6.number_input("Operating Margin EBIT (%)", value=float(get_val("Operating Margin EBIT (%)", 16.5)))
    tax_rate = c7.number_input("Effective Tax Rate (%)", value=float(get_val("Effective Tax Rate (%)", 25.0)))
    capex_pct_rev = c8.number_input("CapEx (% of Revenue)", value=float(get_val("CapEx % of Revenue", 6.0)))

with tab2:
    st.markdown("#### Core Area 2: Financial Forecasts & Projections")
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    forecast_years = col_p1.slider("Explicit Forecast Period (Years)", 3, 10, int(get_val("Forecast Horizon (Years)", 5)))
    rev_growth = col_p2.number_input("Revenue Growth Rate Y1-Y5 (%)", value=float(get_val("Revenue Growth Rate Y1-Y5 (%)", 11.5)))
    target_margin = col_p3.number_input("Terminal Operating Margin (%)", value=float(get_val("Terminal Operating Margin (%)", 18.0)))
    reinvestment_rate = col_p4.number_input("Reinvestment Rate (%)", value=float(get_val("Reinvestment Rate (%)", 30.0)))

with tab3:
    st.markdown("#### Core Area 3: Capital Structure & Net Debt Bridge")
    cap1, cap2, cap3, cap4, cap5 = st.columns(5)
    total_debt = cap1.number_input(f"Total Debt ({currency} M)", value=float(get_val("Total Debt (Millions)", 300000.0)))
    cash_equivalents = cap2.number_input(f"Cash ({currency} M)", value=float(get_val("Cash & Cash Equivalents (Millions)", 200000.0)))
    preferred_stock = cap3.number_input(f"Preferred Stock ({currency} M)", value=float(get_val("Preferred Stock (Millions)", 0.0)))
    non_controlling = cap4.number_input(f"Non-Controlling Interest ({currency} M)", value=float(get_val("Non-Controlling Interest (Millions)", 0.0)))
    non_op_assets = cap5.number_input(f"Non-Operating Assets ({currency} M)", value=float(get_val("Non-Operating Assets (Millions)", 15000.0)))

with tab4:
    st.markdown("#### Core Area 4: Cost of Capital (WACC / CAPM Derivation)")
    wacc_manual_override = st.checkbox("Manual WACC Override", value=False)
    if wacc_manual_override:
        calculated_wacc = st.number_input("Specify WACC (%)", value=10.5, min_value=1.0, max_value=30.0)
        cost_of_equity = calculated_wacc
        cost_of_debt_after_tax = calculated_wacc
    else:
        w1, w2, w3, w4, w5 = st.columns(5)
        rf_rate = w1.number_input("Risk-Free Rate (%)", value=float(get_val("Risk Free Rate (%)", 7.1)))
        beta = w2.number_input("Beta (Market Risk)", value=float(get_val("Beta", 1.05)))
        erp = w3.number_input("Equity Risk Premium (%)", value=float(get_val("Equity Risk Premium (%)", 5.5)))
        cost_of_debt = w4.number_input("Pre-Tax Cost of Debt (%)", value=float(get_val("Cost of Debt Pre-Tax (%)", 7.5)))
        debt_weight = w5.number_input("Target Debt Weight (%)", value=float(get_val("Target Debt Weight (%)", 25.0)))

        cost_of_equity = rf_rate + (beta * erp)
        cost_of_debt_after_tax = cost_of_debt * (1 - tax_rate / 100.0)
        calculated_wacc = ((100.0 - debt_weight) / 100.0 * cost_of_equity) + (debt_weight / 100.0 * cost_of_debt_after_tax)
        st.info(f"📊 Derived WACC: **{calculated_wacc:.2f}%** | Cost of Equity: **{cost_of_equity:.2f}%** | Cost of Debt (After Tax): **{cost_of_debt_after_tax:.2f}%**")

with tab5:
    st.markdown("#### Core Area 5: Terminal Value & Multi-Scenario Assumptions")
    tv1, tv2, tv3, tv4 = st.columns(4)
    perpetual_growth = tv1.number_input("Perpetual Growth Rate g (%)", value=float(get_val("Perpetual Terminal Growth Rate (%)", 3.0)))
    exit_multiple = tv2.number_input("Exit Multiple EV/EBITDA", value=float(get_val("Exit Multiple EV/EBITDA", 12.5)))
    bull_delta = tv3.number_input("Bull Case Growth Premium (+%)", value=float(get_val("Bull Case Growth Adjustment (+%)", 3.0)))
    bear_delta = tv4.number_input("Bear Case Growth Penalty (-%)", value=float(get_val("Bear Case Growth Adjustment (-%)", 3.0)))

    st.caption("Multi-Scenario Probability Weights")
    sc1, sc2, sc3 = st.columns(3)
    p_base = sc1.slider("Base Weight (%)", 0, 100, 60)
    p_bull = sc2.slider("Bull Weight (%)", 0, 100, 20)
    p_bear = sc3.slider("Bear Weight (%)", 0, 100, 20)

# DCF Calculation Function
def compute_dcf(growth_adj=0.0, margin_adj=0.0, wacc_val=calculated_wacc):
    effective_growth = rev_growth + growth_adj
    effective_margin = target_margin + margin_adj

    revenues, ebits, nopats, fcffs, pv_fcffs = [], [], [], [], []
    curr_rev = base_revenue
    for t in range(1, forecast_years + 1):
        curr_rev *= (1 + effective_growth / 100.0)
        curr_margin = ebit_margin + (effective_margin - ebit_margin) * (t / forecast_years)
        curr_ebit = curr_rev * (curr_margin / 100.0)
        curr_nopat = curr_ebit * (1 - tax_rate / 100.0)
        curr_fcff = curr_nopat * (1 - reinvestment_rate / 100.0)
        pv_fcff = curr_fcff / ((1 + wacc_val / 100.0) ** (t - 0.5))

        revenues.append(curr_rev)
        ebits.append(curr_ebit)
        nopats.append(curr_nopat)
        fcffs.append(curr_fcff)
        pv_fcffs.append(pv_fcff)

    terminal_fcff = fcffs[-1] * (1 + perpetual_growth / 100.0)
    terminal_value = terminal_fcff / ((wacc_val / 100.0) - (perpetual_growth / 100.0)) if wacc_val > perpetual_growth else 0.0
    pv_terminal_value = terminal_value / ((1 + wacc_val / 100.0) ** forecast_years)
    pv_explicit_fcff = sum(pv_fcffs)
    enterprise_value = pv_explicit_fcff + pv_terminal_value

    equity_value = enterprise_value + cash_equivalents + non_op_assets - total_debt - preferred_stock - non_controlling
    intrinsic_value_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0.0

    projection_df = pd.DataFrame({
        "Year": [f"Year {i}" for i in range(1, forecast_years + 1)],
        f"Revenue ({currency}M)": np.round(revenues, 2),
        f"EBIT ({currency}M)": np.round(ebits, 2),
        f"NOPAT ({currency}M)": np.round(nopats, 2),
        f"FCFF ({currency}M)": np.round(fcffs, 2),
        f"PV of FCFF ({currency}M)": np.round(pv_fcffs, 2)
    })

    return {
        "intrinsic_value": intrinsic_value_per_share,
        "equity_value": equity_value,
        "enterprise_value": enterprise_value,
        "pv_explicit": pv_explicit_fcff,
        "pv_terminal": pv_terminal_value,
        "projections": projection_df,
        "fcffs": fcffs,
        "pv_fcffs": pv_fcffs
    }

base_res = compute_dcf()
bull_res = compute_dcf(growth_adj=bull_delta, margin_adj=2.0)
bear_res = compute_dcf(growth_adj=-bear_delta, margin_adj=-3.0)

total_w = p_base + p_bull + p_bear
weighted_val = ((base_res["intrinsic_value"] * p_base) + (bull_res["intrinsic_value"] * p_bull) + (bear_res["intrinsic_value"] * p_bear)) / (total_w if total_w > 0 else 1.0)
upside_pct = ((weighted_val - current_price) / current_price) * 100.0
margin_of_safety = max(0.0, upside_pct)

status_str = "UNDERVALUED" if upside_pct > 10.0 else ("OVERVALUED" if upside_pct < -10.0 else "FAIRLY VALUED")

# ----------------------------------------------------
# TAB 6: Final Valuation Results & Export (Excel & PDF)
# ----------------------------------------------------
with tab6:
    st.markdown("### 📊 Tab 6: Complete Valuation Results & Export Report")
    
    if not st.session_state.analysis_run:
        st.warning("⚠️ Click the **🚀 Run Analysis** button in the sidebar (or below) to perform calculations and view results.")
        if st.button("🚀 Run Valuation Analysis Now", type="primary"):
            st.session_state.analysis_run = True
            st.rerun()
    else:
        # 1. Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.caption("Weighted Intrinsic Value")
            st.markdown(f"### {currency}{weighted_val:.2f}")
            st.caption(f"Base: {currency}{base_res['intrinsic_value']:.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

        with m2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.caption("Current Market Price")
            st.markdown(f"### {currency}{current_price:.2f}")
            st.caption(f"Company: {company_name}")
            st.markdown('</div>', unsafe_allow_html=True)

        with m3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.caption("Valuation Status")
            if upside_pct > 10.0:
                st.markdown(f'<span class="undervalued-badge">UNDERVALUED ({abs(upside_pct):.1f}%)</span>', unsafe_allow_html=True)
            elif upside_pct < -10.0:
                st.markdown(f'<span class="overvalued-badge">OVERVALUED ({abs(upside_pct):.1f}%)</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="fair-badge">FAIRLY VALUED</span>', unsafe_allow_html=True)
            st.caption("Implied Upside/Downside")
            st.markdown('</div>', unsafe_allow_html=True)

        with m4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.caption("Margin of Safety")
            st.markdown(f"### {margin_of_safety:.1f}%")
            st.caption(f"WACC: {calculated_wacc:.2f}%")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # 2. Multi-Scenario Breakdown
        st.markdown("#### 🎯 Scenario Breakdown")
        sc_col1, sc_col2, sc_col3 = st.columns(3)
        sc_col1.metric("🐻 Bear Case Intrinsic Value", f"{currency}{bear_res['intrinsic_value']:.2f}", delta=f"{((bear_res['intrinsic_value']-current_price)/current_price)*100:.1f}% vs Market")
        sc_col2.metric("🎯 Base Case Intrinsic Value", f"{currency}{base_res['intrinsic_value']:.2f}", delta=f"{((base_res['intrinsic_value']-current_price)/current_price)*100:.1f}% vs Market")
        sc_col3.metric("ox Bull Case Intrinsic Value", f"{currency}{bull_res['intrinsic_value']:.2f}", delta=f"{((bull_res['intrinsic_value']-current_price)/current_price)*100:.1f}% vs Market")

        st.markdown("---")

        # 3. Charts
        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown(f"##### 💵 Projected FCFF Cash Flows ({currency} M)")
            df_proj = base_res["projections"]
            fig_cf = go.Figure()
            fig_cf.add_trace(go.Bar(x=df_proj["Year"], y=df_proj[f"FCFF ({currency}M)"], name="Nominal FCFF", marker_color="#94A3B8"))
            fig_cf.add_trace(go.Bar(x=df_proj["Year"], y=df_proj[f"PV of FCFF ({currency}M)"], name="Present Value (PV)", marker_color="#2563EB"))
            fig_cf.update_layout(barmode="group", height=300, margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_cf, use_container_width=True)

        with ch2:
            st.markdown("##### 🌉 Enterprise Value to Equity Value Bridge")
            bridge_labels = ["PV FCFF", "PV Terminal", "Cash (+)", "Non-Op (+)", "Debt (-)", "Equity Value"]
            bridge_values = [base_res["pv_explicit"], base_res["pv_terminal"], cash_equivalents, non_op_assets, -total_debt, base_res["equity_value"]]
            fig_bridge = go.Figure(go.Waterfall(
                orientation="v",
                measure=["relative", "relative", "relative", "relative", "relative", "total"],
                x=bridge_labels,
                textposition="outside",
                text=[f"{v:.0f}" for v in bridge_values],
                y=bridge_values,
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                decreasing={"marker": {"color": "#EF4444"}},
                increasing={"marker": {"color": "#10B981"}},
                totals={"marker": {"color": "#3B82F6"}}
            ))
            fig_bridge.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_bridge, use_container_width=True)

        st.markdown("---")

        # 4. Sensitivity Matrix
        st.markdown("#### 🧪 Sensitivity Analysis: WACC vs Perpetual Growth Rate (g)")
        wacc_range = [calculated_wacc - 1.0, calculated_wacc - 0.5, calculated_wacc, calculated_wacc + 0.5, calculated_wacc + 1.0]
        g_range = [perpetual_growth - 1.0, perpetual_growth - 0.5, perpetual_growth, perpetual_growth + 0.5, perpetual_growth + 1.0]

        sens_matrix = []
        for w in wacc_range:
            row = []
            for g in g_range:
                res = compute_dcf(wacc_val=w)
                if w > g:
                    term_fcff = res["fcffs"][-1] * (1 + g / 100.0)
                    tv = term_fcff / ((w / 100.0) - (g / 100.0))
                    pv_tv = tv / ((1 + w / 100.0) ** forecast_years)
                    ev = res["pv_explicit"] + pv_tv
                    eq = ev + cash_equivalents + non_op_assets - total_debt - preferred_stock - non_controlling
                    val_per_share = eq / shares_outstanding if shares_outstanding > 0 else 0.0
                else:
                    val_per_share = 0.0
                row.append(round(val_per_share, 2))
            sens_matrix.append(row)

        sens_df = pd.DataFrame(sens_matrix, index=[f"WACC {w:.2f}%" for w in wacc_range], columns=[f"g {g:.1f}%" for g in g_range])
        try:
            st.dataframe(sens_df.style.background_gradient(cmap="RdYlGn"), use_container_width=True)
        except Exception:
            st.dataframe(sens_df, use_container_width=True)

        st.markdown("---")

        # 5. EXPORT SECTION (EXCEL & PDF)
        st.markdown("### 📤 Download Export Reports (Excel & PDF)")

        exp_col1, exp_col2, exp_col3 = st.columns(3)

        valuation_summary_df = pd.DataFrame({
            "Metric": [
                "Company Name", "Current Market Price", "Weighted Intrinsic Value", "Base Case Intrinsic Value",
                "Bull Case Intrinsic Value", "Bear Case Intrinsic Value", "Implied Upside/Downside (%)",
                "WACC (%)", "Cost of Equity (%)", "Cost of Debt After Tax (%)",
                "Enterprise Value (Base)", "Equity Value (Base)", "Shares Outstanding (M)"
            ],
            "Value": [
                company_name, f"{currency}{current_price:.2f}", f"{currency}{weighted_val:.2f}", f"{currency}{base_res['intrinsic_value']:.2f}",
                f"{currency}{bull_res['intrinsic_value']:.2f}", f"{currency}{bear_res['intrinsic_value']:.2f}", f"{upside_pct:.2f}%",
                f"{calculated_wacc:.2f}%", f"{cost_of_equity:.2f}%", f"{cost_of_debt_after_tax:.2f}%",
                f"{currency}{base_res['enterprise_value']:.2f}M", f"{currency}{base_res['equity_value']:.2f}M", f"{shares_outstanding}M"
            ]
        })

        with exp_col1:
            excel_bytes = export_to_excel(
                valuation_summary_df,
                base_res["projections"],
                {"WACC": calculated_wacc, "Cost of Equity": cost_of_equity, "Cost of Debt After Tax": cost_of_debt_after_tax},
                sens_df
            )
            st.download_button(
                label="📊 Export Full Model in Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"{company_name.replace(' ', '_')}_DCF_Valuation.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with exp_col2:
            pdf_bytes = generate_pdf_report(
                company_name, currency, current_price, weighted_val, status_str, upside_pct,
                calculated_wacc, base_res['intrinsic_value'], bull_res['intrinsic_value'], bear_res['intrinsic_value'],
                base_res["projections"]
            )
            st.download_button(
                label="📄 Export Executive Report in PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"{company_name.replace(' ', '_')}_Valuation_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with exp_col3:
            json_report = {
                "company": company_name,
                "intrinsic_value": weighted_val,
                "current_price": current_price,
                "status": status_str,
                "wacc": calculated_wacc,
                "scenarios": {
                    "base": base_res['intrinsic_value'],
                    "bull": bull_res['intrinsic_value'],
                    "bear": bear_res['intrinsic_value']
                }
            }
            st.download_button(
                label="⚙️ Export Raw Data in JSON",
                data=json.dumps(json_report, indent=4),
                file_name=f"{company_name.replace(' ', '_')}_Valuation.json",
                mime="application/json",
                use_container_width=True
            )
