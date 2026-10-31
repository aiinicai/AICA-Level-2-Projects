"""CHS Audit Assistant - interactive application.

Run:  .venv/bin/streamlit run app.py
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import os

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from chs_audit.ai_writer import AIWriter, LogEntry  # noqa: E402
from chs_audit.config import FIRM, FY_LABEL, SOCIETY, Firm, save_firm  # noqa: E402
from chs_audit.importer import REQUIRED_SHEETS, SHEET_HELP, build_template, save_upload, validate_workbook
from chs_audit.mockup_data import MOCKUP_DIR, MOCKUP_LABEL  # noqa: E402
from chs_audit.findings import inr  # noqa: E402
from chs_audit.report_excel import write_workbook  # noqa: E402
from chs_audit.run_audit import run_pipeline  # noqa: E402
from chs_audit.dashboard import build_dashboard  # noqa: E402
from chs_audit.compliance import parse_minutes  # noqa: E402

# --------------------------------------------------------------------------- look and feel
NAVY, TEAL, ORANGE, RED, AMBER, GREEN, GREY = "#0f2a4a", "#006b63", "#e8872b", "#d03b3b", "#ec835a", "#1a7f4b", "#5f6b7a"   # jjaa.in brand: navy, teal, saffron
SEV_COLOR = {"High": RED, "Medium": AMBER, "Low": "#c98500", "Info": GREEN}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Playfair+Display:wght@600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stDataFrame, button, input, textarea, select {font-family:'Manrope','Segoe UI',Arial,sans-serif}
h1, h2, h3, .hero h1, .brand-name {font-family:'Playfair Display',Georgia,serif !important; letter-spacing:0}
#MainMenu, footer {visibility:hidden}
.block-container{padding-top:1.4rem;padding-bottom:3rem;max-width:1280px}
section[data-testid="stSidebar"]{background:#0f2a4a}
section[data-testid="stSidebar"] *{color:#E9EEF5}
section[data-testid="stSidebar"] .stMarkdown small{color:#a9b8cc}
section[data-testid="stSidebar"] a{color:#f3b47a}
section[data-testid="stSidebar"] img{background:#fff;border-radius:8px;padding:8px 10px}
.brand{display:flex;align-items:center;gap:12px;margin:4px 0 2px}
.brand-mark{width:46px;height:46px;border-radius:50%;background:#e8872b;color:#fff;font-weight:800;font-size:1.05rem;display:flex;align-items:center;justify-content:center;flex:0 0 46px;letter-spacing:.04em}
.brand-name{font-size:1.12rem;font-weight:700;color:#fff;margin:0;line-height:1.2}
.brand-sub{font-size:.78rem;color:#f3b47a;letter-spacing:.08em;text-transform:uppercase}
.brand-course{font-size:.74rem;color:#c9d3df;margin:6px 0 2px;letter-spacing:.02em}
.hero{background:linear-gradient(120deg,#0f2a4a 0%,#1c3d63 70%,#006b63 100%);color:#fff;border-radius:14px;padding:22px 26px;margin-bottom:18px;border-left:6px solid #e8872b}
.hero h1{margin:0;font-size:1.6rem;font-weight:700;color:#fff}
.hero p{margin:6px 0 0;opacity:.92;font-size:.95rem}
.hero b{color:#f3b47a}
.kpi{background:#fff;border:1px solid #e6e1d8;border-radius:12px;padding:14px 16px;box-shadow:0 1px 2px rgba(15,42,74,.06);height:100%;border-top:3px solid #e8872b}
.kpi .k{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:#5f6b7a}
.kpi .v{font-size:1.5rem;font-weight:800;color:#0f2a4a;margin:4px 0 2px;font-variant-numeric:tabular-nums}
.kpi .s{font-size:.78rem;color:#52514e}
.chip{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.74rem;font-weight:600;border:1px solid;white-space:nowrap}
.card{background:#fff;border:1px solid #e6e1d8;border-radius:12px;padding:16px 18px;margin-bottom:12px}
.card h4{margin:0 0 6px;color:#0f2a4a}
.muted{color:#5f6b7a;font-size:.85rem}
.obs{border-left:4px solid var(--c);background:#fff;border-radius:10px;padding:12px 16px;margin-bottom:10px;border-top:1px solid #e6e1d8;border-right:1px solid #e6e1d8;border-bottom:1px solid #e6e1d8}
.obs .t{font-weight:700;color:#0f2a4a}
.obs .m{color:#52514e;font-size:.9rem;margin:4px 0}
.obs .r{color:#006b63;font-size:.85rem}
.stTabs [data-baseweb="tab"]{font-weight:600}
div[data-testid="stMetric"]{background:#fff;border:1px solid #e6e1d8;border-radius:12px;padding:10px 14px}
</style>
"""


def chip(text: str, color: str) -> str:
    return f'<span class="chip" style="color:{color};border-color:{color};background:{color}14">{text}</span>'


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="k">{label}</div><div class="v">{value}</div><div class="s">{sub}</div></div>', unsafe_allow_html=True)


def lakh(x: float) -> str:
    return f"₹{x / 1e5:.2f} L" if abs(x) >= 1e5 else inr(x).replace("Rs ", "₹")


def rupee(x) -> str:
    try:
        return inr(float(x)).replace("Rs ", "₹")
    except Exception:
        return str(x)


def fig_layout(fig: go.Figure, height=320, **kw) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, Segoe UI, sans-serif", color="#1B2A4A", size=12), legend=dict(orientation="h", y=1.12, x=0), **kw)
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#ECEAE5", zeroline=False)
    return fig


def hbar(labels, values, colors, text=None, height=300):
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=colors, text=text or [rupee(v) for v in values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{text}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return fig_layout(fig, height=height, xaxis=dict(visible=False))


def sev_chip(s):
    return chip(s, SEV_COLOR.get(s, GREY))


# --------------------------------------------------------------------------- state and data
def stored_api_key() -> str:
    """Key from .streamlit/secrets.toml (git-ignored) or the ANTHROPIC_API_KEY env var; else empty."""
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"]).strip()
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def stored_model() -> str:
    try:
        if "ANTHROPIC_MODEL" in st.secrets:
            return str(st.secrets["ANTHROPIC_MODEL"]).strip()
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5").strip()


def init_state():
    ss = st.session_state
    ss.setdefault("data_dir", str(ROOT / "data" / "raw"))
    ss.setdefault("data_label", "Sample society (Sunrise Heights, 64 flats)")
    ss.setdefault("as_of", date(2026, 7, 15))
    ss.setdefault("api_key", stored_api_key())
    ss.setdefault("model", stored_model())
    ss.setdefault("ai_log", [])
    ss.setdefault("drafts", {})
    ss.setdefault("chat", [])


@st.cache_resource(show_spinner="Running audit tests...")
def pipeline(data_dir: str, as_of_iso: str, version: int):
    return run_pipeline(Path(data_dir), date.fromisoformat(as_of_iso))


def results():
    ss = st.session_state
    return pipeline(ss.data_dir, ss.as_of.isoformat(), ss.get("data_version", 0))


def writer() -> AIWriter:
    ss = st.session_state
    w = AIWriter(enabled=bool(ss.api_key), model=ss.model, api_key=ss.api_key or None)
    w.log = ss.ai_log
    return w


def run_draft(key: str, gen, waiting: str = "Claude is reading the audit context (the first words can take up to a minute)...") -> str | None:
    """Stream a Claude draft with a visible status while waiting for the first token; store it and rerun so the page shows the stored draft once."""
    box = st.status(waiting, expanded=False)

    def wrapped():
        first = True
        for chunk in gen:
            if first:
                box.update(label="Claude is drafting...", state="running")
                first = False
            yield chunk
        box.update(label="Draft complete. Review and edit below.", state="complete")

    try:
        out = st.write_stream(wrapped())
    except Exception as exc:
        box.update(label="Claude request failed", state="error")
        st.error(f"Claude request failed: {exc}")
        return None
    if out:
        st.session_state.drafts[key] = out
        st.rerun()
    return out


# --------------------------------------------------------------------------- pages
def page_overview():
    r = results()
    f = r["findings_df"]; ledger = r["sheets"]["Member_Ledger"]; gst = r["sheets"]["GST_Summary"]; tax = r["tax_summary"]
    st.markdown(f'<div class="hero"><h1>{SOCIETY.name}</h1><p>Statutory audit {FY_LABEL} · {len(ledger)} flats · audit date {r["as_of"]:%d %b %Y} · Regn. {SOCIETY.reg_no}</p><p>Statutory auditor: <b>{FIRM.auditor}</b>{" · " + FIRM.website if FIRM.website else ""}</p></div>', unsafe_allow_html=True)
    sev = f.severity.value_counts()
    c = st.columns(6)
    kpi(c[0], "Member dues", lakh(ledger.closing_balance.clip(lower=0).sum()), f"{int((ledger.months_of_arrears >= 3).sum())} members over 3 months")
    kpi(c[1], "Observations", str(len(f)), f"{sev.get('High', 0)} high · {sev.get('Medium', 0)} medium · {sev.get('Low', 0) + sev.get('Info', 0)} low")
    kpi(c[2], "GST billing errors", lakh(gst.amount.abs().sum()), f"{int(gst.bills.sum())} bills · {int(gst.flats.sum())} flats")
    kpi(c[3], "Sinking fund gap", lakh(r["sf_gap"]), "vs earmarked FDs")
    kpi(c[4], "Quantified exposure", lakh(f.amount.sum()), "all observations")
    kpi(c[5], "Income-tax payable", rupee(tax["net_payable"] + tax["interest_234b"] + tax["interest_234c"]), "incl. 234B/C interest")
    st.write("")
    a, b = st.columns([1.1, 1])
    with a:
        st.markdown("#### Observations by module and severity")
        pivot = f.pivot_table(index="module", columns="severity", values="id", aggfunc="count", fill_value=0)
        pivot = pivot.reindex(columns=[s for s in ["High", "Medium", "Low", "Info"] if s in pivot.columns]).sort_values(pivot.columns.tolist(), ascending=False)
        fig = go.Figure()
        for s in pivot.columns:
            fig.add_bar(y=pivot.index, x=pivot[s], name=s, orientation="h", marker_color=SEV_COLOR[s], hovertemplate="%{y}: %{x} " + s + "<extra></extra>")
        fig.update_layout(barmode="stack"); fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_layout(fig, height=330), use_container_width=True)
    with b:
        st.markdown("#### Monthly billing vs collection")
        m = r["monthly"]
        fig = go.Figure()
        fig.add_scatter(x=m.month, y=m.billed, name="Billed", mode="lines+markers", line=dict(color=SERIES[0], width=2), hovertemplate="Billed %{x}: ₹%{y:,.0f}<extra></extra>")
        fig.add_scatter(x=m.month, y=m.collected, name="Collected", mode="lines+markers", line=dict(color=SERIES[2], width=2), hovertemplate="Collected %{x}: ₹%{y:,.0f}<extra></extra>")
        st.plotly_chart(fig_layout(fig, height=330, yaxis=dict(rangemode="tozero")), use_container_width=True)

    st.markdown("#### Audit observations")
    fcol, mcol = st.columns([1, 2])
    sel_sev = fcol.multiselect("Severity", ["High", "Medium", "Low", "Info"], default=["High", "Medium", "Low", "Info"], label_visibility="collapsed")
    sel_mod = mcol.multiselect("Module", sorted(f.module.unique()), default=sorted(f.module.unique()), label_visibility="collapsed")
    view = f[f.severity.isin(sel_sev) & f.module.isin(sel_mod)]
    for row in view.itertuples():
        amt = f" · {rupee(row.amount)}" if row.amount else ""
        st.markdown(f'<div class="obs" style="--c:{SEV_COLOR[row.severity]}"><div class="t">{row.id} · {row.area} {sev_chip(row.severity)} <span class="muted">{row.module}{amt}</span></div>'
                    f'<div class="m">{row.observation}</div><div class="r">Reference: {row.reference}</div><div class="m"><b>Action:</b> {row.recommendation}</div></div>', unsafe_allow_html=True)


def page_members():
    r = results(); s = r["sheets"]
    ledger, interest, defaulters = s["Member_Ledger"], s["Interest_Recompute"], s["Defaulters"]
    st.markdown("## Member ledger and defaulters")
    st.caption("Ledger rebuilt from bills and receipts; interest recomputed at 21% p.a. simple interest on the amount outstanding at each bill date (bye-law 72).")
    c = st.columns(4)
    kpi(c[0], "Billed in year", lakh(ledger.billed_fy.sum()))
    kpi(c[1], "Collected in year", lakh(ledger.received_fy.sum()), f"{ledger.received_fy.sum() / ledger.billed_fy.sum():.1%} of billing")
    kpi(c[2], "Closing dues", lakh(ledger.closing_balance.clip(lower=0).sum()), f"{int((ledger.months_of_arrears >= 3).sum())} defaulters over 3 months")
    kpi(c[3], "Interest short-charged", rupee(interest["short_(excess)_charge"].clip(lower=0).sum()) if len(interest) else "₹0", f"{len(interest)} accounts")
    st.write("")
    a, b = st.columns([1, 1.3])
    with a:
        st.markdown("#### Dues by ageing bucket")
        order = ["Regular", "Arrears 1-3 months", "Defaulter (>3 months)", "Chronic defaulter (>6 months)"]
        vals = [float(ledger[ledger.status == o].closing_balance.clip(lower=0).sum()) for o in order]
        cnt = [int((ledger.status == o).sum()) for o in order]
        st.plotly_chart(hbar([f"{o} ({n})" for o, n in zip(["Regular", "1-3 months", "3-6 months", "Over 6 months"], cnt)], vals, ["#86b6ef", "#5598e7", "#2a78d6", "#0d366b"], height=260), use_container_width=True)
    with b:
        st.markdown("#### Interest recomputation exceptions")
        if len(interest):
            st.dataframe(interest.rename(columns={"short_(excess)_charge": "short charge"}), hide_index=True, use_container_width=True,
                         column_config={"interest_charged_by_society": st.column_config.NumberColumn("charged by society", format="%.2f"),
                                        "interest_per_bye_law_21pct": st.column_config.NumberColumn("per bye-law @21%", format="%.2f"),
                                        "short charge": st.column_config.NumberColumn(format="%.2f")})
        else:
            st.success("Interest charged agrees with the bye-law rate for all members.")
    st.markdown("#### Member ledger")
    status = st.multiselect("Status", ledger.status.unique().tolist(), default=ledger.status.unique().tolist())
    view = ledger[ledger.status.isin(status)].copy()
    st.dataframe(view, hide_index=True, use_container_width=True, height=380,
                 column_config={c: st.column_config.NumberColumn(format="%.0f") for c in ["opening_arrears", "billed_fy", "received_fy", "closing_balance", "received_after_year_end"]})
    st.markdown("#### Reminder letters for defaulters")
    flat = st.selectbox("Select defaulter", defaulters.flat_no.tolist(), format_func=lambda x: f"{x} · {rupee(defaulters.set_index('flat_no').loc[x, 'closing_balance'])} · {defaulters.set_index('flat_no').loc[x, 'months_of_arrears']:.0f} months")
    row = defaulters[defaulters.flat_no == flat].iloc[0]
    w = writer()
    col1, col2 = st.columns([1, 1])
    key = f"reminder_{flat}"
    if col1.button("Draft with Claude", disabled=not w.enabled, key=key + "_ai", type="primary"):
        instr, ctx, mt = w.task_spec("reminder", row=row, as_of=r["as_of"])
        run_draft(key, w.stream_task(key, instr, ctx, mt))
    if col2.button("Use offline template", key=key + "_tpl"):
        st.session_state.drafts[key] = w.reminder_letter(row, r["as_of"])
    if key in st.session_state.drafts:
        st.text_area("Letter", st.session_state.drafts[key], height=320, key=key + "_txt")
        st.download_button("Download letter", st.session_state.drafts[key], file_name=f"Reminder_{flat}.txt")


def page_gst():
    r = results(); s = r["sheets"]
    sched, summary = s["GST_Check"], s["GST_Summary"]
    st.markdown("## GST on maintenance bills")
    st.caption("Rs 7,500 per member per month test (Notification 12/2017 entry 77(c), Circular 109/28/2019): property tax excluded from the reckonable amount; once the limit is crossed the whole amount is taxable.")
    c = st.columns(4)
    over = float(sched[sched.difference > 1].difference.sum()); under = float(-sched[sched.difference < -1].difference.sum())
    kpi(c[0], "Bills tested", f"{len(sched)}", f"{int(sched.gst_applicable.sum())} liable to GST")
    kpi(c[1], "Over-charged", rupee(over), "credit notes u/s 34")
    kpi(c[2], "Under-charged", rupee(under), "debit notes + interest")
    kpi(c[3], "Flats affected", f"{sched[sched.issue != ''].flat_no.nunique()}", "of 64")
    st.write("")
    a, b = st.columns([1, 1.4])
    with a:
        st.markdown("#### Errors by cause")
        st.plotly_chart(hbar(summary.issue.tolist(), summary.amount.abs().tolist(), [ORANGE, ORANGE, SERIES[2]], height=240), use_container_width=True)
    with b:
        st.markdown("#### GST difference by flat (society charged minus correct)")
        by_flat = sched.groupby("flat_no").difference.sum()
        by_flat = by_flat[by_flat.abs() > 1].sort_values()
        fig = go.Figure(go.Bar(x=by_flat.index, y=by_flat.values, marker_color=[RED if v < 0 else ORANGE for v in by_flat.values], hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>"))
        st.plotly_chart(fig_layout(fig, height=240), use_container_width=True)
    st.markdown("#### Bill-level test")
    only = st.checkbox("Show only bills with issues", value=True)
    view = sched[sched.issue != ""] if only else sched
    st.dataframe(view, hide_index=True, use_container_width=True, height=400,
                 column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ["property_tax", "reckonable", "gst_charged", "correct_gst", "difference"]})


def page_expenses():
    r = results(); s = r["sheets"]
    st.markdown("## Funds, bank and expenditure")
    t1, t2, t3, t4 = st.tabs(["Fund compliance", "Bank reconciliation", "Expense anomalies", "TDS"])
    with t1:
        fs = s["Fund_Compliance"].copy()
        for c in ("expected", "actual"):
            fs[c] = fs[c].apply(lambda v: rupee(v) if isinstance(v, (int, float)) else str(v))
        st.dataframe(fs, hide_index=True, use_container_width=True)
        d = r["data"]
        sf = d.fund("Sinking Fund - opening") + d.fund("Sinking Fund - collected")
        fig = go.Figure(go.Bar(x=["Sinking fund balance", "Earmarked FDs"], y=[sf, d.fund("Fixed deposits - Thane")], marker_color=[SERIES[0], SERIES[2]], text=[rupee(sf), rupee(d.fund("Fixed deposits - Thane"))], textposition="outside", cliponaxis=False))
        st.plotly_chart(fig_layout(fig, height=280, title="Sinking fund vs investments (bye-law 15 / s.70)"), use_container_width=True)
    with t2:
        a, b = st.columns([1, 1])
        with a:
            st.markdown("#### Reconciliation at 31-Mar-2026")
            st.dataframe(s["Bank_Reconciliation"], hide_index=True, use_container_width=True, column_config={"amount": st.column_config.NumberColumn(format="%.2f")})
        with b:
            st.markdown("#### Exceptions")
            ex = s["Bank_Exceptions"]
            for row in ex.itertuples():
                st.markdown(f'<div class="card"><h4>{row.exception}</h4><span class="muted">Flat {row.flat_no if isinstance(row.flat_no, str) else "-"} · {row.receipt_date:%d-%b-%Y} · {row.reference}</span><div style="font-size:1.2rem;font-weight:700">{rupee(row.amount)}</div></div>', unsafe_allow_html=True)
    with t3:
        an, ben = s["Expense_Anomalies"], s["Benford"]
        for row in an.itertuples():
            st.markdown(f'<div class="obs" style="--c:{ORANGE}"><div class="t">{row.test} <span class="muted">· {row.vendor}</span> <span style="float:right">{rupee(row.amount)}</span></div><div class="m">{row.detail}</div><div class="r">{row.reference}</div></div>', unsafe_allow_html=True)
        st.markdown("#### Benford first-digit test")
        fig = go.Figure()
        fig.add_bar(x=ben.first_digit.astype(str), y=ben.expected_pct, name="Benford expected", marker_color=SERIES[3])
        fig.add_bar(x=ben.first_digit.astype(str), y=ben.actual_pct, name="Actual", marker_color=SERIES[0])
        st.plotly_chart(fig_layout(fig, height=280, barmode="group", yaxis_ticksuffix="%"), use_container_width=True)
    with t4:
        tds = s["TDS_Check"]
        st.dataframe(tds, hide_index=True, use_container_width=True,
                     column_config={c: st.column_config.NumberColumn(format="%.0f") for c in ["aggregate_payments", "tds_expected", "tds_deducted", "short_deduction"]})
        short = tds[tds.short_deduction > 0]
        st.plotly_chart(hbar(short.vendor_name.tolist(), short.short_deduction.tolist(), [RED] * len(short), height=200), use_container_width=True)


def page_compliance():
    r = results(); s = r["sheets"]; d = r["data"]
    cal, meetings, resol, actions = s["Compliance_Calendar"], s["Minutes_Meetings"], s["Minutes_Resolutions"], s["Minutes_Actions"]
    st.markdown("## Compliance calendar and minutes analyser")
    c = st.columns(4)
    kpi(c[0], "Overdue", f"{int(cal.status.str.startswith('Overdue').sum())}", "obligations past due")
    kpi(c[1], "Due within 45 days", f"{int(cal.status.str.startswith('Due').sum())}")
    kpi(c[2], "Meetings analysed", f"{len(meetings)}", f"{int((meetings.issues != '').sum())} with notice/quorum issues")
    kpi(c[3], "Action items not complied", f"{int(actions.status.str.startswith('Not').sum())}", f"of {len(actions)}")
    st.write("")
    t1, t2, t3 = st.tabs(["Calendar", "Meetings and resolutions", "Action tracker"])
    with t1:
        def colour(sv):
            return RED if sv.startswith("Overdue") else AMBER if sv.startswith("Due") else GREEN if sv.startswith("Complied") else GREY
        for row in cal.itertuples():
            st.markdown(f'<div class="obs" style="--c:{colour(row.status)}"><div class="t">{row.obligation} {chip(row.status, colour(row.status))} <span class="muted" style="float:right">due {row.due_date:%d-%b-%Y}</span></div><div class="r">{row.authority}</div><div class="m">{row.remarks}</div></div>', unsafe_allow_html=True)
    with t2:
        st.dataframe(meetings.drop(columns=["file"]), hide_index=True, use_container_width=True)
        st.markdown("#### Read and analyse a minutes file")
        name = st.selectbox("Minutes file", list(d.minutes.keys()))
        text = d.minutes[name]
        a, b = st.columns([1, 1])
        a.text_area("Minutes text", text, height=380)
        w = writer()
        with b:
            parsed = parse_minutes(name, text)
            st.markdown(f"**Parsed:** {parsed.kind} · {parsed.meeting_date:%d-%b-%Y} · present {parsed.present}/{parsed.total} · {len(parsed.resolutions)} resolutions · {len(parsed.actions)} actions")
            key = f"minutes_{name}"
            if st.button("Analyse with Claude", disabled=not w.enabled, type="primary", key=key):
                instr, ctx, mt = w.task_spec("minutes", name=name, text=text, parsed={"present": parsed.present, "total": parsed.total, "notice_date": parsed.notice_date, "meeting_date": parsed.meeting_date})
                run_draft(key, w.stream_task(key, instr, ctx, mt), "Claude is reading the minutes...")
            elif key in st.session_state.drafts:
                st.markdown(st.session_state.drafts[key])
            else:
                st.markdown("**Resolutions found**")
                for i, rs in enumerate(parsed.resolutions, 1):
                    st.markdown(f"{i}. {rs}")
        st.markdown("#### All resolutions")
        st.dataframe(resol, hide_index=True, use_container_width=True)
    with t3:
        for row in actions.sort_values("due_date").itertuples():
            colr = RED if row.status.startswith("Not") else GREEN if row.status.startswith("Complied") else AMBER
            due = f"{row.due_date:%d-%b-%Y}" if row.due_date else "-"
            st.markdown(f'<div class="obs" style="--c:{colr}"><div class="t">{row.action} <span class="muted">· {row.owner} · due {due}</span></div><div class="m">{row.status}</div></div>', unsafe_allow_html=True)


def page_tax():
    r = results(); s = r["sheets"]; t = r["tax_summary"]
    st.markdown("## Income-tax computation (AY 2026-27)")
    st.caption("Member receipts excluded on the principle of mutuality; co-operative bank interest deducted under s.80P(2)(d); normal slabs compared with s.115BAD.")
    c = st.columns(4)
    kpi(c[0], "Gross total income", rupee(t["gti"]))
    kpi(c[1], "Deduction u/s 80P(2)(d)", rupee(t["deduction_80p"]))
    kpi(c[2], "Tax (recommended regime)", rupee(t["tax_old"] if t["regime"].startswith("Normal") else t["tax_115bad"]), t["regime"])
    kpi(c[3], "Payable with return", rupee(t["net_payable"] + t["interest_234b"] + t["interest_234c"]), f"incl. 234B {rupee(t['interest_234b'])} · 234C {rupee(t['interest_234c'])}")
    st.write("")
    a, b = st.columns([1.4, 1])
    with a:
        comp = s["Tax_Computation"].copy()
        comp["amount"] = comp.amount.apply(lambda v: "" if pd.isna(v) else rupee(v))
        st.dataframe(comp, hide_index=True, use_container_width=True, height=620)
    with b:
        fig = go.Figure(go.Bar(x=["Normal provisions + 80P", "s.115BAD (22%)"], y=[t["tax_old"], t["tax_115bad"]], marker_color=[SERIES[2], SERIES[1]], text=[rupee(t["tax_old"]), rupee(t["tax_115bad"])], textposition="outside", cliponaxis=False))
        st.plotly_chart(fig_layout(fig, height=300, title="Regime comparison"), use_container_width=True)
        w = writer()
        if st.button("Draft tax note with Claude", disabled=not w.enabled, type="primary"):
            instr, ctx, mt = w.task_spec("tax_note", summary=t)
            run_draft("tax_note", w.stream_task("tax_note", instr, ctx, mt), "Claude is reading the tax computation...")
        elif "tax_note" in st.session_state.drafts:
            st.markdown(st.session_state.drafts["tax_note"])
        else:
            st.markdown(w.tax_note(t))


def page_ai():
    r = results(); s = r["sheets"]; w = writer()
    st.markdown("## AI drafting studio")
    if w.enabled:
        st.success(f"Connected · model {w.model} · key held in this session only. Every prompt and response is logged below.")
    else:
        st.warning("No API key entered. Enter your Anthropic API key in **Data & settings** to draft with Claude. Offline templates remain available.")
    tabs = st.tabs(["Audit observations", "Management letter", "Governance summary", "Ask the auditor", "Prompt log"])
    specs = [("observations", "audit observations section", dict(findings=r["findings"])),
             ("management_letter", "management letter", dict(findings=r["findings"], as_of=r["as_of"])),
             ("governance", "governance summary", dict(meetings=s["Minutes_Meetings"], actions=s["Minutes_Actions"]))]
    templates = {"observations": lambda: w.audit_observations(r["findings"]), "management_letter": lambda: w.management_letter(r["findings"], r["as_of"]),
                 "governance": lambda: w.minutes_summary(s["Minutes_Meetings"], s["Minutes_Actions"])}
    for tab, (kind, label, kw) in zip(tabs[:3], specs):
        with tab:
            c1, c2, c3 = st.columns([1, 1, 3])
            if c1.button("Draft with Claude", key=kind + "_ai", disabled=not w.enabled, type="primary"):
                instr, ctx, mt = w.task_spec(kind, **kw)
                run_draft(kind, w.stream_task(kind, instr, ctx, mt))
            if c2.button("Offline template", key=kind + "_tpl"):
                st.session_state.drafts[kind] = templates[kind]()
            if kind in st.session_state.drafts:
                st.text_area(label.title(), st.session_state.drafts[kind], height=480, key=kind + "_txt")
                c3.download_button("Download", st.session_state.drafts[kind], file_name=f"{kind}.txt", key=kind + "_dl")
            else:
                st.caption(f"Generate the {label} from the {len(r['findings'])} structured findings. The model receives only the JSON context shown in the prompt log.")
    with tabs[3]:
        st.caption("Ask questions about this audit. Answers are grounded in the findings, schedules and tax computation; the model is told to say when the context does not contain the answer.")
        f = r["findings_df"]; ledger = s["Member_Ledger"]; cal = s["Compliance_Calendar"]
        context = {"findings": f.to_dict(orient="records"), "tax": r["tax_summary"],
                   "calendar": cal[["obligation", "due_date", "status"]].to_dict(orient="records"),
                   "defaulters": r["defaulters"][["flat_no", "closing_balance", "months_of_arrears", "status"]].to_dict(orient="records"),
                   "totals": {"billed": float(ledger.billed_fy.sum()), "collected": float(ledger.received_fy.sum()), "closing_dues": float(ledger.closing_balance.clip(lower=0).sum())},
                   "fund_tests": s["Fund_Compliance"].to_dict(orient="records"), "tds": s["TDS_Check"].to_dict(orient="records")}
        for m in st.session_state.chat:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
        if q := st.chat_input("e.g. Which findings should go to the General Body first?", disabled=not w.enabled):
            st.session_state.chat.append({"role": "user", "content": q})
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Thinking..."):
                        ans = st.write_stream(w.chat_stream(q, st.session_state.chat[:-1], context))
                except Exception as exc:
                    st.error(f"Claude request failed: {exc}")
                    st.session_state.chat.pop()
                    ans = None
            if ans:
                st.session_state.chat.append({"role": "assistant", "content": ans})
        if st.session_state.chat and st.button("Clear conversation"):
            st.session_state.chat = []
            st.rerun()
    with tabs[4]:
        if not st.session_state.ai_log:
            st.caption("No AI calls yet in this session.")
        for e in reversed(st.session_state.ai_log):
            with st.expander(f"{e.task} · {e.source}" + (f" · {len(e.unverified_citations)} citation(s) flagged" if e.unverified_citations else "")):
                st.code(e.prompt[:3000], language="text")
                st.markdown(e.response)


PAGES: dict = {}


def page_import():
    ss = st.session_state
    st.markdown("## Import society data")
    st.markdown("Run the audit on a real society. Fill the Excel template, upload it with the minutes, and the tool validates the file before it runs the tests. "
                "Everything stays on this computer; only the JSON context for a draft goes to Claude, and only when you press a draft button.")
    a, b = st.columns([1, 1])
    with a:
        st.markdown("#### 1. Get the template")
        st.download_button("Download blank template (Excel)", build_template(), file_name="CHS_Input_Template.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        st.caption("Nine sheets with the exact headers, two example rows each, and an Instructions sheet. Minutes go in a zip of .txt files, one meeting per file.")
        with st.expander("What each sheet needs"):
            for k, v in SHEET_HELP.items():
                st.markdown(f"**{k}**{'' if k in REQUIRED_SHEETS else ' (optional)'} - {v}")
        with st.expander("Where the data usually comes from"):
            st.markdown("- **Members, bills, receipts**: export the member ledger and bill register from the society's accounting or society-management software (Tally, ApnaComplex, MyGate, SocietyRun...) and paste into the sheets.\n"
                        "- **Bank statement**: download the year's statement as Excel from net banking; keep date, narration, debit, credit, balance.\n"
                        "- **Vendors and expenses**: the payment voucher register and the vendor master from the books.\n"
                        "- **Fund balances and compliance master**: from the audited balance sheet of the previous year, the FD register and the society's statutory file.\n"
                        "- **Minutes**: copy each meeting's minutes into a plain text file.")
    with b:
        st.markdown("#### 2. Upload and validate")
        up = st.file_uploader("Society workbook (filled template)", type=["xlsx"])
        mins = st.file_uploader("Minutes (zip of .txt files, optional)", type=["zip"])
        if up:
            rep = validate_workbook(up.getvalue())
            if rep.summary:
                st.dataframe(pd.DataFrame({"sheet": list(rep.summary), "rows": list(rep.summary.values())}), hide_index=True, use_container_width=True)
            for e in rep.errors:
                st.error(e)
            for w in rep.warnings:
                st.warning(w)
            if rep.ok:
                st.success("Workbook passes validation.")
                if st.button("Run the audit on this data", type="primary"):
                    target = ROOT / "data" / "uploads" / pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                    save_upload(up.getvalue(), mins.getvalue() if mins else None, target)
                    ss.data_dir, ss.data_label = str(target), up.name
                    ss.data_version = ss.get("data_version", 0) + 1
                    ss.drafts, ss.chat = {}, []
                    st.success("Data loaded. Audit tests re-run.")
                    st.rerun()
            else:
                st.info("Fix the errors above and upload again. Warnings do not block the run.")
        st.markdown("#### Or try a mock-up upload")
        st.caption("Loads a second synthetic society (Green Meadows, Pune) exactly as if its workbook and minutes had been uploaded: validation first, then every page re-runs on it.")
        if st.button("Mock-up data upload", key="mockup_btn"):
            rep = validate_workbook((MOCKUP_DIR / "society_data.xlsx").read_bytes())
            ss.mockup_report = rep
            if rep.ok:
                ss.data_dir, ss.data_label = str(MOCKUP_DIR), MOCKUP_LABEL
                ss.data_version = ss.get("data_version", 0) + 1
                ss.drafts, ss.chat = {}, []
                st.rerun()
        if ss.get("mockup_report") is not None and ss.data_label == MOCKUP_LABEL:
            rep = ss.mockup_report
            st.dataframe(pd.DataFrame({"sheet": list(rep.summary), "rows": list(rep.summary.values())}), hide_index=True, use_container_width=True)
            for w in rep.warnings:
                st.warning(w)
            st.success("Mock-up workbook and 13 minutes files validated and loaded. Every page now shows Green Meadows.")
            if st.button("Open the overview", type="primary", key="mockup_go"):
                st.switch_page(PAGES["overview"])
            st.download_button("Download the mock-up workbook", (MOCKUP_DIR / "society_data.xlsx").read_bytes(), file_name="Mockup_Green_Meadows_society_data.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown(f"Current data set: **{ss.data_label}**")
        if ss.data_label != "Sample society (Sunrise Heights, 64 flats)" and st.button("Back to the sample society"):
            ss.data_dir, ss.data_label = str(ROOT / "data" / "raw"), "Sample society (Sunrise Heights, 64 flats)"
            ss.data_version = ss.get("data_version", 0) + 1
            ss.drafts, ss.chat = {}, []
            st.rerun()


def page_settings():
    ss = st.session_state
    st.markdown("## Data & settings")
    a, b = st.columns([1, 1])
    with a:
        st.markdown("#### Anthropic API key")
        if stored_api_key():
            st.caption("A key was loaded from .streamlit/secrets.toml or the ANTHROPIC_API_KEY environment variable. Leave the box as is to keep using it, or paste a different key for this session.")
        key = st.text_input("API key", value=ss.api_key, type="password", help="Held in memory for this browser session only; never written to disk by the app. To avoid re-pasting, put it in .streamlit/secrets.toml (git-ignored) as ANTHROPIC_API_KEY = \"sk-ant-...\".")
        model = st.selectbox("Model", ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"], index=["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"].index(ss.model))
        if st.button("Save AI settings", type="primary"):
            ss.api_key, ss.model = key.strip(), model
            if ss.api_key:
                try:
                    import anthropic
                    anthropic.Anthropic(api_key=ss.api_key).models.retrieve(ss.model)
                    st.success("Key verified. AI drafting is enabled.")
                except Exception as exc:
                    st.error(f"Could not verify the key: {exc}")
            else:
                st.info("AI drafting disabled; offline templates will be used.")
        st.markdown("#### Audit date")
        as_of = st.date_input("As-of date for the compliance calendar", value=ss.as_of)
        if as_of != ss.as_of:
            ss.as_of = as_of
            st.rerun()
    with b:
        st.markdown("#### Firm profile")
        st.caption("The signing partner is named in the header, the sign-off of every draft and the AI system prompt. Saved to data/firm.json.")
        with st.form("firm_form"):
            f1, f2 = st.columns(2)
            name = f1.text_input("Firm name", FIRM.name)
            short_name = f2.text_input("Short name", FIRM.short_name)
            descriptor = f1.text_input("Descriptor", FIRM.descriptor)
            website = f2.text_input("Website", FIRM.website)
            signatory = f2.text_input("Signing partner", FIRM.signatory, placeholder="CA Full Name")
            membership_no = f1.text_input("Membership no.", FIRM.membership_no)
            panel_no = f2.text_input("Co-op audit panel no.", FIRM.panel_no)
            phone = f1.text_input("Phone", FIRM.phone)
            email = f2.text_input("Email", FIRM.email)
            address = st.text_input("Office address", FIRM.address)
            if st.form_submit_button("Save firm profile", type="primary"):
                FIRM.__dict__.update(Firm(name=name.strip() or "Jain Jakhotiya & Associates", short_name=short_name.strip() or "JJAA", descriptor=descriptor.strip(), website=website.strip(),
                                          signatory=signatory.strip(), membership_no=membership_no.strip(), panel_no=panel_no.strip(),
                                          phone=phone.strip(), email=email.strip(), address=address.strip()).__dict__)
                save_firm(FIRM)
                st.success("Firm profile saved.")
                st.rerun()
        st.markdown("Signature block used in drafts:")
        st.code("\n".join(FIRM.signature_block()), language="text")
        st.markdown("#### Society data")
        st.markdown(f"Current data set: **{ss.data_label}** · upload your own on the **Import society data** page.")
        if st.button("Reset to sample society"):
            ss.data_dir, ss.data_label = str(ROOT / "data" / "raw"), "Sample society (Sunrise Heights, 64 flats)"
            ss.data_version = ss.get("data_version", 0) + 1
            ss.drafts, ss.chat = {}, []
            st.rerun()
        st.markdown("#### Downloads")
        r = results()
        drafts = {k: v for k, v in ss.drafts.items()}
        if st.button("Build audit workbook (Excel)"):
            tmp = Path(tempfile.mkdtemp()) / "CHS_Audit_Workbook.xlsx"
            texts = {("Draft_" + k.title().replace("_", " ")): v for k, v in drafts.items()} or {"Draft_Note": "Generate drafts in the AI studio to include them here."}
            write_workbook(tmp, r["sheets"], texts, r["findings_df"])
            ss.workbook_bytes = tmp.read_bytes()
        if ss.get("workbook_bytes"):
            st.download_button("Download workbook", ss.workbook_bytes, file_name="CHS_Audit_Workbook_FY2025-26.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download findings (CSV)", r["findings_df"].to_csv(index=False), file_name="findings.csv", mime="text/csv")
        ctx = {"findings": r["findings_df"], "ledger": r["sheets"]["Member_Ledger"], "calendar": r["sheets"]["Compliance_Calendar"], "gst_summary": r["sheets"]["GST_Summary"],
               "benford": r["sheets"]["Benford"], "monthly": r["monthly"], "tax_summary": r["tax_summary"], "as_of": r["as_of"], "sf_gap": r["sf_gap"]}
        st.download_button("Download static dashboard (HTML)", build_dashboard(ctx), file_name="dashboard.html", mime="text/html")
        sample = ROOT / "data" / "raw" / "society_data.xlsx"
        if sample.exists():
            st.download_button("Download sample input workbook", sample.read_bytes(), file_name="society_data_sample.xlsx")


# --------------------------------------------------------------------------- app
def main():
    st.set_page_config(page_title=f"CHS Audit Assistant · {FIRM.auditor}", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    with st.sidebar:
        who = FIRM.auditor
        initials = "".join(w[0] for w in who.replace("CA ", "").split()[:2]).upper() or "CA"
        st.markdown(f'<div class="brand"><div class="brand-mark">{initials}</div><div><div class="brand-name">{who}</div>'
                    f'<div class="brand-sub">{"Chartered Accountant" if FIRM.signatory else FIRM.descriptor}</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-course">ICAI AICA Level 2 · Batch 100 · Pune</div>', unsafe_allow_html=True)
        st.markdown(f"<small>CHS Audit Assistant · AI-powered statutory audit for co-operative housing societies{' · ' + FIRM.website if FIRM.website else ''}</small>", unsafe_allow_html=True)
        st.markdown("---")
    pages = [
        st.Page(page_overview, title="Overview", icon="📊", default=True),
        st.Page(page_members, title="Member ledger & defaulters", icon="🏠"),
        st.Page(page_gst, title="GST check", icon="🧾"),
        st.Page(page_expenses, title="Funds, bank & expenses", icon="🏦"),
        st.Page(page_compliance, title="Compliance & minutes", icon="📅"),
        st.Page(page_tax, title="Income-tax", icon="🧮"),
        st.Page(page_ai, title="AI drafting studio", icon="✨"),
        st.Page(page_import, title="Import society data", icon="📥"),
        st.Page(page_settings, title="Data & settings", icon="⚙️"),
    ]
    PAGES["overview"] = pages[0]
    pg = st.navigation(pages)
    with st.sidebar:
        st.markdown("---")
        ss = st.session_state
        st.markdown(f"<small>Data: {ss.data_label}<br>Audit date: {ss.as_of:%d %b %Y}<br>AI: {'connected · ' + ss.model if ss.api_key else 'offline templates'}</small>", unsafe_allow_html=True)
    pg.run()


main()
