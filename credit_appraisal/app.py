"""
app.py - Streamlit dashboard for corporate credit appraisal (₹10-50 Cr facilities).

Run:   streamlit run app.py

Layout
------
Sidebar : data source (sample / upload), proposal what-if inputs, editable policy guardrails
Header  : executive summary card (applicant, amount, grade, recommendation badge)
Tabs    : 1 Financial overview & trends   2 Ratio analysis (RAG)   3 Debt & exposure   4 Appraisal memo
"""
from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import streamlit as st

from appraisal import charts
from appraisal.config import (COLORS, GRADE_COLORS, PolicyLimits, fmt_value, rag_status, ratio_meta_for)
from appraisal.exposure import (compute_pro_forma, exposure_profile, repayment_schedule, stress_table)
from appraisal.ingestion import ApplicantData, DataValidationError, load_from_files
from appraisal.memo import build_recommendation, render_memo_markdown
from appraisal.ratios import compute_ratios
from appraisal.sample_data import build_excel_template, generate_sample, list_sample_profiles
from appraisal.scoring import build_scorecard, run_policy_checks

st.set_page_config(page_title="Corporate Credit Appraisal", page_icon="🏦", layout="wide")


def _stretch_kwargs(fn) -> dict:
    """Full-width kwargs that work on both older Streamlit (use_container_width) and newer (width='stretch')."""
    try:
        p = inspect.signature(fn).parameters.get("width")
        if p is not None and p.default == "stretch":
            return {}                       # newer Streamlit already stretches by default
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


STRETCH_DF = _stretch_kwargs(st.dataframe)
STRETCH_CH = _stretch_kwargs(st.plotly_chart)

RAG_BG = {"green": COLORS["green_bg"], "amber": COLORS["amber_bg"], "red": COLORS["red_bg"], "na": ""}
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

st.markdown(
    """
<style>
.block-container {padding-top: 2.2rem;}
.chip {display:inline-block; padding:.28rem .8rem; border-radius:999px; font-weight:650; color:#fff; font-size:.95rem;}
.decision {border-left:6px solid var(--c); padding:.85rem 1.2rem; border-radius:4px; background:rgba(128,128,128,.09);}
.decision .label {font-size:1.4rem; font-weight:650; color:var(--c); margin-bottom:.25rem;}
.small {color:rgba(128,128,128,1); font-size:.85rem;}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Sidebar: data source, what-if proposal, policy
# --------------------------------------------------------------------------- #
def sidebar_inputs() -> tuple[ApplicantData, PolicyLimits]:
    sb = st.sidebar
    sb.header("Applicant data")
    source = sb.radio("Source", ["Sample applicant", "Upload Excel / CSV"], label_visibility="collapsed")

    if source == "Sample applicant":
        choice = sb.selectbox("Sample profile", list_sample_profiles())
        data = generate_sample(choice)
        sb.download_button("Download this sample as Excel template", build_excel_template(data),
                           file_name="applicant_input_template.xlsx", mime=XLSX_MIME)
    else:
        files = sb.file_uploader("One .xlsx workbook, or the six CSVs", type=["xlsx", "xls", "csv"],
                                 accept_multiple_files=True)
        sb.caption("CSV file names must contain: applicant, proposed, balance, pnl, cash, debt.")
        sb.download_button("Download blank-format template (sample filled)",
                           build_excel_template(generate_sample(list_sample_profiles()[0])),
                           file_name="applicant_input_template.xlsx", mime=XLSX_MIME)
        if not files:
            st.info("Upload the applicant workbook in the sidebar, or switch to a sample applicant to explore the tool.")
            st.stop()
        try:
            data = load_from_files({f.name: f.getvalue() for f in files})
        except DataValidationError as e:
            st.error("The uploaded data could not be used:")
            for msg in e.errors:
                st.markdown(f"- {msg}")
            st.stop()

    # ---- proposal what-if -------------------------------------------------------------------
    sb.divider()
    sb.header("Proposed facility")
    k = data.profile["name"]
    prop = dict(data.proposed)
    prop["amount"] = sb.number_input("Amount (₹ Cr)", 1.0, 200.0, float(prop["amount"]), 1.0, key=f"amt_{k}")
    prop["tenure_years"] = sb.number_input("Tenure (years)", 1.0, 15.0, float(prop["tenure_years"]), 0.5, key=f"ten_{k}")
    prop["rate_pct"] = sb.number_input("Interest rate (% p.a.)", 5.0, 25.0, float(prop["rate_pct"]), 0.25, key=f"rate_{k}")
    prop["moratorium_months"] = sb.number_input("Moratorium (months)", 0.0, 36.0, float(prop["moratorium_months"]), 3.0,
                                                key=f"mor_{k}")
    prop["collateral_value"] = sb.number_input("Collateral value (₹ Cr)", 0.0, 500.0, float(prop["collateral_value"]), 1.0,
                                               key=f"col_{k}")
    prop["refinance_amount"] = sb.number_input("Of which refinances existing debt (₹ Cr)", 0.0, float(prop["amount"]),
                                               min(float(prop["refinance_amount"]), float(prop["amount"])), 1.0,
                                               key=f"refi_{k}")
    data.proposed = prop

    # ---- credit bureau score (what-if / manual entry) -----------------------------------------
    sb.divider()
    sb.header("Credit bureau score")
    cur = data.profile.get("bureau_score")
    cur = 0.0 if cur is None or pd.isna(cur) else float(cur)
    entered = sb.number_input("Score (300-900, 0 = not available)", 0.0, 900.0, cur, 1.0, key=f"bur_{k}")
    data.profile["bureau_score"] = np.nan if entered < 300 else entered

    # ---- policy guardrails --------------------------------------------------------------------
    with sb.expander("Policy guardrails (editable)"):
        d = PolicyLimits()
        limits = PolicyLimits(
            min_dscr=st.number_input("Min DSCR (x)", 0.5, 3.0, d.min_dscr, 0.05),
            max_de=st.number_input("Max Debt / TNW (x)", 0.5, 8.0, d.max_de, 0.25),
            min_icr=st.number_input("Min ICR (x)", 0.5, 6.0, d.min_icr, 0.25),
            max_debt_ebitda=st.number_input("Max Debt / EBITDA (x)", 1.0, 10.0, d.max_debt_ebitda, 0.25),
            min_security_cover=st.number_input("Min security cover (x)", 1.0, 3.0, d.min_security_cover, 0.05),
            min_bureau_score=st.number_input("Min credit bureau score", 300.0, 900.0, d.min_bureau_score, 10.0),
        )
    return data, limits


# --------------------------------------------------------------------------- #
# Small presentation helpers
# --------------------------------------------------------------------------- #
def chip(text: str, color: str) -> str:
    return f'<span class="chip" style="background:{color}">{text}</span>'


def trend_text(vals: pd.Series, meta: dict) -> str:
    a, b = vals.iloc[0], vals.iloc[-1]
    if not (np.isfinite(a) and np.isfinite(b)):
        return "n.m."
    d = b - a
    if abs(d) < 1e-9:
        return "-"
    arrow = "▲" if d > 0 else "▼"
    good = (d > 0) == meta["hb"]
    mark = "improving" if good else "weakening"
    unit = meta["unit"]
    txt = f"{d * 100:+.1f} pp" if unit == "pct" else f"{d:+.2f}x" if unit == "x" else f"{d:+.0f} d"
    return f"{arrow} {txt} ({mark})"


def ratio_table(bundle, limits):
    """Formatted ratio grid + parallel grid of background colours (RAG) for pandas Styler."""
    meta_all = ratio_meta_for(limits)
    years = bundle.years
    rows, colors = [], []
    for key, m in meta_all.items():
        s = bundle.ratios[key]
        op_g, op_b = ("≥", "<") if m["hb"] else ("≤", ">")
        row = {"Category": m["cat"], "Ratio": m["label"]}
        col = {"Category": "", "Ratio": ""}
        for y in years:
            row[y] = fmt_value(s[y], m["unit"])
            col[y] = RAG_BG[rag_status(s[y], m)]
        row["3-yr movement"] = trend_text(s, m)
        row["Green / Red rule"] = (f"{op_g} {fmt_value(m['good'], m['unit'])} / "
                                   f"{op_b} {fmt_value(m['bad'], m['unit'])}")
        col["3-yr movement"] = ""
        col["Green / Red rule"] = ""
        rows.append(row)
        colors.append(col)
    df = pd.DataFrame(rows)
    cdf = pd.DataFrame(colors, columns=df.columns)
    return df.style.apply(lambda _: cdf.map(lambda c: f"background-color: {c}" if c else ""), axis=None)


def color_status(df: pd.DataFrame, col: str, ok_col_bool: pd.Series):
    """Style helper: colour the ``col`` column green/red from a boolean Series."""
    bg = pd.DataFrame("", index=df.index, columns=df.columns)
    bg[col] = np.where(ok_col_bool, f"background-color: {COLORS['green_bg']}", f"background-color: {COLORS['red_bg']}")
    return bg


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
st.title("Corporate credit appraisal")
st.caption("Automated financial evaluation for facilities of ₹10-50 Cr. All amounts in ₹ Crore.")

data, limits = sidebar_inputs()

try:
    bundle = compute_ratios(data)
    pf_now = compute_pro_forma(data, bundle, include_proposed=False)
    pf = compute_pro_forma(data, bundle, include_proposed=True)
    exposure = exposure_profile(data, bundle)
    stress = stress_table(data, bundle, limits)
    scorecard = build_scorecard(data, bundle, pf)
    policy_df = run_policy_checks(data, bundle, pf, limits)
    rec = build_recommendation(data, bundle, pf, exposure, stress, scorecard, policy_df, limits)
    memo_md = render_memo_markdown(data, bundle, pf, pf_now, exposure, stress, scorecard, policy_df, rec, limits)
except Exception as exc:  # surface calculation problems instead of a blank page
    st.error("The appraisal could not be computed from this data.")
    st.exception(exc)
    st.stop()

for w in data.warnings:
    st.warning(w)

fin, ratios = bundle.fin, bundle.ratios
prop, prof = data.proposed, data.profile

# ---- Executive summary card -------------------------------------------------------------------
with st.container(border=True):
    c0, c1, c2, c3, c4 = st.columns([3.2, 1.3, 1.5, 1.5, 2.6])
    c0.markdown(f"### {prof['name']}")
    c0.markdown(f"<span class='small'>{prof.get('industry') or ''} · CIN {prof.get('cin') or 'n.a.'} · "
                f"{data.vintage_years:.0f} years in operation · Promoter holding "
                f"{prof['promoter_holding_pct']:.1f}%</span>"
                if pd.notna(prof.get("promoter_holding_pct")) else f"<span class='small'>{prof.get('industry') or ''}</span>",
                unsafe_allow_html=True)
    c0.markdown(f"<span class='small'>Purpose: {prop['purpose']}</span>", unsafe_allow_html=True)
    c1.metric("Requested", f"₹{prop['amount']:,.1f} Cr")
    c1.caption(f"{prop['tenure_years']:g} yrs @ {prop['rate_pct']:.2f}%")
    c2.metric("Debt: now → post-loan", f"₹{pf['total_debt']:,.0f} Cr", f"+₹{pf['total_debt'] - pf_now['total_debt']:,.0f} Cr",
              delta_color="off")
    c2.caption(f"Currently ₹{pf_now['total_debt']:,.0f} Cr")
    c3.markdown("**Risk grade**")
    c3.markdown(chip(f"Grade {scorecard.grade}", GRADE_COLORS[scorecard.grade]), unsafe_allow_html=True)
    c3.caption(f"{scorecard.grade_label} · {scorecard.composite:.0f}/100 · Bureau {fmt_value(prof.get('bureau_score'), 'score')}")
    c4.markdown("**Recommendation**")
    c4.markdown(chip(rec.label, rec.color), unsafe_allow_html=True)
    nb = int(((policy_df["Severity"] == "Hard") & (~policy_df["Passed"])).sum())
    c4.caption(f"{nb} hard guardrail breach{'es' if nb != 1 else ''} · pro-forma DSCR {fmt_value(pf['dscr'], 'x')}")

tab1, tab2, tab3, tab4 = st.tabs(["Financial overview", "Ratio analysis", "Debt & exposure", "Appraisal memo"])

# =========================================================================== #
# TAB 1 - Financial overview & trend analysis
# =========================================================================== #
with tab1:
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    prev = fin.iloc[-2] if len(fin) > 1 else fin.iloc[-1]
    cur = fin.iloc[-1]
    k1.metric(f"Revenue {bundle.years[-1]}", f"₹{cur['revenue']:,.0f} Cr", f"{(cur['revenue'] / prev['revenue'] - 1) * 100:+.1f}% YoY")
    k2.metric("EBITDA", f"₹{cur['ebitda']:,.1f} Cr", f"{(ratios['ebitda_margin'].iloc[-1]) * 100:.1f}% margin", delta_color="off")
    k3.metric("PAT", f"₹{cur['pat']:,.1f} Cr", f"{(ratios['npm'].iloc[-1]) * 100:.1f}% margin", delta_color="off")
    k4.metric("Tangible net worth", f"₹{cur['tnw']:,.1f} Cr")
    k5.metric("Revenue CAGR", fmt_value(bundle.revenue_cagr, "pct"))
    bur = prof.get("bureau_score")
    k6.metric("Credit bureau score", fmt_value(bur, "score"),
              None if pd.isna(bur) else ("Meets policy" if bur >= limits.min_bureau_score else "Below policy"),
              delta_color="off" if pd.isna(bur) or bur >= limits.min_bureau_score else "inverse")

    a, b = st.columns(2)
    a.plotly_chart(charts.revenue_profit_chart(fin), **STRETCH_CH)
    b.plotly_chart(charts.margins_chart(ratios), **STRETCH_CH)
    a, b = st.columns(2)
    a.plotly_chart(charts.leverage_chart(ratios, limits, pf), **STRETCH_CH)
    b.plotly_chart(charts.coverage_chart(ratios, limits, pf), **STRETCH_CH)
    a, b = st.columns(2)
    a.plotly_chart(charts.returns_chart(ratios), **STRETCH_CH)
    b.plotly_chart(charts.working_capital_chart(ratios), **STRETCH_CH)
    st.plotly_chart(charts.cashflow_chart(fin), **STRETCH_CH)

    with st.expander("Derived financial statements (₹ Cr)"):
        labels = {"revenue": "Revenue", "ebitda": "EBITDA", "dep": "Depreciation", "ebit": "EBIT", "finance_cost": "Finance costs",
                  "pbt": "PBT", "tax": "Tax", "pat": "PAT", "net_worth": "Net worth", "tnw": "Tangible net worth",
                  "total_debt": "Total debt", "current_assets": "Current assets", "current_liabilities": "Current liabilities",
                  "total_assets": "Total assets", "cfo": "Operating cash flow", "capex": "Capex",
                  "principal_repaid": "Principal repaid", "fcf": "Free cash flow"}
        st.dataframe(fin[list(labels)].rename(columns=labels).T.style.format("{:,.1f}"), **STRETCH_DF)

# =========================================================================== #
# TAB 2 - Ratio analysis table
# =========================================================================== #
with tab2:
    st.markdown("Cells are coloured against risk thresholds: "
                f"<span style='background:{COLORS['green_bg']};padding:2px 8px;border-radius:4px'>comfortable</span> "
                f"<span style='background:{COLORS['amber_bg']};padding:2px 8px;border-radius:4px'>watch</span> "
                f"<span style='background:{COLORS['red_bg']};padding:2px 8px;border-radius:4px'>weak / breach</span>. "
                "Debt/TNW, Debt/EBITDA, ICR and DSCR red lines follow the policy guardrails in the sidebar.",
                unsafe_allow_html=True)
    st.dataframe(ratio_table(bundle, limits), **STRETCH_DF, hide_index=True, height=36 * 21 + 40)
    st.caption("ROE/ROCE/ROA use average balances. DSCR follows policy: (EBITDA - Capex - Tax) / (Principal repaid + Interest), "
               "using actual historical capex, so growth capex depresses it; the cash-accrual DSCR is shown for reference. "
               "Debt/TNW and Debt/EBITDA show 'n.m.' when the denominator is not positive.")

# =========================================================================== #
# TAB 3 - Debt & exposure
# =========================================================================== #
with tab3:
    e1, e2, e3, e4, e5 = st.columns(5)
    e1.metric("Existing debt (lender-wise)", f"₹{exposure['outstanding']:,.1f} Cr")
    e2.metric("Existing sanctioned limits", f"₹{exposure['sanctioned']:,.1f} Cr")
    e3.metric("Lenders", exposure["n_lenders"], f"Top lender {exposure['top_lender_share'] * 100:.0f}%", delta_color="off")
    e4.metric("Weighted avg cost", f"{exposure['wavg_rate']:.2f}%")
    e5.metric("CC/OD utilisation", fmt_value(exposure["cc_utilisation"], "pct"))

    st.subheader("Existing lenders and facilities")
    ed = data.existing_debt.copy()
    st.dataframe(ed.style.format({"Sanctioned Limit": "{:,.1f}", "Outstanding": "{:,.1f}", "Interest Rate (%)": "{:.2f}",
                                  "Annual Principal": "{:,.2f}", "Annual Interest": "{:,.2f}"}),
                 **STRETCH_DF, hide_index=True)
    if abs(exposure["recon_gap_pct"]) > 0.02:
        st.warning(f"Lender-wise outstanding differs from audited balance-sheet debt "
                   f"(₹{exposure['bs_debt']:,.1f} Cr) by {exposure['recon_gap_pct'] * 100:+.1f}%. Reconcile before sanction.")
    else:
        st.caption(f"Reconciles with audited balance-sheet debt of ₹{exposure['bs_debt']:,.1f} Cr "
                   f"({exposure['recon_gap_pct'] * 100:+.1f}%).")

    a, b = st.columns(2)
    a.plotly_chart(charts.lender_donut(exposure["by_lender"]), **STRETCH_CH)
    b.plotly_chart(charts.facility_bar(exposure["by_type"]), **STRETCH_CH)

    st.subheader("Pro-forma position after the proposed facility")
    spec = [("Total debt (₹ Cr)", "total_debt", "cr_plain", None, None), ("Debt / TNW", "de", "x", limits.max_de, "max"),
            ("Debt / EBITDA", "debt_ebitda", "x", limits.max_debt_ebitda, "max"),
            ("ICR", "icr", "x", limits.min_icr, "min"), ("DSCR", "dscr", "x", limits.min_dscr, "min")]
    rows, oks = [], []
    for label, k, unit, lim, kind in spec:
        f_ = (lambda v: f"{v:,.1f}") if unit == "cr_plain" else (lambda v: fmt_value(v, "x"))
        ok = True if lim is None else (pf[k] <= lim if kind == "max" else pf[k] >= lim)
        rows.append({"Metric": label, "Current": f_(pf_now[k]), "Pro-forma": f_(pf[k]),
                     "Policy limit": "-" if lim is None else f"{'≤' if kind == 'max' else '≥'} {lim:.2f}x",
                     "Status": "-" if lim is None else ("Within limit" if ok else "Breach")})
        oks.append(ok)
    pf_df = pd.DataFrame(rows)
    st.dataframe(pf_df.style.apply(lambda d: color_status(d, "Status", pd.Series(oks, index=d.index)), axis=None),
                 **STRETCH_DF, hide_index=True)
    st.caption(f"Basis: latest audited TNW ₹{pf['tnw']:,.1f} Cr and EBITDA ₹{pf['ebitda']:,.1f} Cr held constant; "
               f"maintenance capex proxy = depreciation (₹{pf['capex_basis']:,.1f} Cr); tax ₹{pf['tax']:,.1f} Cr; "
               f"debt service measured in the first full repayment year "
               f"(principal ₹{pf['principal']:,.1f} Cr + interest ₹{pf['interest']:,.1f} Cr).")

    st.plotly_chart(charts.pro_forma_chart(pf_now, pf, limits), **STRETCH_CH)

    x1, x2, x3 = st.columns(3)
    x1.metric("Proposed / TNW", fmt_value(pf["proposed_to_tnw"], "pct"))
    x2.metric("Proposed / Revenue", fmt_value(pf["proposed_to_revenue"], "pct"))
    x3.metric("Collateral cover", fmt_value(pf["security_cover"], "x"))

    a, b = st.columns([1.2, 1])
    a.plotly_chart(charts.repayment_chart(repayment_schedule(data)), **STRETCH_CH)
    with b:
        st.markdown("**Stress test (pro-forma)**")
        s = stress.copy()
        view = pd.DataFrame({"DSCR": s["DSCR"].map(lambda v: fmt_value(v, "x")), "ICR": s["ICR"].map(lambda v: fmt_value(v, "x")),
                             "Debt/EBITDA": s["Debt / EBITDA"].map(lambda v: fmt_value(v, "x")),
                             "Meets policy": np.where(s["DSCR >= policy"], "Yes", "No")}, index=s.index)
        st.dataframe(view.style.apply(lambda d: color_status(d, "Meets policy", s["DSCR >= policy"].values), axis=None),
                     **STRETCH_DF)
        st.caption("Rate shock is applied to the full pro-forma debt book (assumed floating).")

# =========================================================================== #
# TAB 4 - Appraisal memo & recommendation
# =========================================================================== #
with tab4:
    st.markdown(f"<div class='decision' style='--c:{rec.color}'><div class='label'>{rec.label}</div>{rec.headline}</div>",
                unsafe_allow_html=True)
    st.markdown("")
    for line in rec.rationale:
        st.markdown(f"- {line}")

    a, b = st.columns([1, 1.25])
    a.plotly_chart(charts.score_gauge(scorecard.composite, scorecard.grade), **STRETCH_CH)
    b.plotly_chart(charts.pillar_chart(scorecard.pillar_scores), **STRETCH_CH)

    st.subheader("Policy compliance")
    pol = pd.DataFrame({"Guardrail": policy_df["Check"], "Basis": policy_df["Basis"], "Rule": policy_df["Rule"],
                        "Actual": [fmt_value(v, u) for v, u in zip(policy_df["Actual"], policy_df["Unit"])],
                        "Severity": policy_df["Severity"],
                        "Result": np.where(policy_df["Passed"], "Pass", np.where(policy_df["Critical"], "CRITICAL BREACH", "Breach"))})
    st.dataframe(pol.style.apply(lambda d: color_status(d, "Result", policy_df["Passed"].values), axis=None),
                 **STRETCH_DF, hide_index=True)

    with st.expander("Scorecard detail - metric-level scores"):
        m = scorecard.metrics.copy()
        m["Value"] = [f"{v:,.2f}" if np.isfinite(v) else "n.m." for v in m["value"]]
        m["Score"] = m["score"].map(lambda v: f"{v:.0f}" if pd.notna(v) else "n.a.")
        m["Worst → Best"] = [f"{w:g} → {b:g}" for w, b in zip(m["worst"], m["best"])]
        m["Weight in pillar"] = m["weight"].map(lambda v: f"{v * 100:.0f}%")
        st.dataframe(m[["pillar", "metric", "Value", "Worst → Best", "Weight in pillar", "Score"]]
                     .rename(columns={"pillar": "Pillar", "metric": "Metric"}), **STRETCH_DF, hide_index=True)
        st.caption(f"Base score {scorecard.base_score:.1f}, trend adjustment {scorecard.trend_adjustment:+.0f}, "
                   f"composite {scorecard.composite:.1f}. Ratios in percent are held as fractions here (0.15 = 15%).")

    s_col, r_col = st.columns(2)
    with s_col:
        st.subheader("Key strengths")
        for item in rec.strengths or ["None identified."]:
            st.markdown(f"- {item}")
    with r_col:
        st.subheader("Key risks")
        for item in rec.risks or ["None identified."]:
            st.markdown(f"- {item}")

    if rec.decision != "DECLINE":
        st.subheader("Proposed covenants and structure")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Financial covenants**")
            for item in rec.financial_covenants:
                st.markdown(f"- {item}")
            st.markdown("**Conditions precedent**")
            for item in rec.conditions_precedent:
                st.markdown(f"- {item}")
        with c2:
            st.markdown("**Security, DSRA and drawing power**")
            for item in rec.structural_terms:
                st.markdown(f"- {item}")
        st.subheader("Monitoring triggers")
        for item in rec.monitoring:
            st.markdown(f"- {item}")

    st.divider()
    with st.expander("Full credit appraisal memo (Markdown)"):
        st.markdown(memo_md)
    st.download_button("Download memo (.md)", memo_md, file_name=f"credit_memo_{prof['name'].replace(' ', '_')}.md",
                       mime="text/markdown")
