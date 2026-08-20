"""
Salary TDS Calculator & Advisor
AICA Level 2 Capstone — built with Streamlit + Claude API

Solves a real, recurring problem: employees repeatedly asking their finance
team each month "how is my TDS calculated?" This app lets them self-serve —
compute their own salary TDS under both tax regimes, see a clear dashboard,
get an AI-generated plain-language explanation grounded in their own numbers,
and separately ask general, educational tax questions — all citing the
correct Income Tax Act, 2025 section numbers.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.tax_engine import SalaryInput, compute_old_regime, compute_new_regime
from utils.ai_assistant import explain_tds, answer_tax_faq
from utils.audio_helper import transcribe_audio, speak_text_button

try:
    from streamlit_mic_recorder import mic_recorder
except ImportError:
    mic_recorder = None

st.set_page_config(
    page_title="Salary TDS Calculator & Advisor",
    page_icon="💼",
    layout="wide",
)

# ---------- Minimal custom styling for a "presentable" dashboard feel ----------
st.markdown("""
<style>
.metric-card {
    background: #f7f9fc;
    border: 1px solid #e3e8ef;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.metric-card h2 { margin: 0; font-size: 1.8rem; }
.metric-card p { margin: 0; color: #667085; font-size: 0.9rem; }
.verdict-box {
    background: #eefaf0;
    border-left: 5px solid #12b76a;
    padding: 16px 20px;
    border-radius: 8px;
    font-size: 1.05rem;
}
.faq-disclaimer {
    background: #fff8e6;
    border-left: 5px solid #f79009;
    padding: 14px 18px;
    border-radius: 8px;
    font-size: 0.92rem;
    margin-bottom: 16px;
}
.app-footer {
    text-align: center;
    color: #667085;
    font-size: 0.85rem;
    padding: 18px 0 6px 0;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------- Screen 1: Header ----------------------------
st.title("💼 Salary TDS Calculator & Advisor")
st.caption(
    "Know exactly how your monthly TDS is calculated — under both the Old Regime "
    "and the default New Regime (Section 202) of the Income Tax Act, 2025."
)

# ---------------------------- Sidebar: Screens 2-4 (Inputs) ----------------------------
with st.sidebar:
    st.header("👤 Your Details")
    name = st.text_input("Name (optional)")
    age_band = st.selectbox("Age", ["Below 60", "60-80", "Above 80"])

    st.header("💰 Salary Details")
    basic_salary = st.number_input("Basic Salary (annual, ₹)", min_value=0.0, value=600000.0, step=10000.0)
    hra_received = st.number_input("HRA Received (annual, ₹)", min_value=0.0, value=240000.0, step=5000.0)
    special_allowance = st.number_input("Special Allowance / Other Allowances (annual, ₹)", min_value=0.0, value=300000.0, step=5000.0)
    bonus = st.number_input("Bonus (annual, ₹)", min_value=0.0, value=60000.0, step=5000.0)
    other_income = st.number_input("Other Income — interest, rent, etc. (₹)", min_value=0.0, value=0.0, step=5000.0)

    st.header("🏠 Rent & HRA (Old Regime only)")
    rent_paid = st.number_input("Annual Rent Paid (₹)", min_value=0.0, value=180000.0, step=5000.0)
    city = st.selectbox("City", ["Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru",
                                  "Hyderabad", "Pune", "Ahmedabad", "Other (Non-Metro)"])

    st.header("📊 Investments & Deductions (Old Regime only)")
    invest_123 = st.number_input("Sec 123 (erstwhile 80C) — PPF/ELSS/LIC/tuition/etc. (₹, cap 1.5L)", min_value=0.0, value=100000.0, step=5000.0)
    nps_124 = st.number_input("Sec 124 (erstwhile 80CCD(1B)) — NPS additional (₹, cap 50K)", min_value=0.0, value=0.0, step=5000.0)
    health_126 = st.number_input("Sec 126 (erstwhile 80D) — Health Insurance Premium (₹)", min_value=0.0, value=15000.0, step=1000.0)
    home_loan_22 = st.number_input("Sec 22(2) (erstwhile 24(b)) — Home Loan Interest (₹, cap 2L)", min_value=0.0, value=0.0, step=5000.0)

    calculate = st.button("🔎 Calculate My TDS", type="primary", use_container_width=True)

# ---------------------------- Compute ----------------------------
inp = SalaryInput(
    name=name, age_band=age_band,
    basic_salary=basic_salary, hra_received=hra_received,
    special_allowance=special_allowance, bonus=bonus, other_income=other_income,
    rent_paid=rent_paid, city=city,
    invest_123=invest_123, nps_124=nps_124, health_126=health_126,
    home_loan_interest_22=home_loan_22,
)

old_result = compute_old_regime(inp)
new_result = compute_new_regime(inp)
better = "New Regime" if new_result.total_tax <= old_result.total_tax else "Old Regime"
savings = abs(new_result.total_tax - old_result.total_tax)

# ---------------------------- Tabs ----------------------------
tab_calc, tab_faq = st.tabs(["🧮 TDS Calculator", "📚 Tax FAQ (Educational)"])

# ============================================================
# TAB 1 — TDS Calculator (Screens 5-7)
# ============================================================
with tab_calc:
    st.markdown("## 📊 Regime Comparison Dashboard")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><p>Old Regime — Annual Tax</p>
                     <h2>₹{old_result.total_tax:,.0f}</h2>
                     <p>Monthly TDS (Sec 392): ₹{old_result.monthly_tds:,.0f}</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><p>New Regime — Annual Tax (Sec 202)</p>
                     <h2>₹{new_result.total_tax:,.0f}</h2>
                     <p>Monthly TDS (Sec 392): ₹{new_result.monthly_tds:,.0f}</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><p>Better Option</p>
                     <h2>{better}</h2>
                     <p>Saves ₹{savings:,.0f} / year</p></div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="verdict-box">
    ✅ Based on your inputs, the <b>{better}</b> works out cheaper by
    <b>₹{savings:,.0f} per year</b> (≈ ₹{savings/12:,.0f}/month).
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### Tax Comparison")
        fig_bar = go.Figure(data=[
            go.Bar(name="Annual Tax", x=["Old Regime", "New Regime (Sec 202)"],
                   y=[old_result.total_tax, new_result.total_tax],
                   marker_color=["#f79009", "#12b76a"])
        ])
        fig_bar.update_layout(height=350, showlegend=False, yaxis_title="₹")
        st.plotly_chart(fig_bar, use_container_width=True)

    with chart_col2:
        st.markdown("#### Salary Breakup")
        breakup_df = pd.DataFrame(
            {"Component": list(old_result.breakup.keys()), "Amount": list(old_result.breakup.values())}
        )
        fig_pie = px.pie(breakup_df, names="Component", values="Amount", hole=0.45)
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("📄 See full computation detail (old vs new regime)"):
        detail_df = pd.DataFrame({
            "Item": ["Gross Salary", "HRA Exemption (Sec 11/19/Sch. II)", "Standard Deduction (Sec 19)",
                     "Chapter VI-A equiv. + Sec 22(2)", "Taxable Income", "Tax before Rebate",
                     "Rebate (Sec 156)", "Cess (4%)", "Total Tax"],
            "Old Regime": [old_result.gross_salary, old_result.exemptions, old_result.standard_deduction,
                           old_result.chapter_via_deductions, old_result.taxable_income,
                           old_result.tax_before_cess, old_result.rebate, old_result.cess, old_result.total_tax],
            "New Regime": [new_result.gross_salary, new_result.exemptions, new_result.standard_deduction,
                           new_result.chapter_via_deductions, new_result.taxable_income,
                           new_result.tax_before_cess, new_result.rebate, new_result.cess, new_result.total_tax],
        })
        st.dataframe(detail_df.style.format({"Old Regime": "₹{:,.0f}", "New Regime": "₹{:,.0f}"}),
                     use_container_width=True, hide_index=True)

    # ---------------------------- Screen 6: AI Insights ----------------------------
    st.markdown("## 🤖 Ask the AI About Your TDS")
    st.caption("Powered by Claude — answers are grounded strictly in the numbers computed above.")

    if "ai_explanation" not in st.session_state:
        st.session_state.ai_explanation = None

    col_a, col_b = st.columns([3, 1])
    with col_a:
        user_question = st.text_input("Ask a question (or leave blank for a general explanation)",
                                       placeholder="e.g. Why is my TDS higher this month?")
    with col_b:
        st.write("")
        st.write("")
        ask = st.button("Ask AI", use_container_width=True)

    if mic_recorder is not None:
        st.caption("🎤 Or ask by voice:")
        voice_input = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop",
                                    key="tds_voice", format="wav")
        if voice_input and voice_input.get("bytes"):
            with st.spinner("Transcribing your question..."):
                transcribed = transcribe_audio(voice_input["bytes"])
            if transcribed:
                st.info(f"Heard: \"{transcribed}\"")
                user_question = transcribed
                ask = True
            else:
                st.warning("Couldn't quite catch that — please try again or type your question.")

    if ask:
        with st.spinner("Thinking..."):
            st.session_state.ai_explanation = explain_tds(inp, old_result, new_result, user_question or None)

    if st.session_state.ai_explanation:
        st.info(st.session_state.ai_explanation)
        speak_text_button(st.session_state.ai_explanation, key="tds_answer")

    # ---------------------------- Screen 7: Download Report ----------------------------
    st.markdown("## 📥 Download Your Report")
    report_df = pd.DataFrame({
        "Field": ["Name", "Age Band", "Gross Salary", "Old Regime Tax", "New Regime Tax",
                  "Better Option", "Annual Savings", "Old Regime Monthly TDS (Sec 392)",
                  "New Regime Monthly TDS (Sec 392)"],
        "Value": [name or "Employee", age_band, old_result.gross_salary, old_result.total_tax,
                  new_result.total_tax, better, savings, old_result.monthly_tds, new_result.monthly_tds],
    })
    csv = report_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Report (CSV)", data=csv,
                        file_name=f"TDS_Report_{name or 'employee'}.csv", mime="text/csv")

# ============================================================
# TAB 2 — Tax FAQ (Educational only, no liability computation)
# ============================================================
with tab_faq:
    st.markdown("## 📚 General Tax FAQ")
    st.markdown("""
    <div class="faq-disclaimer">
    ⚠️ <b>Educational information only.</b> This panel explains general income-tax
    concepts and provisions — it does <b>not</b> compute your personal tax liability
    (e.g. on capital gains) and does <b>not</b> prepare or file your return. Accurate,
    situation-specific advice requires reviewing your full facts with a qualified
    Chartered Accountant.
    </div>
    """, unsafe_allow_html=True)

    st.caption(
        "Ask about things like: how capital gains are taxed, which ITR form applies "
        "to you, filing deadlines, or what a section of the Income Tax Act, 2025 means."
    )

    if "faq_history" not in st.session_state:
        st.session_state.faq_history = []

    faq_question = st.text_input(
        "Ask a general tax question",
        placeholder="e.g. How is long-term capital gain on shares taxed?",
        key="faq_input",
    )
    faq_ask = st.button("Ask", key="faq_ask_button")

    if mic_recorder is not None:
        st.caption("🎤 Or ask by voice:")
        faq_voice_input = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop",
                                        key="faq_voice", format="wav")
        if faq_voice_input and faq_voice_input.get("bytes"):
            with st.spinner("Transcribing your question..."):
                faq_transcribed = transcribe_audio(faq_voice_input["bytes"])
            if faq_transcribed:
                st.info(f"Heard: \"{faq_transcribed}\"")
                faq_question = faq_transcribed
                faq_ask = True
            else:
                st.warning("Couldn't quite catch that — please try again or type your question.")

    if faq_ask and faq_question.strip():
        with st.spinner("Thinking..."):
            faq_answer = answer_tax_faq(faq_question.strip())
        st.session_state.faq_history.insert(0, (faq_question.strip(), faq_answer))

    for i, (q, a) in enumerate(st.session_state.faq_history):
        with st.expander(f"❓ {q}", expanded=(q == st.session_state.faq_history[0][0])):
            st.write(a)
            speak_text_button(a, key=f"faq_answer_{i}")

# ---------------------------- Footer ----------------------------
st.markdown("---")
st.caption(
    "Scope note: This version handles cash salary components — Basic, HRA, Special "
    "Allowance, and Bonus. Perquisites such as rent-free accommodation, company cars, "
    "and ESOPs are deliberately out of scope for this release, since Rule 15 of the "
    "Income Tax Rules, 2026 prescribes distinct valuation methods for each category. "
    "This is flagged as a planned enhancement for the next development phase, once "
    "each valuation method can be built and tested independently."
)
st.caption(
    "Built for AICA Level 2 capstone. Section references follow the Income Tax Act, 2025 "
    "(effective 1 Apr 2026, Tax Year 2026-27 onwards). For income earned up to 31 Mar 2026, "
    "the corresponding 1961 Act sections continue to apply. This tool is for illustration "
    "and self-service estimation only — not a substitute for professional tax advice."
)
st.caption(
    "Privacy: Your data is not stored — this calculator processes your figures only for "
    "this session and does not save any information."
)
st.markdown(
    '<div class="app-footer">Designed by CA Piyush Makkar — AICA Level 2, Batch 77</div>',
    unsafe_allow_html=True,
)
