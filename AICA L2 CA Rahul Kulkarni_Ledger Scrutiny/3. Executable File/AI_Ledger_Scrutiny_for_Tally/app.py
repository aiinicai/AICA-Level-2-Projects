"""
app.py  -  AI Ledger Scrutiny Assistant for Tally (Streamlit web app)
Run:  streamlit run app.py
"""

import copy
from datetime import date

import pandas as pd
import streamlit as st

from config import DEFAULT_CONFIG
from demo_data import make_demo
from report import build_excel
from scrutiny_engine import run_all
from tally_connector import TallyConnector, parse_xml_file

st.set_page_config(page_title="AI Ledger Scrutiny - Tally", page_icon="📒", layout="wide")
st.title("📒 AI Ledger Scrutiny Assistant")
st.caption("Pulls vouchers directly from Tally, applies audit & Income-tax rules, "
           "and uses AI (Isolation Forest + Benford's Law) to flag unusual entries.")

cfg = copy.deepcopy(DEFAULT_CONFIG)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("1. Data source")
    source = st.radio("Get data from", ["Tally (live)", "Upload Tally XML", "Demo data"], index=2)

    st.header("2. Audit period")
    today = date.today()
    fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    p_from = st.date_input("From", date(2025, 4, 1) if source == "Demo data" else fy_start)
    p_to = st.date_input("To", date(2026, 3, 31) if source == "Demo data" else today)

    company = ""
    if source == "Tally (live)":
        host = st.text_input("Tally host", cfg["tally_host"])
        port = st.number_input("Port", value=cfg["tally_port"], step=1)
        tc = TallyConnector(host, int(port))
        if st.button("🔌 Test connection"):
            if tc.is_alive():
                st.success("Tally is responding.")
                try:
                    st.session_state["companies"] = tc.companies()
                except Exception as ex:
                    st.warning(f"Connected, but could not list companies: {ex}")
            else:
                st.error("No response. Open Tally, open the company, enable port 9000 (see README).")
        comps = st.session_state.get("companies", [])
        company = st.selectbox("Company", comps) if comps else st.text_input("Company name (as in Tally)")
    elif source == "Upload Tally XML":
        st.caption("Tally: Day Book (period = full year) → Export → Format XML. "
                   "Optionally also export 'List of Accounts' (masters) as XML.")
        vch_file = st.file_uploader("Day Book / Vouchers XML", type=["xml"])
        mst_file = st.file_uploader("Masters XML (optional, improves accuracy)", type=["xml"])
        company = st.text_input("Company name (for report)", "")

    st.header("3. Thresholds")
    with st.expander("Change limits / materiality"):
        cfg["materiality_amount"] = st.number_input("Materiality (₹)", value=cfg["materiality_amount"], step=50000)
        cfg["cash_payment_limit_40A3"] = st.number_input("40A(3) cash limit (₹)", value=cfg["cash_payment_limit_40A3"])
        cfg["cash_receipt_limit_269ST"] = st.number_input("269ST limit (₹)", value=cfg["cash_receipt_limit_269ST"])
        cfg["cash_loan_limit_269SS_T"] = st.number_input("269SS/T limit (₹)", value=cfg["cash_loan_limit_269SS_T"])
        cfg["round_sum_min"] = st.number_input("Round-sum check from (₹)", value=cfg["round_sum_min"])
        cfg["duplicate_window_days"] = st.slider("Duplicate window (days)", 0, 30, cfg["duplicate_window_days"])
        cfg["outlier_zscore"] = st.slider("Outlier sensitivity (SD)", 2.0, 5.0, cfg["outlier_zscore"], 0.5)
        cfg["ai_contamination"] = st.slider("AI: expected % anomalies", 0.005, 0.10, cfg["ai_contamination"], 0.005)
        hol = st.text_area("Holidays (YYYY-MM-DD, one per line)", "")
        cfg["holidays"] = [h.strip() for h in hol.splitlines() if h.strip()]

    run = st.button("▶️ Run Ledger Scrutiny", type="primary", use_container_width=True)

# ---------------------------------------------------------------- load + run
if run:
    try:
        with st.spinner("Fetching data..."):
            if source == "Tally (live)":
                groups, ledgers, entries = tc.fetch_all(company or None, p_from, p_to)
            elif source == "Upload Tally XML":
                if not vch_file:
                    st.error("Please upload the Day Book XML.")
                    st.stop()
                groups, ledgers, entries = parse_xml_file(vch_file.getvalue())
                if mst_file:
                    g2, l2, _ = parse_xml_file(mst_file.getvalue())
                    groups, ledgers = g2, l2
            else:
                groups, ledgers, entries = make_demo()
                company = "Demo Industries Pvt Ltd"
        if entries.empty:
            st.error("No vouchers found for this period / company.")
            st.stop()
        with st.spinner("Running audit rules and AI model..."):
            exc, summary, extras = run_all(groups, ledgers, entries, cfg, p_from, p_to)
        st.session_state["result"] = (exc, summary, extras, company, f"{p_from:%d-%b-%Y} to {p_to:%d-%b-%Y}")
    except Exception as ex:
        st.error(f"Error: {ex}")
        st.stop()

if "result" not in st.session_state:
    st.info("👈 Choose a data source and click **Run Ledger Scrutiny**. Try **Demo data** first.")
    st.stop()

exc, summary, extras, company, period = st.session_state["result"]
stats = extras["stats"]

# ---------------------------------------------------------------- dashboard
st.subheader(f"{company or 'Company'}  |  {period}")
c = st.columns(6)
c[0].metric("Vouchers", f"{stats['vouchers']:,}")
c[1].metric("Ledger lines", f"{stats['lines']:,}")
c[2].metric("Exceptions", f"{len(exc):,}")
c[3].metric("🔴 High", int((exc["severity"] == "High").sum()))
c[4].metric("🟠 Medium", int((exc["severity"] == "Medium").sum()))
c[5].metric("Dr = Cr?", "✅ Yes" if abs(stats["total_dr"] - stats["total_cr"]) < 1 else "❌ No")

xlsx = build_excel(exc, summary, extras, company, period)
d1, d2 = st.columns(2)
d1.download_button("⬇️ Download audit working paper (Excel)", xlsx,
                   file_name=f"Ledger_Scrutiny_{(company or 'Company').replace(' ', '_')}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                   use_container_width=True)
d2.download_button("⬇️ Download exceptions (CSV)", exc.to_csv(index=False).encode("utf-8-sig"),
                   file_name="exceptions.csv", mime="text/csv", use_container_width=True)

tabs = st.tabs(["📋 Summary", "🚩 Exceptions", "🤖 AI anomalies", "📊 Benford's Law",
                "💵 Cash book", "🔎 Ledger viewer"])

with tabs[0]:
    st.dataframe(summary, use_container_width=True, hide_index=True,
                 column_config={"amount": st.column_config.NumberColumn("Amount (₹)", format="%.0f")})

with tabs[1]:
    f1, f2, f3 = st.columns([1, 2, 2])
    sev = f1.multiselect("Severity", ["High", "Medium", "Low", "Info"], ["High", "Medium"])
    rules = f2.multiselect("Rule", sorted(exc["rule"].unique()))
    q = f3.text_input("Search ledger / party / remark")
    view = exc[exc["severity"].isin(sev)] if sev else exc
    if rules:
        view = view[view["rule"].isin(rules)]
    if q:
        m = view[["ledger", "party", "remark"]].astype(str).apply(lambda s: s.str.contains(q, case=False))
        view = view[m.any(axis=1)]
    st.caption(f"{len(view)} item(s)")
    st.dataframe(view, use_container_width=True, hide_index=True, height=520)

with tabs[2]:
    st.write(extras["ai_message"])
    st.caption("The model learns the normal pattern of this company's entries (amount, ledger, "
               "day, narration, voucher type) and scores how unusual each entry is. "
               "Higher score = more unusual. Auditor judgement is still required.")
    st.dataframe(exc[exc["rule_id"] == "R17"], use_container_width=True, hide_index=True)

with tabs[3]:
    st.write(f"**{extras['benford_verdict']}** — MAD = {extras['benford_mad']:.4f} "
             f"on {extras['benford_n']:,} debit amounts (Nigrini thresholds: <0.006 close, "
             "<0.012 acceptable, <0.015 marginal).")
    st.bar_chart(extras["benford"].set_index("digit")[["actual_%", "expected_%"]])
    st.dataframe(extras["benford"], hide_index=True)

with tabs[4]:
    cb = extras["cash_balance"]
    if cb.empty:
        st.info("No cash ledger found.")
    else:
        pivot = cb.pivot_table(index="date", columns="ledger", values="closing")
        st.line_chart(pivot)
        neg = cb[cb["closing"] < 0]
        st.write(f"Days with negative cash balance: **{len(neg)}**")
        if len(neg):
            st.dataframe(neg, hide_index=True)

with tabs[5]:
    e = extras["entries"]
    led = st.selectbox("Ledger", sorted(e["ledger"].unique()))
    le = e[e["ledger"] == led].sort_values("date").copy()
    le["Debit"] = le["amount"].where(le["dr_cr"] == "Dr", 0)
    le["Credit"] = le["amount"].where(le["dr_cr"] == "Cr", 0)
    le["Running (Dr+)"] = (le["Debit"] - le["Credit"]).cumsum()
    st.dataframe(le[["date", "voucher_type", "voucher_no", "narration", "Debit", "Credit", "Running (Dr+)"]],
                 use_container_width=True, hide_index=True)
    flagged = exc[exc["ledger"] == led]
    if len(flagged):
        st.warning(f"{len(flagged)} exception(s) on this ledger")
        st.dataframe(flagged, hide_index=True, use_container_width=True)
