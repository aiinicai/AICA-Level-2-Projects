"""Smart Ledger Anomaly & System-Override Detector - Streamlit dashboard.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import logging
import subprocess
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.agent import AgentResult, TraceEvent, run_agent
from src.config import (
    DEFAULT_HOLIDAYS, DEFAULT_TOP_N_EXTREME, DEFAULT_WEIGHTS, DETECTOR_LABELS, MAX_AGENT_ITERATIONS,
    PRIMARY_COLOR, REQUIRED_COLUMNS, SAMPLE_CSV, SAMPLE_ENTITY, SEVERITY_COLORS,
    SEVERITY_FILLS, SEVERITY_ORDER, DetectorConfig,
)
from src.data_loader import (
    SchemaError, detect_kind, list_sheets, load_ledger, missing_required, read_header, suggest_mapping,
    suggest_sheet,
)
from src.detectors import benford_stats, benford_table
from src.llm_client import LLMSettings, check_connection
from src.pipeline import analyse
from src.privacy import Pseudonymiser
from src.letter import build_letter_docx, make_context, render_markdown
from src.report_exporter import build_template_xlsx, build_workbook, letter_to_docx, letter_to_plain_text
from src.risk_scoring import detector_counts, kpis
from src.tools import LedgerToolbox
from src.utils import fmt_crore_lakh, fmt_inr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(page_title="Smart Ledger Anomaly Detector", page_icon="🔎", layout="wide")

st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 1.6rem; }}
      h1, h2, h3 {{ color: {PRIMARY_COLOR}; }}
      [data-testid="stMetric"] {{ background: rgba(31,58,95,0.06); border-left: 4px solid {PRIMARY_COLOR};
                                  padding: 10px 14px; border-radius: 6px; }}
      [data-testid="stMetricValue"] {{ font-size: 1.3rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SS = st.session_state


# =============================================================================== helpers
def style_fig(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=40, b=10),
                      font=dict(size=12), title_font=dict(size=15, color=PRIMARY_COLOR),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def ensure_sample_csv() -> None:
    """Generate the sample ledger on first use if it is missing."""
    if not SAMPLE_CSV.exists():
        with st.spinner("Generating sample ledger (one-off, ~10 s)…"):
            subprocess.run([sys.executable, str(SAMPLE_CSV.parent / "generate_sample_data.py")],
                           check=True, cwd=str(SAMPLE_CSV.parent.parent))


@st.cache_data(show_spinner=False, max_entries=4)
def cached_analyse(_df: pd.DataFrame, data_key: str, cfg: DetectorConfig, enabled: tuple[str, ...]) -> pd.DataFrame:
    return analyse(_df, cfg, list(enabled))


@st.cache_data(show_spinner=False, max_entries=4)
def cached_workbook(_results: pd.DataFrame, run_id: str, entity: str, period: str, letter: str, mode: str,
                    cfg: DetectorConfig) -> bytes:
    return build_workbook(_results, entity, period, letter, mode, cfg)


def parse_holidays(text: str) -> tuple[dt.date, ...]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                out.append(dt.date.fromisoformat(line))
            except ValueError:
                st.sidebar.warning(f"Ignoring invalid holiday date: {line!r} (use YYYY-MM-DD)")
    return tuple(out)


# =============================================================================== sidebar
st.sidebar.title("🔎 Ledger Anomaly Detector")
st.sidebar.caption("Scan 100% of journal entries • Python variance analysis • LLM management letter")

run_clicked = st.sidebar.button("▶ Run analysis", type="primary", key="run_btn", width="stretch")
gen_clicked = st.sidebar.button("✉ Generate Management Letter", key="gen_btn", width="stretch",
                                disabled="analysis" not in SS)
force_offline = st.sidebar.checkbox("Offline mode (no LLM call)", value=False)

st.sidebar.header("1 · Data")
UPLOAD = "Upload CSV / Excel file"
source = st.sidebar.radio("Ledger source", ["Sample ledger (≈52k entries)", UPLOAD], key="source")
entity = st.sidebar.text_input("Entity name", SAMPLE_ENTITY)
uploaded = None
sheet_choice: str | None = None
mapping_override: dict[str, str] = {}
if source == UPLOAD:
    uploaded = st.sidebar.file_uploader("Journal-entry / general-ledger file", type=["csv", "xlsx", "xlsm", "xls"],
                                        help="CSV or Excel (.xlsx, .xlsm, .xls). Title rows above the header and "
                                             "several worksheets are handled.")
    st.sidebar.download_button("⬇ Excel input template", build_template_xlsx(), "ledger_input_template.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_template")
    if uploaded is not None:
        up_bytes = uploaded.getvalue()
        try:
            kind = detect_kind(io.BytesIO(up_bytes))
            if kind != "csv":
                sheets = list_sheets(io.BytesIO(up_bytes))
                if not sheets:
                    st.sidebar.error("Could not read this Excel file (for old .xls files install `xlrd`, or save as .xlsx).")
                    st.stop()
                default_sheet = suggest_sheet(io.BytesIO(up_bytes)) or sheets[0]
                sheet_choice = st.sidebar.selectbox("Worksheet", sheets, index=sheets.index(default_sheet),
                                                    help="Pre-selected: the sheet that best matches the ledger columns.")
            header = read_header(io.BytesIO(up_bytes), sheet_choice)
        except Exception as exc:  # noqa: BLE001 - unreadable / corrupt file
            st.sidebar.error(f"Cannot read this file: {exc}")
            st.stop()
        auto_map = suggest_mapping(header)
        missing = missing_required(auto_map)
        mapping_override = dict(auto_map)
        if missing:
            st.sidebar.warning("Some required columns were not recognised. Map them below.")
        with st.sidebar.expander("Column mapping", expanded=bool(missing)):
            st.caption("Required: " + ", ".join(REQUIRED_COLUMNS))
            for col in missing:
                choice = st.selectbox(f"{col}", ["— not in file —"] + header, key=f"map_{col}")
                if choice != "— not in file —":
                    mapping_override[col] = choice

st.sidebar.header("2 · Detectors & thresholds")
with st.sidebar.expander("Enabled detectors", expanded=False):
    enabled = [k for k, label in DETECTOR_LABELS.items() if st.checkbox(label, value=True, key=f"en_{k}")]
with st.sidebar.expander("Thresholds", expanded=False):
    threshold_amount = st.number_input("Approval threshold (₹)", 100_000, 100_000_000, 1_000_000, 50_000,
                                       help="Amounts just below this limit are flagged.")
    band = st.slider("Just-below band (%)", 1.0, 15.0, 5.0, 0.5)
    z_cut = st.slider("Z-score cutoff (σ)", 2.0, 6.0, 3.5, 0.1, help="Applied to log-amount per account.")
    iqr_mult = st.slider("IQR fence multiplier", 1.5, 6.0, 3.0, 0.5)
    mom_pct = st.slider("Month-on-month spike vs 3-mo mean (%)", 50, 500, 150, 10)
    ah_a, ah_b = st.columns(2)
    ah_start = ah_a.slider("After-hours from (h)", 0, 23, 22, help="Hour (inclusive) the night window begins.")
    ah_end = ah_b.slider("until (h)", 0, 23, 5, help="Hour (exclusive) it ends; may be earlier than 'from' (wraps midnight).")
    backdate = st.slider("Back-dated if posting > N days after document date", 7, 120, 30)
    round_unit = st.number_input("Round-figure unit (₹)", 10_000, 10_000_000, 100_000, 10_000)
    period_end_days = st.slider("Period-end window (last N days)", 1, 5, 2)
    dormant_days = st.slider("Dormant account gap (days)", 60, 365, 180, 10)
    holiday_text = st.text_area("Public holidays (YYYY-MM-DD per line)",
                                "\n".join(d.isoformat() for d in DEFAULT_HOLIDAYS), height=110)
with st.sidebar.expander("Risk weights & severity bands"):
    weights = {k: float(st.slider(DETECTOR_LABELS[k], 0, 40, int(w), key=f"w_{k}"))
               for k, w in DEFAULT_WEIGHTS.items()}
    extreme_min = st.slider("Extreme band starts at score", 50, 95, 70)
top_n = st.sidebar.slider("Max Extreme entries sent to the LLM", 5, 50, DEFAULT_TOP_N_EXTREME,
                          help="Only the top-N Extreme entries (pseudonymised) are exposed to the model via tools.")

cfg = DetectorConfig(
    holidays=parse_holidays(holiday_text) or tuple(DEFAULT_HOLIDAYS),
    after_hours_start=ah_start, after_hours_end=ah_end, threshold_amount=float(threshold_amount),
    threshold_band_pct=band, round_unit=float(round_unit), zscore_cutoff=z_cut, iqr_multiplier=iqr_mult,
    mom_pct_cutoff=float(mom_pct), period_end_days=period_end_days, backdate_days=backdate,
    dormant_days=dormant_days, weights=weights, extreme_min_score=float(extreme_min),
    high_min_score=min(50.0, float(extreme_min) - 5), medium_min_score=30.0,
)

st.sidebar.header("3 · LLM (Claude / OpenAI / Groq)")
PROVIDER_OPTIONS = ["anthropic", "openai", "groq"]
_env_provider = LLMSettings.from_env().provider
provider = st.sidebar.selectbox("Provider", PROVIDER_OPTIONS, index=PROVIDER_OPTIONS.index(_env_provider))
default_settings = LLMSettings.from_env(provider=provider)
model = st.sidebar.text_input("Model", default_settings.model)
typed_key = st.sidebar.text_input("API key (optional - overrides .env)", type="password",
                                  help="Kept in memory for this session only. Prefer the .env file.")
settings = LLMSettings.from_env(provider=provider, model=model, api_key=typed_key or None)
if settings.has_key:
    st.sidebar.caption("🔑 API key found.")
else:
    st.sidebar.caption("⚠️ No API key found - the offline template letter will be used.")
if st.sidebar.button("Test API connection", key="test_btn"):
    with st.sidebar.status("Contacting the API…"):
        ok, msg = check_connection(settings)
    (st.sidebar.success if ok else st.sidebar.error)(msg)
st.sidebar.info("🔒 Privacy: user names are pseudonymised (USER_nn) and only the top Extreme entries "
                "are exposed to the model through tools. The name map never leaves this machine.")

# =============================================================================== load + analyse
if source == UPLOAD and uploaded is not None:
    raw_bytes = uploaded.getvalue()
    source_key = ("upload:" + hashlib.md5(raw_bytes).hexdigest() + f":{sheet_choice}"
                  + json.dumps(mapping_override, sort_keys=True))
else:
    raw_bytes = None
    if run_clicked and source != UPLOAD:
        ensure_sample_csv()
    source_key = f"sample:{SAMPLE_CSV.stat().st_mtime_ns if SAMPLE_CSV.exists() else 0}"
sig = (source_key, json.dumps(cfg.to_dict(), sort_keys=True, default=str), tuple(enabled))

if run_clicked:
    if source == UPLOAD and uploaded is None:
        st.error("Please upload a CSV or Excel file, or switch to the sample ledger.")
        st.stop()
    bar = st.progress(0.0, text="Reading file in chunks…")

    def on_progress(rows: int, frac: float | None) -> None:
        bar.progress(min(frac or 0.0, 1.0), text=f"Reading file… {rows:,} rows loaded")

    try:
        if SS.get("raw_key") != source_key:
            df, report = load_ledger(io.BytesIO(raw_bytes) if raw_bytes is not None else SAMPLE_CSV,
                                     mapping=mapping_override or None, progress_cb=on_progress, sheet=sheet_choice)
            SS["raw"], SS["report"], SS["raw_key"] = df, report, source_key
        bar.progress(1.0, text="Running detectors…")
        with st.spinner("Running 12 detectors and risk scoring on the full ledger…"):
            results = cached_analyse(SS["raw"], source_key, cfg, tuple(enabled))
    except SchemaError as exc:
        bar.empty()
        st.error(f"**Cannot read this ledger.** {exc}")
        st.info("Use the *Column mapping* panel in the sidebar to map your headers to the required columns.")
        st.stop()
    except Exception as exc:  # noqa: BLE001
        bar.empty()
        st.error(f"Unexpected problem while processing the file: {type(exc).__name__}: {exc}")
        st.stop()
    bar.empty()
    pseudo = Pseudonymiser(pd.concat([results["posted_by"], results["approved_by"]]))
    SS["analysis"] = dict(results=results, pseudo=pseudo, sig=sig, entity=entity, cfg=cfg, run_id=sig[0] + str(hash(sig[1])))
    SS["agent"] = None
    SS.pop("letter_override", None)
    st.rerun()      # re-render the sidebar so the "Generate Management Letter" button becomes enabled

# =============================================================================== landing page
if "analysis" not in SS:
    st.title("Smart Ledger Anomaly & System-Override Detector")
    st.markdown(
        "Traditional audit sampling skips key ledger anomalies and strange weekend overrides. "
        "This dashboard tests **100% of journal entries**, ranks them by risk, and lets an **LLM agent** investigate "
        "the extreme ones with Python tools and draft a **Management Letter**."
    )
    c1, c2, c3 = st.columns(3)
    c1.markdown("##### 1 · Ingest\nCSV or Excel upload (any worksheet), chunked load, schema validation and column mapping.")
    c2.markdown("##### 2 · Detect\n12 vectorised tests: SoD, weekend/after-hours, Benford, z-score/IQR, duplicates, back-dating…")
    c3.markdown("##### 3 · Investigate\nClaude tool-calling agent → Management Letter Draft + Excel audit report.")
    st.info("👈 Choose a data source in the sidebar (or keep the sample ledger) and click **▶ Run analysis**.")
    st.stop()

A = SS["analysis"]
results: pd.DataFrame = A["results"]
pseudo: Pseudonymiser = A["pseudo"]
run_entity: str = A["entity"]
k = kpis(results)
period_label = f"{results['posting_date'].min():%B %Y} to {results['posting_date'].max():%B %Y}"

st.title("Smart Ledger Anomaly & System-Override Detector")
st.caption(f"{run_entity} • {period_label} • {k['total_entries']:,} journal entries scanned")
if A["sig"] != sig:
    st.warning("Sidebar settings changed since the last run - click **▶ Run analysis** to refresh the results.")
if "report" in SS:
    rep = SS["report"]
    st.caption(f"📄 Source: {rep.file_kind.upper()}" + (f" • worksheet “{rep.sheet}”" if rep.sheet else "")
               + f" • {rep.rows_loaded:,} rows loaded")
for w in SS["report"].warnings if "report" in SS else []:
    st.caption(f"ℹ️ {w}")

cols = st.columns(6)
cols[0].metric("Entries scanned", f"{k['total_entries']:,}")
cols[1].metric("Total value", fmt_crore_lakh(k["total_value"]))
cols[2].metric("Flagged entries", f"{k['flagged_entries']:,}")
cols[3].metric("% flagged", f"{k['flagged_pct']:.1f}%")
cols[4].metric("Extreme entries", f"{k['extreme_count']:,}", help="Risk score at or above the Extreme band.")
cols[5].metric("Value at risk", fmt_crore_lakh(k["value_at_risk"]), help="Total amount of High + Extreme entries.")

# =============================================================================== agent run (live trace above the tabs)
if gen_clicked:
    llm_top_n = min(top_n, 10) if settings.provider == "groq" else top_n    # Groq free tier: ~8k tokens/minute
    toolbox = LedgerToolbox(results, A["cfg"], pseudo, run_entity, default_top_n=llm_top_n)
    box = st.status("🤖 Agent investigating extreme anomalies…", expanded=True)
    ICONS = {"start": "🚀", "llm_call": "🧠", "tool_call": "🔧", "tool_result": "✅", "tool_error": "⚠️",
             "final": "📝", "fallback": "↩️", "verify": "🔍"}

    def live(ev: TraceEvent) -> None:
        box.write(f"`{ev.ts}` {ICONS.get(ev.kind, '•')} **{ev.title}** {('— ' + ev.detail[:160]) if ev.detail else ''}")

    try:
        agent_result = run_agent(toolbox, settings, run_entity, period_label, top_n=llm_top_n,
                                 max_iterations=MAX_AGENT_ITERATIONS, on_event=live, force_offline=force_offline)
    except Exception as exc:  # noqa: BLE001 - never leave the user without a letter
        logging.getLogger("app").exception("Agent crashed")
        st.error(f"The agent failed unexpectedly ({type(exc).__name__}: {exc}). Using the offline template instead.")
        agent_result = run_agent(toolbox, settings, run_entity, period_label, top_n=llm_top_n, force_offline=True)
        agent_result.error = f"agent error: {type(exc).__name__}: {exc}"
    label = {"llm": "Letter drafted by the LLM agent", "offline": "Letter generated without LLM (template)",
             "no_exceptions": "No material exceptions - template letter"}[agent_result.mode]
    box.update(label=f"✅ {label} • {agent_result.tool_calls} tool calls • {agent_result.seconds:.1f}s",
               state="complete", expanded=False)
    SS["agent"] = agent_result
    SS["letter_override"] = None            # hand-edited Markdown, if any
    SS["letter_key"] = f"{agent_result.seconds}"

agent: AgentResult | None = SS.get("agent")

def current_letter(reveal: bool = False) -> str:
    """Markdown of the letter: the user's edit if any, else rendered from the structured letter data."""
    if agent is None:
        return ""
    override = SS.get("letter_override")
    if override:
        return pseudo.unmask_text(override) if reveal else override
    if agent.letter_data is not None:
        return render_markdown(agent.letter_data, make_context(results, pseudo, A["cfg"], run_entity,
                                                                period_label, reveal))
    return agent.letter


# =============================================================================== tabs
tab_over, tab_explore, tab_sod, tab_trace, tab_letter, tab_about = st.tabs(
    ["📊 Overview", "🔎 Anomaly Explorer", "🛡️ Override & SoD", "🤖 Agent Trace", "✉️ Management Letter", "ℹ️ About"])

# ------------------------------------------------------------------- Overview
with tab_over:
    flagged = results[results["is_flagged"]]
    counts = detector_counts(results)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(counts.sort_values("flagged_entries"), x="flagged_entries", y="label", orientation="h",
                     title="Flagged entries by detector", labels={"flagged_entries": "Entries", "label": ""},
                     color_discrete_sequence=[PRIMARY_COLOR], text="flagged_entries")
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_xaxes(range=[0, max(counts["flagged_entries"].max() * 1.15, 1)])
        st.plotly_chart(style_fig(fig, 420), width="stretch")
    with c2:
        sev = flagged["severity"].astype(str).value_counts().reindex(SEVERITY_ORDER, fill_value=0).reset_index()
        sev.columns = ["severity", "entries"]
        fig = px.bar(sev, x="severity", y="entries", color="severity", color_discrete_map=SEVERITY_COLORS,
                     title="Severity distribution (flagged entries)", text="entries")
        fig.update_layout(showlegend=False, xaxis_title="")
        st.plotly_chart(style_fig(fig, 420), width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        heat = (flagged.assign(wd=flagged["posting_date"].dt.dayofweek)
                .groupby(["wd", "posting_hour"]).size().unstack(fill_value=0)
                .reindex(index=range(7), columns=range(24), fill_value=0))
        fig = px.imshow(heat.values, x=list(range(24)), y=WEEKDAYS, aspect="auto",
                        color_continuous_scale="Reds", title="Anomalies by weekday and hour",
                        labels=dict(x="Hour of day", y="", color="Entries"))
        st.plotly_chart(style_fig(fig, 340), width="stretch")
    with c4:
        monthly = (flagged.assign(sev=flagged["severity"].astype(str))
                   .groupby(["period", "sev"])["amount"].sum().div(1e5).reset_index())
        fig = px.bar(monthly, x="period", y="amount", color="sev", color_discrete_map=SEVERITY_COLORS,
                     category_orders={"sev": SEVERITY_ORDER}, title="Monthly flagged value (₹ lakh)",
                     labels={"amount": "₹ lakh", "period": "", "sev": "Severity"})
        st.plotly_chart(style_fig(fig, 340), width="stretch")

    c5, c6 = st.columns(2)
    with c5:
        eligible = results.groupby("account_code").size()
        eligible = eligible[eligible >= cfg.benford_min_entries].index.tolist()
        choice = st.selectbox("Benford's law - account", ["All accounts"] + eligible, key="benford_acct")
        sample = results["amount"] if choice == "All accounts" else results.loc[results["account_code"] == choice, "amount"]
        tbl, bst = benford_table(sample), benford_stats(sample)
        fig = go.Figure()
        fig.add_bar(x=tbl["digit"], y=tbl["observed_pct"] * 100, name="Observed", marker_color=PRIMARY_COLOR)
        fig.add_scatter(x=tbl["digit"], y=tbl["expected_pct"] * 100, name="Benford expected", mode="lines+markers",
                        line=dict(color=SEVERITY_COLORS["Extreme"], width=2))
        fig.update_layout(title="First-digit distribution: observed vs expected (%)", xaxis_title="Leading digit",
                          yaxis_title="% of entries", xaxis=dict(dtick=1), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(style_fig(fig, 340), width="stretch")
        verdict = "conforms" if bst["mad"] <= cfg.benford_mad_cutoff else "DEVIATES"
        st.caption(f"n = {bst['n']:,} • MAD = {bst['mad']:.4f} (cutoff {cfg.benford_mad_cutoff}) • "
                   f"chi-square p = {bst['p_value']:.2e} → {verdict}")
    with c6:
        users = (flagged.groupby("posted_by")["risk_score"].sum().sort_values(ascending=False).head(10)
                 .sort_values().reset_index())
        fig = px.bar(users, x="risk_score", y="posted_by", orientation="h", title="Top 10 users by total risk score",
                     labels={"risk_score": "Sum of risk scores (flagged entries)", "posted_by": ""},
                     color_discrete_sequence=[PRIMARY_COLOR])
        st.plotly_chart(style_fig(fig, 400), width="stretch")

    st.download_button("⬇ Download Excel audit report", key="dl_xlsx_over", mime=(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), file_name="ledger_anomaly_report.xlsx",
        data=cached_workbook(results, A["run_id"], run_entity, period_label, current_letter(),
                             agent.mode if agent else "", A["cfg"]))

# ------------------------------------------------------------------- Explorer
with tab_explore:
    f1, f2, f3, f4 = st.columns([1.3, 1.6, 1, 1.2])
    sev_pick = f1.multiselect("Severity", SEVERITY_ORDER, default=["Extreme", "High"])
    det_pick = f2.multiselect("Detector fired", list(DETECTOR_LABELS), format_func=DETECTOR_LABELS.get)
    min_score = f3.slider("Min risk score", 0, 100, 0)
    search = f4.text_input("Search (ID / description / reason)")
    g1, g2 = st.columns(2)
    acct_pick = g1.selectbox("Account", ["All"] + sorted(results["account_code"].unique()))
    user_pick = g2.selectbox("Posted by", ["All"] + sorted(results["posted_by"].unique()))

    view = results[results["is_flagged"] & results["severity"].astype(str).isin(sev_pick) & (results["risk_score"] >= min_score)]
    if det_pick:
        view = view[view[[f"flag_{d}" for d in det_pick]].any(axis=1)]
    if acct_pick != "All":
        view = view[view["account_code"] == acct_pick]
    if user_pick != "All":
        view = view[view["posted_by"] == user_pick]
    if search:
        hay = (view["entry_id"] + " " + view["description"] + " " + view["reasons"]).str.contains(search, case=False, regex=False)
        view = view[hay]
    view = view.sort_values(["risk_score", "amount"], ascending=False)
    st.caption(f"{len(view):,} entries match" + (" (showing the first 1,000)" if len(view) > 1000 else ""))

    show_cols = ["entry_id", "posting_date", "posting_time", "account_code", "account_name", "amount", "entry_type",
                 "posted_by", "approved_by", "risk_score", "severity", "detectors_hit", "reasons"]
    table = view.head(1000)[show_cols].copy()
    table["posting_date"] = table["posting_date"].dt.strftime("%Y-%m-%d")
    table["amount"] = table["amount"].map(fmt_inr)
    table["severity"] = table["severity"].astype(str)

    def row_style(row: pd.Series) -> list[str]:
        return [f"background-color: #{SEVERITY_FILLS[row['severity']]}; color: #111827"] * len(row)

    st.dataframe(table.style.apply(row_style, axis=1), width="stretch", height=380, hide_index=True)

    st.subheader("Drill-down")
    ids = view["entry_id"].head(500).tolist()
    if ids:
        pick = st.selectbox("Select an entry", ids, key="drill_pick")
        row = view[view["entry_id"] == pick].iloc[0]
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Amount", fmt_inr(row["amount"]))
        d2.metric("Risk score", f"{row['risk_score']:.0f}")
        d3.metric("Severity", str(row["severity"]))
        d4.metric("Detectors fired", int(row["flag_count"]))
        left, right = st.columns([1, 1.4])
        with left:
            detail = {
                "Posting date / time": f"{row['posting_date']:%d-%b-%Y} {row['posting_time']}",
                "Document date": f"{row['document_date']:%d-%b-%Y}",
                "Account": f"{row['account_code']} - {row['account_name']}",
                "Description": row["description"], "Entry type": row["entry_type"],
                "Manual override": row["is_manual_override"], "Posted by": row["posted_by"],
                "Approved by": row["approved_by"] or "(none)", "Debit": fmt_inr(row["debit"]),
                "Credit": fmt_inr(row["credit"]), "Cost centre": row["cost_center"],
            }
            st.table(pd.DataFrame({"Field": detail.keys(), "Value": [str(v) for v in detail.values()]}).set_index("Field"))
        with right:
            st.markdown("**Why it was flagged**")
            for dname in DETECTOR_LABELS:
                if row[f"flag_{dname}"]:
                    st.markdown(f"- **{DETECTOR_LABELS[dname]}** (+{cfg.weights[dname]:.0f}): {row[f'why_{dname}']}")
            acct = results.loc[results["account_code"] == row["account_code"], "amount"]
            st.caption(f"Account context: {len(acct):,} entries • median {fmt_inr(acct.median(), 0)} • "
                       f"95th percentile {fmt_inr(acct.quantile(0.95), 0)} • this entry is "
                       f"{row['amount'] / acct.median():.1f}× the median")
    else:
        st.info("No entries match the current filters.")

# ------------------------------------------------------------------- Override & SoD
with tab_sod:
    approver = results["approved_by"].astype(str).str.strip()
    no_appr = results["is_manual_like"] & approver.str.lower().isin(["", "nan", "none", "null", "na", "n/a"])
    self_appr = results["is_manual_like"] & ~no_appr & (approver.str.lower() == results["posted_by"].str.lower())
    overrides = results[results["is_manual_override"] == "Y"]
    offtime = results[results["flag_weekend_holiday"]]
    m = st.columns(5)
    m[0].metric("Manual overrides", f"{len(overrides):,}")
    m[1].metric("No approver", f"{int(no_appr.sum()):,}")
    m[2].metric("Self-approved", f"{int(self_appr.sum()):,}")
    m[3].metric("Weekend / holiday", f"{len(offtime):,}")
    m[4].metric("After-hours", f"{int(results['flag_after_hours'].sum()):,}")

    breach = (pd.DataFrame({"user": results["posted_by"], "No approver": no_appr, "Self-approved": self_appr})
              .groupby("user").sum().astype(int))
    breach = breach[breach.sum(axis=1) > 0].sort_values("No approver", ascending=False).head(12).reset_index()
    if not breach.empty:
        fig = px.bar(breach.melt("user", var_name="Type", value_name="Entries"), x="user", y="Entries", color="Type",
                     title="Segregation-of-duties breaches by user", barmode="stack",
                     color_discrete_map={"No approver": SEVERITY_COLORS["Extreme"], "Self-approved": SEVERITY_COLORS["Medium"]})
        st.plotly_chart(style_fig(fig, 320), width="stretch")

    def small_table(df: pd.DataFrame) -> pd.DataFrame:
        t = df.sort_values(["risk_score", "amount"], ascending=False).head(500)[
            ["entry_id", "posting_date", "posting_time", "account_name", "amount", "posted_by", "approved_by",
             "is_manual_override", "risk_score", "severity"]].copy()
        t["posting_date"] = t["posting_date"].dt.strftime("%Y-%m-%d")
        t["amount"] = t["amount"].map(fmt_inr)
        t["severity"] = t["severity"].astype(str)
        return t

    with st.expander(f"Manual overrides ({len(overrides):,})", expanded=True):
        st.dataframe(small_table(overrides), width="stretch", height=260, hide_index=True)
    with st.expander(f"Weekend / public-holiday postings ({len(offtime):,})"):
        st.dataframe(small_table(offtime), width="stretch", height=260, hide_index=True)
    with st.expander(f"Self-approved or unapproved manual entries ({int((no_appr | self_appr).sum()):,})"):
        st.dataframe(small_table(results[no_appr | self_appr]), width="stretch", height=260, hide_index=True)

# ------------------------------------------------------------------- Agent trace
with tab_trace:
    st.markdown("The agent receives only **tool access**, never the raw ledger. Each row below is one step of the "
                "loop: *model call → tool call → tool result → … → final letter*.")
    if agent is None:
        st.info("Click **✉ Generate Management Letter** in the sidebar to run the agent. "
                "The live log also appears above the tabs while it runs.")
    else:
        mm = st.columns(5)
        mm[0].metric("Mode", {"llm": "LLM agent", "offline": "Offline template", "no_exceptions": "No exceptions"}[agent.mode])
        mm[1].metric("Model calls", agent.iterations)
        mm[2].metric("Tool calls", agent.tool_calls)
        mm[3].metric("Duration", f"{agent.seconds:.1f}s")
        mm[4].metric("Unverified IDs", len(agent.unverified_ids))
        if agent.error:
            st.warning(f"Fallback reason: {agent.error}")
        trace_df = pd.DataFrame([{"#": e.step, "time": e.ts, "step": e.kind, "action": e.title, "detail": e.detail[:300]}
                                 for e in agent.trace])
        st.dataframe(trace_df, width="stretch", hide_index=True, height=min(520, 60 + 36 * len(trace_df)))
        calls = [e for e in agent.trace if e.kind == "tool_call"]
        if calls:
            with st.expander("Tool-call arguments"):
                for e in calls:
                    st.code(f"{e.title}({e.detail})", language="python")

# ------------------------------------------------------------------- Letter
with tab_letter:
    if agent is None:
        st.info("No letter yet. Click **✉ Generate Management Letter** in the sidebar. With an API key the Claude "
                "agent investigates the extreme anomalies; without one a deterministic template is produced.")
    else:
        badge = {"llm": f"🤖 Drafted by {agent.provider} / {agent.model}",
                 "offline": "📄 Generated without LLM (offline template)",
                 "no_exceptions": "✅ No material exceptions"}[agent.mode]
        st.markdown(f"**{badge}** — draft for discussion; review before issue.")
        if agent.mode == "offline" and agent.error:
            st.warning(f"The LLM was **not** used. Reason: {agent.error}")
        reveal = st.checkbox("Reveal real user names (local only, never sent to the model)", value=False)
        md = current_letter(reveal)
        edited_flag = bool(SS.get("letter_override"))
        rendered_tab, edit_tab = st.tabs(["Rendered", "Edit"])
        with edit_tab:
            edited = st.text_area("Edit the letter (Markdown). Tables, headings and bold are kept in the Word file.",
                                  value=md, height=420, key=f"letter_editor_{SS.get('letter_key', '')}_{reveal}_{edited_flag}")
            if edited != md:
                SS["letter_override"] = edited
                st.rerun()
            if edited_flag and st.button("↺ Discard edits and restore the generated letter", key="reset_letter"):
                SS["letter_override"] = None
                st.rerun()
        with rendered_tab:
            st.markdown(md)
        if edited_flag or agent.letter_data is None:
            docx_bytes = letter_to_docx(md, run_entity, period_label)
        else:
            docx_bytes = build_letter_docx(agent.letter_data, make_context(results, pseudo, A["cfg"], run_entity,
                                                                           period_label, reveal))
        d0, d1, d2, d3 = st.columns(4)
        d0.download_button("⬇ Word (.docx)", docx_bytes, "management_letter.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_docx",
                           width="stretch", type="primary")
        d1.download_button("⬇ Letter (.md)", md, "management_letter.md", "text/markdown", key="dl_md", width="stretch")
        d2.download_button("⬇ Letter (.txt)", letter_to_plain_text(md), "management_letter.txt", "text/plain",
                           key="dl_txt", width="stretch")
        d3.download_button("⬇ Excel audit report", cached_workbook(results, A["run_id"], run_entity, period_label,
                                                                    current_letter(), agent.mode, A["cfg"]),
                           "ledger_anomaly_report.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx_letter",
                           width="stretch")

# ------------------------------------------------------------------- About
with tab_about:
    st.subheader("How this project meets the ICAI AICA Level 2 rubric")
    st.table(pd.DataFrame([
        ["Python & Agentic Logic (10)", "Vectorised Pandas detectors and conditional logic; Claude/OpenAI tool-calling "
         "loop with branching (no extremes, tool errors, exhausted budget, offline fallback).",
         "src/detectors.py, src/agent.py, src/tools.py"],
        ["API & Backend Architecture (10)", "Provider abstraction for the Claude and OpenAI endpoints with timeouts, "
         "exponential-backoff retries, auth / rate-limit / network error mapping, key handling via .env and a "
         "connection-test button.", "src/llm_client.py, src/privacy.py"],
        ["UI Deployment & Walkthrough (10)", "This Streamlit dashboard: KPIs, Plotly charts, explorer with drill-down, "
         "SoD panel, live agent trace, letter editor, Excel and text downloads.", "app.py, src/report_exporter.py"],
    ], columns=["Rubric parameter", "Where it is satisfied", "Code"]).set_index("Rubric parameter"))
    st.subheader("Method notes")
    st.markdown(
        "- **Variance analysis:** per-account z-score and IQR fence on log-amounts (ledger amounts are roughly "
        "log-normal), plus month-on-month spikes versus the prior three-month mean.\n"
        "- **Benford's law:** first-digit MAD and chi-square per account (minimum sample enforced); only the "
        "over-represented digit's entries are flagged.\n"
        "- **Risk score:** weighted sum of fired detectors (+10 for top-1% amounts), capped at 100. Extreme / High / "
        "Medium / Low bands are configurable in the sidebar.\n"
        "- **Privacy:** names → `USER_nn` before any LLM call; the model only sees tool outputs for Extreme entries.\n"
        "- **Limitations:** rule thresholds need calibration per client; analytics highlight exceptions, they are "
        "not audit conclusions; sample holidays are indicative."
    )
