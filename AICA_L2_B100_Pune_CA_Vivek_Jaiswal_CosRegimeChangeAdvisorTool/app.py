"""
app.py - RegimeWise dashboard.

Run:  streamlit run app.py
Colours and fonts: .streamlit/config.toml (theme) and the CSS block below.
"""
import html
import re

import altair as alt
import pandas as pd
import streamlit as st

import engine
import note

ACCENT = "#0F766E"      # teal - the recommended option
MUTED = "#CBD5E1"       # grey - every other option
AMBER = "#B45309"       # close calls

st.set_page_config(page_title="RegimeWise - Regime Switch Analyser", page_icon="⚖️", layout="wide")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"], .stMarkdown, .stDataFrame {{ font-family: 'Inter', sans-serif; }}
  .block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }}

  .rw-hero {{ background: linear-gradient(120deg, #0B3B4F 0%, {ACCENT} 100%); color: #fff;
             border-radius: 14px; padding: 26px 30px; margin-bottom: 18px; }}
  .rw-hero h1 {{ color: #fff; font-size: 2rem; font-weight: 700; margin: 0; padding: 0; letter-spacing: -0.02em; }}
  .rw-hero p {{ color: #D9F2EE; margin: 6px 0 0; font-size: 1rem; }}
  .rw-pill {{ display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.3);
             border-radius: 999px; padding: 2px 12px; font-size: .78rem; margin-top: 12px; color: #fff; }}

  div[data-testid="stMetric"] {{ background: #fff; border: 1px solid #E2E8F0; border-radius: 12px;
             padding: 16px 18px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }}
  div[data-testid="stMetricLabel"] p {{ color: #64748B; font-size: .82rem; font-weight: 500;
             text-transform: uppercase; letter-spacing: .04em; }}
  div[data-testid="stMetricValue"] {{ color: #0F172A; font-weight: 700; }}

  .rw-card {{ background: #fff; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 20px;
             margin-bottom: 16px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }}
  .rw-card h4 {{ margin: 0 0 10px; font-size: 1.05rem; color: #0F172A; }}
  .rw-badge {{ display: inline-block; background: #E6F4F1; color: {ACCENT}; font-weight: 600;
             border-radius: 6px; padding: 3px 10px; font-size: .88rem; }}
  .rw-badge.warn {{ background: #FEF3C7; color: {AMBER}; }}
  .rw-big {{ font-size: 1.6rem; font-weight: 700; color: #0F172A; margin: 12px 0 0; }}
  .rw-sub {{ color: #64748B; font-size: .85rem; margin: 2px 0 0; }}
  .rw-row {{ display: flex; justify-content: space-between; border-top: 1px solid #F1F5F9;
             padding-top: 10px; margin-top: 12px; font-size: .86rem; color: #475569; }}

  .rw-foot {{ color: #94A3B8; font-size: .8rem; border-top: 1px solid #E2E8F0; margin-top: 32px; padding-top: 12px; }}
  section[data-testid="stSidebar"] h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: .05em; color: #475569; }}
  button[data-baseweb="tab"] p {{ font-size: .95rem; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)


def cr(x) -> str:
    """Rupees to a crore string, e.g. 12,31,84,567 -> ₹12.32 cr."""
    return f"₹{x / 1e7:,.2f} cr"


def option_order(name: str) -> int:
    m = re.search(r"Y(\d+)", name)
    return int(m.group(1)) if m else 0      # "Stay normal" first, then Y1, Y2 ...


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("1 · Templates")
    st.caption("Download, fill in Excel, save as CSV. Keep the column names; company names must match in both files.")
    t_comp, t_proj = engine.templates()
    st.download_button("⬇ Companies template", t_comp.to_csv(index=False), "companies_template.csv",
                       mime="text/csv", use_container_width=True)
    st.download_button("⬇ Projections template", t_proj.to_csv(index=False), "projections_template.csv",
                       mime="text/csv", use_container_width=True)
    with st.expander("What goes in each column"):
        st.markdown(
            "**Companies** - one row per company\n"
            "- `entity`: anonymised name, e.g. Co A\n"
            "- `bf_business_loss`, `unabsorbed_depreciation`, `mat_credit_bf`: opening balances in ₹\n"
            "- `loss_not_allowed_concessional`: part of the losses that cannot be set off after opting for Section 200 (old 115BAA)\n\n"
            "**Projections** - one row per company per year\n"
            "- `year`: e.g. 2026-27\n"
            "- `turnover`: decides the 25% or 30% normal rate\n"
            "- `income_before_setoff`: taxable income before loss set-off (negative for a loss)\n"
            "- `book_profit`: for MAT\n"
            "- `dividend_received`, `dividend_distributed`: for the inter-corporate dividend deduction\n\n"
            "Leave a cell blank or 0 if it does not apply. Amounts in rupees.")

    st.header("2 · Upload")
    c_up = st.file_uploader("Companies CSV", type=["csv"])
    p_up = st.file_uploader("Projections CSV", type=["csv"])

    st.header("3 · Assumptions")
    discount = st.slider("Discount rate for present value (%)", 0, 20, 10)

# ---------------------------------------------------------------- data
raw_c = pd.read_csv(c_up if c_up else "data/companies.csv")
raw_p = pd.read_csv(p_up if p_up else "data/projections.csv")
missing = engine.missing_columns(raw_c.rename(columns=str.strip), raw_p.rename(columns=str.strip))
comp, proj = engine.prepare(raw_c, raw_p)
own_data = bool(c_up and p_up)

# ---------------------------------------------------------------- header
st.markdown(f"""
<div class="rw-hero">
  <h1>RegimeWise <span style="font-weight:500;opacity:.85">- Regime Switch Analyser: Old Vs New - Section 200 (old 115BAA)</span></h1>
  <p>Normal regime or the concessional regime under Section 200 (old 115BAA) - and the right year to switch - for every company in the group</p>
  <span class="rw-pill">{'Your data' if own_data else 'Invented sample data'} · discount rate {discount}%</span>
</div>""", unsafe_allow_html=True)

if not own_data:
    st.info("You are looking at invented sample data. Download the templates from the sidebar, "
            "fill them in, and upload both files to analyse your own group.", icon="ℹ️")
if missing:
    st.error("These columns are missing from your upload and are being read as zero: " + ", ".join(missing)
             + ". Start from the templates in the sidebar.", icon="⚠️")
unmatched = sorted(set(proj["entity"]) - set(comp["entity"]))
if unmatched:
    st.warning("Projections for companies not in the companies file are ignored: "
               + ", ".join(map(str, unmatched)), icon="⚠️")

tab_rec, tab_co, tab_note, tab_inputs = st.tabs(
    ["Recommendations", "Company deep-dive", "Advisory note", "Inputs & assumptions"])

# Inputs are edited in the last tab but needed first, so build that tab's editors before the analysis.
with tab_inputs:
    st.subheader("Edit inputs")
    st.caption("You can change any cell below; every tab updates at once. To keep your changes for next time, "
               "download the table and upload it again later.")
    st.markdown("**Companies** - opening position")
    comp = st.data_editor(comp, num_rows="dynamic", use_container_width=True, key="c")
    st.download_button("⬇ Download this table (CSV)", comp.to_csv(index=False), "companies.csv",
                       mime="text/csv", key="dl_c")
    st.markdown("**Projections** - one row per company per year")
    proj = st.data_editor(proj, num_rows="dynamic", use_container_width=True, key="p")
    st.download_button("⬇ Download this table (CSV)", proj.to_csv(index=False), "projections.csv",
                       mime="text/csv", key="dl_p")

    st.subheader("Rates in use")
    st.caption("Inputs, not law: verify against the Income-tax Act, 2025 and the current Finance Act. Edit in engine.py. Section 200 of the Income-tax Act, 2025 corresponds to section 115BAA of the Income-tax Act, 1961.")
    r = engine.RATES
    st.dataframe(pd.DataFrame([
        ("Normal rate, turnover up to limit", f"{r['normal_rate_small']:.0%}"),
        ("Normal rate, above limit", f"{r['normal_rate_large']:.0%}"),
        ("Turnover limit", cr(r["small_turnover_limit"])),
        ("Surcharge, normal regime", "0% up to ₹1 cr · 7% up to ₹10 cr · 12% above"),
        ("Section 200 (old 115BAA): rate + surcharge", f"{r['concessional_rate']:.0%} + {r['concessional_surcharge']:.0%}"),
        ("MAT rate", f"{r['mat_rate']:.0%}"),
        ("Health and education cess", f"{r['cess']:.0%}"),
    ], columns=["Item", "Value"]), hide_index=True, use_container_width=True)

summary, detail = engine.analyse_group(comp, proj, discount)
if summary.empty:
    st.error("No companies with projections found. Check that company names match in both files.")
    st.stop()

close = summary[summary["Margin over runner-up"] < 0.05 * summary["PV of tax - best"]]
total_normal = summary["PV of tax - stay normal"].sum()
total_saving = summary["PV saving"].sum()

# ---------------------------------------------------------------- recommendations
with tab_rec:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Companies", len(summary))
    k2.metric("Group PV of tax, best options", cr(summary["PV of tax - best"].sum()))
    k3.metric("Group PV saving", cr(total_saving), delta_color="inverse",
              delta=f"-{total_saving / total_normal:.1%} tax vs staying normal" if total_normal else None)
    k4.metric("Close calls (<5% margin)", len(close))

    st.markdown("#### Best option per company")
    records = summary.to_dict("records")
    for start in range(0, len(records), 3):                     # three cards per row
        for col, row in zip(st.columns(3), records[start:start + 3]):
            is_close = row["Entity"] in set(close["Entity"])
            badge = ('<span class="rw-badge warn">Close call</span>' if is_close else "")
            col.markdown(f"""
<div class="rw-card">
  <h4>{html.escape(str(row['Entity']))}</h4>
  <span class="rw-badge">{html.escape(row['Best option'])}</span> {badge}
  <p class="rw-big">{cr(row['PV saving'])}</p>
  <p class="rw-sub">PV saving against staying normal</p>
  <div class="rw-row"><span>Runner-up: {html.escape(str(row['Runner-up']))}</span>
       <span>{cr(row['Margin over runner-up'])} behind</span></div>
</div>""", unsafe_allow_html=True)

    if not close.empty:
        st.warning("The choice is sensitive to the projections for " + ", ".join(close["Entity"]) +
                   ". The option cannot be withdrawn once exercised, so test these before advising.", icon="⚖️")

    st.markdown("#### Summary table")
    show = summary.copy()
    for c in ["PV of tax - best", "PV of tax - stay normal", "PV saving", "Margin over runner-up"]:
        show[c] = show[c] / 1e7
    money = lambda label: st.column_config.NumberColumn(label, format="₹%.2f cr")
    st.dataframe(show, hide_index=True, use_container_width=True, column_config={
        "PV of tax - best": money("PV of tax, best"),
        "PV of tax - stay normal": money("PV of tax, stay normal"),
        "PV saving": money("PV saving"),
        "Margin over runner-up": money("Lead over runner-up")})

    rows = [d["schedule"].assign(Entity=name) for name, d in detail.items()]
    st.download_button("⬇ Download all year-by-year schedules (CSV)", pd.concat(rows).to_csv(index=False),
                       "regimewise_schedules.csv", mime="text/csv")

# ---------------------------------------------------------------- company deep-dive
with tab_co:
    name = st.selectbox("Company", list(detail.keys()))
    d = detail[name]
    opts = d["options"].copy()
    best = opts.iloc[0]["Option"]
    opts["PV (₹ cr)"] = opts["PV of tax"] / 1e7
    opts["Recommended"] = opts["Option"] == best
    opts["order"] = opts["Option"].map(option_order)

    st.markdown(f"**Recommended: <span style='color:{ACCENT}'>{html.escape(best)}</span>** - "
                f"present value of tax for each option, at a {discount}% discount rate. \"Switch in Yn\" means opting for Section 200 (old 115BAA) from that year.",
                unsafe_allow_html=True)
    sort = list(opts.sort_values("order")["Option"])
    base = alt.Chart(opts).encode(
        y=alt.Y("Option:N", sort=sort, title=None, axis=alt.Axis(labelFontSize=13, labelLimit=220)),
        x=alt.X("PV (₹ cr):Q", title="Present value of tax (₹ crore)", axis=alt.Axis(grid=True, gridColor="#EEF2F6")),
        tooltip=[alt.Tooltip("Option:N"), alt.Tooltip("PV (₹ cr):Q", format=",.2f", title="PV ₹ cr"),
                 alt.Tooltip("Total tax:Q", format=",.0f", title="Total tax ₹")])
    bars = base.mark_bar(cornerRadiusEnd=4, height=26).encode(
        color=alt.condition(alt.datum.Recommended, alt.value(ACCENT), alt.value(MUTED)))
    labels = base.mark_text(align="left", dx=6, fontSize=12, color="#334155").encode(
        text=alt.Text("PV (₹ cr):Q", format=",.2f"))
    st.altair_chart((bars + labels).properties(height=60 + 38 * len(opts)).configure_view(strokeWidth=0),
                    use_container_width=True)

    sched = d["schedule"]
    for n in sched["Note"]:
        if n:
            st.info(n, icon="🔁")
    st.markdown("#### Year by year under the recommended option")
    sshow = sched.copy()
    for c in ["Total income", "Tax", "MAT credit c/f", "Loss c/f"]:
        sshow[c] = sshow[c] / 1e7
    st.dataframe(sshow.drop(columns="Note"), hide_index=True, use_container_width=True, column_config={
        c: st.column_config.NumberColumn(c, format="₹%.2f cr") for c in ["Total income", "Tax", "MAT credit c/f", "Loss c/f"]})

    with st.expander("All options in figures"):
        figs = d["options"].copy()
        money_cols = ["Total tax", "PV of tax", "Unused MAT credit at end"]
        figs[money_cols] = figs[money_cols] / 1e7
        st.dataframe(figs, hide_index=True, use_container_width=True, column_config={
            c: st.column_config.NumberColumn(c, format="₹%.2f cr") for c in money_cols})

# ---------------------------------------------------------------- advisory note
with tab_note:
    st.markdown("#### Draft advisory note")
    st.caption("Built only from the figures on the other tabs. Review and edit before it goes to the client.")
    col_a, col_b = st.columns([1, 3])
    with col_a:
        use_ai = note.ai_available() and st.toggle("Draft with AI", value=True)
        if not note.ai_available():
            st.caption("Template mode. Add ANTHROPIC_API_KEY to .env for an AI-drafted note.")
        if st.button("Draft note", type="primary", use_container_width=True):
            with st.spinner("Drafting..."):
                st.session_state["note"] = (note.ai_note(summary, detail, discount) if use_ai
                                            else note.template_note(summary, detail, discount))
    with col_b:
        if "note" in st.session_state:
            text = st.text_area("Edit before downloading", st.session_state["note"], height=460)
            st.download_button("⬇ Download as Word", note.to_docx(text), "regime_advisory_note.docx",
                               type="primary")
        else:
            st.markdown("<div class='rw-card' style='color:#64748B'>Click <b>Draft note</b> to create the note. "
                        "It will appear here for editing.</div>", unsafe_allow_html=True)

st.markdown("<div class='rw-foot'>Decision-support tool. A Chartered Accountant must review every result before "
            "advice is given. Use anonymised data.</div>", unsafe_allow_html=True)
