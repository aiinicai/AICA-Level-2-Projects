"""Day Book Audit: upload a Tally Day Book; get rule-based, narration and amount-shape findings, plus optional AI review."""
import hashlib
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from daybook_auditor import narration  # noqa: E402
from daybook_auditor.analytics import family as family_of  # noqa: E402
from daybook_auditor.catalog import catalog_frame  # noqa: E402
from daybook_auditor.ai_review import review_vouchers  # noqa: E402
from daybook_auditor.parser import load_daybook  # noqa: E402
from daybook_auditor.report import build_excel  # noqa: E402
from daybook_auditor.rules import FINDING_COLS, SEVERITY_RANK, Config, run_rules, summarise_vouchers  # noqa: E402
from ui import ai, charts, theme  # noqa: E402

ICON = {"High": "\U0001f534 High", "Medium": "\U0001f7e0 Medium", "Low": "\U0001f7e1 Low"}


family = family_of


@st.cache_data(show_spinner=False)
def _load(name: str, data: bytes):
    return load_daybook(name, data)


theme.header("Day Book Audit", "Upload a Tally Day Book. Rule tests run on this computer; the optional AI review is the "
             "only part that contacts Google.", "\U0001f4d2")

up = st.file_uploader("Day Book file", type=["xml", "xlsx", "csv"])
if up is None:
    st.info("In TallyPrime: Day Book, Alt+E (Export), format **XML** (or Excel) in the **Detailed** view. "
            "A fictional sample is in `samples/sample_daybook.xml`.")
    with st.expander("What the tests look for"):
        st.markdown("**Narration themes.** Words an auditor would want explained. A match is a lead, not a conclusion, "
                    "and \"no penalty levied\" is not flagged.")
        st.dataframe([{"Theme": t.label, "Severity": t.severity, "Why it matters": t.reference} for t in narration.THEMES],
                     hide_index=True, width="stretch")
        st.markdown("**The 999 test.** Amounts that end in 999, or sit just under a limit that triggers a rule:")
        st.dataframe([{"Limit": f"Rs {x:,.0f}", "What it triggers": why} for x, why in narration.THRESHOLDS],
                     hide_index=True, width="stretch")
        st.markdown("**Also:** the same amount to the same party three or more times in a month, and a Benford "
                    "first-digit screen over all amounts. Plus the accounting rules: cash limits, TDS and GST slips, "
                    "duplicates, voucher gaps, dates outside the year, suspense ledgers, negative cash.")
    st.stop()

data = up.getvalue()
key = hashlib.md5(data).hexdigest()[:10]
try:
    df, meta = _load(up.name, data)
except ValueError as e:
    st.error(str(e))
    st.stop()

dates = df["date"].dropna()
if dates.empty:      # every date hidden: fall back to the last financial year for the default period
    start_year = date.today().year - (1 if date.today().month >= 4 else 2)
else:
    start_year = dates.min().year if dates.min().month >= 4 else dates.min().year - 1

with st.sidebar:
    st.header("Settings")
    fy_start = st.date_input("Financial year start", date(start_year, 4, 1), format="DD/MM/YYYY", key=f"fys{key}")
    fy_end = st.date_input("Financial year end", date(start_year + 1, 3, 31), format="DD/MM/YYYY", key=f"fye{key}")
    opening_cash = st.number_input("Opening cash balance (Rs)", 0.0, step=1000.0,
                                   help="Needed for the negative-cash check when the Day Book starts mid-year.")
    cash_limit = st.number_input("Cash payment limit per party/day (Rs)", 10_000.0, step=1000.0)
    cash_rcpt = st.number_input("Cash receipt limit per party/day (Rs)", 200_000.0, step=10_000.0)
    round_min = st.number_input("Round-sum check from (Rs)", 100_000.0, step=10_000.0)
    narr_min = st.number_input("Narration required from (Rs)", 25_000.0, step=5_000.0)
    st.divider()
    st.subheader("Narration and amount tests")
    run_new = st.toggle("Run narration and amount-pattern tests", value=True)
    near_pct = st.slider("'Just under a limit' means within (%)", 0.5, 10.0, 2.0, 0.5,
                         help="A 2% window under Rs 10,000 is Rs 9,800 to Rs 9,999.")

cfg = Config(fy_start=fy_start, fy_end=fy_end, opening_cash=opening_cash, cash_payment_limit=cash_limit,
             cash_receipt_limit=cash_rcpt, round_sum_min=round_min, narration_min=narr_min,
             near_threshold_pct=near_pct, run_narration_tests=run_new)
vouchers = summarise_vouchers(df)
rule_f = run_rules(df, cfg, meta["ledger_level"])

if meta.get("undated"):
    st.warning(f"The date is hidden on {meta['undated']} of {meta['vouchers']} vouchers: the export shows "
               f"'{meta.get('date_label') or 'no date'}' instead of a date (TallyPrime Educational Mode does this for every "
               "date except the 1st, 2nd and 31st). Tests that need the date, such as per-day cash totals, cut-off, "
               "weekends and negative cash, are limited or skipped. Every other test ran on all vouchers, in file order.")
if not meta["ledger_level"]:
    st.warning("This file has one line per voucher, so cash, TDS, GST and Dr = Cr checks were skipped. The narration and "
               "amount-pattern tests still ran. Export the Day Book in detailed view (or as XML) to enable the rest.")
if meta.get("skipped"):
    st.caption(f"{meta['skipped']} cancelled/optional voucher(s) were excluded.")

ai_key = f"ai_{key}"
st.session_state.setdefault(ai_key, (pd.DataFrame(columns=FINDING_COLS), []))
st.session_state.setdefault(ai_key + "_n", 0)

findings = pd.concat([rule_f, st.session_state[ai_key][0]], ignore_index=True)
if len(findings):
    findings["family"] = [family(r, s) for r, s in zip(findings["rule"], findings["source"])]
    findings["_r"] = findings["severity"].map(SEVERITY_RANK)
    findings = findings.sort_values(["_r", "date"], kind="stable").drop(columns="_r").reset_index(drop=True)
else:
    findings["family"] = []

c = st.columns(5)
c[0].metric("Vouchers", f"{meta['vouchers']:,}")
c[1].metric("High", int((findings["severity"] == "High").sum()))
c[2].metric("Medium", int((findings["severity"] == "Medium").sum()))
c[3].metric("Low", int((findings["severity"] == "Low").sum()))
if meta.get("undated"):
    c[4].metric("Dates visible", f"{dates.min():%d/%m/%y} to {dates.max():%d/%m/%y}" if len(dates) else "none",
                help=f"{meta['undated']} of {meta['vouchers']} dates are hidden by the export, so the true period is wider than this.")
else:
    c[4].metric("Period", f"{dates.min():%d/%m/%Y} to {dates.max():%d/%m/%Y}" if len(dates) else "n/a")
n_ai = int((findings["source"] == "AI").sum()) if len(findings) else 0
st.caption(f"{len(rule_f)} finding(s) from the rule and narration tests"
           + (f" and {n_ai} from the AI review." if st.session_state[ai_key + "_n"] else ". The AI review has not been run (optional: see its tab)."))
st.download_button("⬇ Download Excel report (findings, AI analysis, vouchers)",
                   build_excel(findings, df, meta, st.session_state[ai_key + "_n"]),
                   file_name=f"daybook_review_{date.today():%Y%m%d}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

tab_b, tab_f, tab_t, tab_a, tab_d = st.tabs(["Overview", "Findings", "Tests run", "AI review of the vouchers", "Day Book data"])
with tab_b:
    charts.daybook(df, findings)
with tab_f:
    if findings.empty:
        st.success("No findings with the current settings.")
    else:
        f0, f1, f2, f3 = st.columns([1.2, 1.2, 1.6, 1.4])
        fam = f0.multiselect("Test family", sorted(findings["family"].unique()), default=sorted(findings["family"].unique()))
        sev = f1.multiselect("Severity", list(ICON), default=list(ICON))
        rules_sel = f2.multiselect("Check", sorted(findings["rule"].unique()))
        text = f3.text_input("Search (party, voucher no., text)")
        view = findings[findings["severity"].isin(sev) & findings["family"].isin(fam)]
        if rules_sel:
            view = view[view["rule"].isin(rules_sel)]
        if text:
            m = view.astype(str).apply(lambda col: col.str.contains(text, case=False, regex=False)).any(axis=1)
            view = view[m]
        shown = view.drop(columns=["voucher_id"]).assign(severity=view["severity"].map(ICON))
        st.dataframe(shown, hide_index=True, width="stretch", height=520, column_config={
            "date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "amount": st.column_config.NumberColumn("Amount (Rs)", format="%,.0f"),
            "detail": st.column_config.TextColumn("Observation", width="large"),
            "reference": st.column_config.TextColumn("Why it matters / reference", width="large"),
        })
        st.caption(f"{len(view)} of {len(findings)} findings shown. AI findings have the family 'AI review'.")
with tab_t:
    cat = catalog_frame(findings)
    ran = int((cat["Findings"] > 0).sum())
    t1, t2, t3 = st.columns(3)
    t1.metric("Tests run", len(cat)); t2.metric("Raised findings", ran); t3.metric("Ran, found nothing", len(cat) - ran)
    st.caption("Every test is listed, including those that found nothing, so you can see it ran. The 999 verification is in the first group.")
    fams = st.multiselect("Family", list(dict.fromkeys(cat["Family"])), default=list(dict.fromkeys(cat["Family"])))
    st.dataframe(cat[cat["Family"].isin(fams)], hide_index=True, width="stretch", height=520,
                 column_config={"What it checks": st.column_config.TextColumn(width="large")})
with tab_a:
    st.info("**This AI reviews the Day Book vouchers**: each narration read against the ledgers it was booked to. It does not look at "
            "the financial statements. The statements have their own AI review on the Financial Statements Builder page.")
    st.markdown("**What it adds.** The rules and narration tests find what can be written as a rule. The AI catches what cannot: personal "
                "spend booked as business expense, a wrong ledger or voucher type, an unusual counterparty, a vague narration on a material "
                "entry. Its findings are marked AI and are leads for the reviewer, not conclusions. For the vouchers you choose it sends "
                "ledger names, amounts and narrations to Google's Gemini API, only after you consent.")
    api_key, model, consent = ai.config()
    ai.badge()
    ai.consent_box("the ledger names, amounts and narrations of the vouchers you choose")
    which = st.radio("Which vouchers to send", ["Vouchers the rules flagged (recommended)", "Largest vouchers by value"], horizontal=True,
                     help="Flagged vouchers are where the risk is. The largest vouchers are often routine sales.")
    max_v = st.slider("Most vouchers to send", 20, 1000, 300, 20)
    if not ai.ready():
        st.caption("Add your key and give consent on the Settings & AI page to enable this.")
        theme.safe_link("ui/settings.py", "Open Settings & AI", ":material/tune:")
    if st.button("Run AI review", disabled=not ai.ready(), type="primary"):
        chosen = vouchers[vouchers["voucher_id"].isin(set(rule_f["voucher_id"]))] if which.startswith("Vouchers the rules") else vouchers
        if chosen.empty:
            st.session_state[ai_key + "_msg"] = "The rules flagged no vouchers, so there is nothing to send. Choose the largest vouchers instead."
        else:
            bar = st.progress(0.0, "Reviewing vouchers...")
            try:
                st.session_state[ai_key] = review_vouchers(chosen, api_key, model, max_v, progress=lambda p: bar.progress(p))
                st.session_state[ai_key + "_n"] = min(len(chosen), max_v)
                got = st.session_state[ai_key]
                failed = sum(e.startswith("Batch") for e in got[1])
                st.session_state[ai_key + "_msg"] = (
                    f"AI review finished: {st.session_state[ai_key + '_n']} voucher(s) sent, {len(got[0])} finding(s) returned"
                    + (f", {failed} batch(es) failed (see below): press Run AI review again to retry." if failed else "."))
            except Exception as e:
                st.session_state[ai_key + "_msg"] = f"AI review failed: {e}"
            bar.empty()
        st.rerun()                                   # so the counts, findings and the Excel report include the AI's work
    failed_now = any(e.startswith("Batch") for e in st.session_state[ai_key][1])
    if st.session_state.get(ai_key + "_msg"):
        (st.warning if failed_now or "failed" in st.session_state[ai_key + "_msg"] or "nothing to send" in st.session_state[ai_key + "_msg"]
         else st.success)(st.session_state[ai_key + "_msg"])
    for e in st.session_state[ai_key][1]:
        st.warning(e)

    ai_f = findings[findings["source"] == "AI"] if len(findings) else findings
    n_sent = st.session_state[ai_key + "_n"]
    if not n_sent:
        st.caption("The AI review has not been run for this file. Nothing is sent until you press Run AI review.")
    else:
        rule_ids = set(rule_f["voucher_id"])
        also = int(ai_f["voucher_id"].isin(rule_ids).sum()) if len(ai_f) else 0
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Vouchers sent", n_sent); a2.metric("AI findings", len(ai_f))
        a3.metric("Also flagged by rules", also, help="The AI agrees with a rule on the same voucher")
        a4.metric("Only the AI raised", len(ai_f) - also, help="Vouchers the rules did not flag")
        if len(ai_f):
            view = ai_f.assign(**{"Also flagged by rules": ai_f["voucher_id"].isin(rule_ids).map({True: "Yes", False: "No: new"}),
                                  "severity": ai_f["severity"].map(ICON)})
            st.dataframe(view[["severity", "rule", "vch_no", "amount", "detail", "reference", "Also flagged by rules"]].rename(
                columns={"severity": "Severity", "rule": "Category", "vch_no": "Voucher", "amount": "Amount (Rs)",
                         "detail": "Observation", "reference": "Suggestion"}),
                hide_index=True, width="stretch", height=420, column_config={
                    "Amount (Rs)": st.column_config.NumberColumn(format="%,.0f"),
                    "Observation": st.column_config.TextColumn(width="large"), "Suggestion": st.column_config.TextColumn(width="large")})
        else:
            st.success("The AI found nothing to add on the vouchers it was sent.")
with tab_d:
    st.dataframe(df, hide_index=True, width="stretch", height=520)
