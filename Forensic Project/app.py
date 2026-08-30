"""
Red Flag Engine — Streamlit Web Application
Forensic accounting fraud-risk engine for Indian statutory and internal audit.
Grounded in ICAI Forensic Accounting Board of Studies material (Ch. 3, 4, 6) and FAIS.
"""
import io
import os
import json
import uuid
import hashlib
import datetime
import traceback

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from engine.ingest import compute_sha256, validate_and_route, UnsupportedFileFormatError
from engine.parse_excel import parse_excel
from engine.parse_pdf import parse_pdf, ScannedPDFError
from engine.normalise import normalise_ledgers
from engine.profile import profile_trial_balance
from engine.derive import derive_financial_statements
from engine.statistical import compute_unsupervised_outliers
from engine.rule_engine import execute_all_rules
from engine.scoring import score_exceptions
from engine.coverage import evaluate_coverage
from engine.custody import record_custody_entry
from reporting.workpaper import generate_excel_workpaper
from reporting.requisition import generate_requisition_pdf
from reporting.hypotheses import build_hypothesis_text

APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Rule, config and lexicon files are resolved by relative path, so the engine must
# run from the project root regardless of where streamlit was invoked.
if os.getcwd() != APP_DIR:
    os.chdir(APP_DIR)
SAMPLE_TB = os.path.join(APP_DIR, "data", "sample", "sample_tb_FY22_FY24.xlsx")
TEMPLATE_TB = os.path.join(APP_DIR, "templates", "trial_balance_template.xlsx")

if not st.runtime.exists():
    import sys
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", os.path.abspath(__file__), "--server.port=8501", "--server.address=0.0.0.0"]
    sys.exit(stcli.main())

st.set_page_config(
    page_title="Red Flag Engine — Forensic Accounting",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# STYLING
# =============================================================================
st.markdown("""
<style>
    :root {
        --navy: #1F497D;
        --navy-dark: #16355A;
        --ink: #1A1D21;
        --muted: #5A6472;
        --line: #DCE3EC;
        --red: #C0392B;
        --amber: #B7791F;
        --green: #1E8449;
    }
    .block-container { padding-top: 2.1rem; padding-bottom: 3rem; max-width: 1500px; }
    header[data-testid="stHeader"] { background: transparent; }

    /* ---------- masthead ---------- */
    .rf-masthead {
        border-bottom: 3px solid var(--navy);
        padding-bottom: 10px; margin-bottom: 6px;
        display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 8px;
    }
    .rf-brand { font-size: 21px; font-weight: 700; color: var(--navy); letter-spacing: -0.2px; }
    .rf-brand span { font-weight: 400; color: var(--muted); font-size: 13px; margin-left: 10px; letter-spacing: 0; }
    .rf-meta { font-size: 11.5px; color: var(--muted); text-align: right; line-height: 1.55; }
    .rf-meta b { color: var(--ink); }

    /* ---------- notice ---------- */
    .rf-notice {
        background: #F7F9FC; border-left: 4px solid var(--navy);
        padding: 9px 14px; font-size: 12px; color: #37414F;
        margin: 12px 0 22px 0; border-radius: 3px; line-height: 1.55;
    }
    .rf-notice b { color: var(--navy); }

    /* ---------- screen title ---------- */
    .rf-h1 { font-size: 23px; font-weight: 700; color: var(--ink); margin: 0 0 2px 0; letter-spacing: -0.3px; }
    .rf-sub { font-size: 13.5px; color: var(--muted); margin-bottom: 20px; line-height: 1.5; }
    .rf-sec { font-size: 12px; font-weight: 700; color: var(--navy); text-transform: uppercase;
              letter-spacing: 0.7px; margin: 26px 0 10px 0; padding-bottom: 5px;
              border-bottom: 1px solid var(--line); }

    /* ---------- score cards ---------- */
    .rf-card { border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px; height: 100%;
               background: #fff; }
    .rf-card-label { font-size: 10.5px; font-weight: 700; color: var(--muted);
                     text-transform: uppercase; letter-spacing: 0.8px; }
    .rf-card-value { font-size: 40px; font-weight: 700; line-height: 1.05; margin: 6px 0 2px 0;
                     font-variant-numeric: tabular-nums; }
    .rf-card-foot { font-size: 11.5px; color: var(--muted); line-height: 1.5; }
    .rf-red   { border-top: 4px solid var(--red);   } .rf-red   .rf-card-value { color: var(--red); }
    .rf-amber { border-top: 4px solid var(--amber); } .rf-amber .rf-card-value { color: var(--amber); }
    .rf-green { border-top: 4px solid var(--green); } .rf-green .rf-card-value { color: var(--green); }
    .rf-navy  { border-top: 4px solid var(--navy);  } .rf-navy  .rf-card-value { color: var(--navy); font-size: 17px; font-weight: 600; margin-top: 10px; }

    /* ---------- severity scale ---------- */
    .rf-scale { height: 7px; border-radius: 4px; margin: 12px 0 5px 0; position: relative;
                background: linear-gradient(90deg,#1E8449 0%,#1E8449 18%,#E9B949 18%,#E9B949 40%,#C0392B 40%,#C0392B 100%); }
    .rf-needle { position: absolute; top: -4px; width: 2px; height: 15px; background: #111; }
    .rf-scale-lbl { display:flex; justify-content:space-between; font-size:10px; color:var(--muted); }

    /* ---------- lead sheet rows ---------- */
    .rf-pill { display:inline-block; font-size:10px; font-weight:700; padding:2px 7px;
               border-radius:3px; letter-spacing:0.5px; margin-right:6px; vertical-align:middle; }
    .rf-pill-red   { background:#FBEAE7; color:var(--red);   border:1px solid #EFC3BC; }
    .rf-pill-amber { background:#FDF5E3; color:var(--amber); border:1px solid #EBD9AC; }
    .rf-pill-green { background:#E8F6EE; color:var(--green); border:1px solid #BFE3CE; }
    .rf-pill-grey  { background:#EEF1F5; color:#4A5568;      border:1px solid #D9E0E9; }

    .rf-kv { font-size: 12.5px; line-height: 1.85; }
    .rf-kv b { color: var(--muted); font-weight: 600; display:inline-block; min-width: 130px; }
    .rf-hyp { background:#F7F9FC; border-left:3px solid var(--navy); padding:10px 14px;
              font-size:12.5px; line-height:1.6; color:#2C3542; border-radius:3px; margin:6px 0; }
    .rf-proc { font-size:12.5px; line-height:1.7; color:#2C3542; }

    /* ---------- sidebar stepper ---------- */
    section[data-testid="stSidebar"] { background: #F7F9FC; border-right: 1px solid var(--line); }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
    .rf-step { font-size:12.5px; padding:6px 10px; border-radius:4px; margin-bottom:3px; line-height:1.4; }
    .rf-step-now  { background:var(--navy); color:#fff; font-weight:700; }
    .rf-step-done { color:var(--green); font-weight:600; }
    .rf-step-todo { color:#9AA5B4; }
    .rf-sb-title { font-size:16px; font-weight:700; color:var(--navy); margin-bottom:0; }
    .rf-sb-cap { font-size:11px; color:var(--muted); margin-bottom:14px; }
    .rf-sb-kv { font-size:11px; color:var(--muted); line-height:1.7; }
    .rf-sb-kv b { color:var(--ink); }

    /* ---------- buttons / tabs ---------- */
    .stButton > button { border-radius: 4px; font-weight: 600; font-size: 13px; }
    .stDownloadButton > button { border-radius: 4px; font-weight: 600; font-size: 13px; width: 100%; }
    button[data-baseweb="tab"] { font-size: 13px; font-weight: 600; }
    div[data-testid="stExpander"] details { border: 1px solid var(--line); border-radius: 5px; }
    div[data-testid="stExpander"] summary { font-size: 13px; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# CACHED PIPELINE  (heavy work runs once, not on every widget interaction)
# =============================================================================
@st.cache_data(show_spinner=False)
def cached_parse(file_bytes: bytes, filename: str, fmt: str) -> pd.DataFrame:
    if fmt == "excel":
        return parse_excel(io.BytesIO(file_bytes))
    return parse_pdf(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def cached_normalise(raw_frames_key: str, _frames) -> pd.DataFrame:
    return normalise_ledgers(pd.concat(_frames, ignore_index=True))


@st.cache_data(show_spinner=False)
def cached_profile(ledgers: pd.DataFrame):
    return profile_trial_balance(ledgers)


@st.cache_data(show_spinner=False)
def cached_analysis(ledgers: pd.DataFrame, params_json: str, gov_json: str, max_per_rule: int):
    params = json.loads(params_json)
    gov = json.loads(gov_json) if gov_json != "null" else None
    derived = derive_financial_statements(ledgers, params=params)
    ml_outliers = compute_unsupervised_outliers(ledgers)
    exceptions_df, executed_rules, skipped_rules = execute_all_rules(ledgers, derived, params=params)
    scoring_res = score_exceptions(
        exceptions_df,
        performance_materiality=params.get("materiality", 500000.0),
        governance_scores=gov,
        ml_outlier_df=ml_outliers,
        executed_rules=executed_rules,
        max_instances_per_rule=max_per_rule,
    )
    return {
        "derived": derived,
        "ml_outliers": ml_outliers,
        "exceptions_df": exceptions_df,
        "executed_rules": executed_rules,
        "skipped_rules": skipped_rules,
        "scoring": scoring_res,
    }


@st.cache_data(show_spinner=False)
def cached_workpaper(_scoring, derived: pd.DataFrame, _cov, _custody, client_name: str, cache_key: str) -> bytes:
    return generate_excel_workpaper(_scoring, derived, _cov, _custody, client_name=client_name)


@st.cache_data(show_spinner=False)
def cached_requisition(_scoring, client_name: str, engagement_ref: str, firm_name: str,
                       operator: str, predication_note: str, cache_key: str) -> bytes:
    return generate_requisition_pdf(
        _scoring, client_name=client_name, engagement_ref=engagement_ref,
        firm_name=firm_name, operator=operator, predication_note=predication_note,
    )


# =============================================================================
# SESSION STATE
# =============================================================================
DEFAULT_ENGAGEMENT = {
    "client_name": "",
    "operator": "",
    "firm_name": "",
    "financial_years": "",
    "materiality": 500000.0,
    "predication_note": "",
    "peer_ratios": {},
    "related_parties": [],
    "prior_adjustments": [],
}

for key, default in [
    ("screen", 1),
    ("run_id", str(uuid.uuid4())),
    ("engagement", dict(DEFAULT_ENGAGEMENT)),
    ("ledgers_df", None),
    ("file_custody_info", []),
    ("governance_scores", None),
    ("analysis_results", None),
    ("custody_entry", None),
    ("data_source_label", ""),
    ("pdf_in_batch", False),
    ("pdf_confirmed", False),
    ("lead_page", 0),
    ("max_per_rule", 15),
    ("exports", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def goto(screen_num: int):
    st.session_state.screen = screen_num
    st.rerun()


def reset_engagement(keep_setup: bool = False):
    st.session_state.run_id = str(uuid.uuid4())
    st.session_state.ledgers_df = None
    st.session_state.file_custody_info = []
    st.session_state.governance_scores = None
    st.session_state.analysis_results = None
    st.session_state.custody_entry = None
    st.session_state.data_source_label = ""
    st.session_state.pdf_in_batch = False
    st.session_state.pdf_confirmed = False
    st.session_state.lead_page = 0
    st.session_state.exports = {}
    if not keep_setup:
        st.session_state.engagement = dict(DEFAULT_ENGAGEMENT)
    st.session_state.screen = 1


def arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Streamlit serialises dataframes through Arrow, which rejects object columns
    holding mixed types (e.g. an 'Observed value' column carrying both floats and
    'DSO: 86d'). Cast every object column to string so tables always render.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))
    out.columns = [str(c) for c in out.columns]
    return out


def fmt_inr(v) -> str:
    try:
        return f"₹{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def flag_pill(flag: str) -> str:
    f = str(flag).upper()
    cls = {"RED": "rf-pill-red", "YELLOW": "rf-pill-amber", "GREEN": "rf-pill-green"}.get(f, "rf-pill-grey")
    return f'<span class="rf-pill {cls}">{f}</span>'


SCREENS = [
    (1, "Engagement Setup"),
    (2, "Upload & Verify"),
    (3, "Governance Assessment"),
    (4, "Findings & Audit Leads"),
    (5, "Export & Requisition"),
]


def screen_reachable(n: int) -> bool:
    if n <= 1:
        return True
    if n == 2:
        return bool(st.session_state.engagement.get("predication_note", "").strip())
    if n == 3:
        return st.session_state.ledgers_df is not None and st.session_state.custody_entry is not None
    if n in (4, 5):
        return st.session_state.analysis_results is not None
    return False


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown('<div class="rf-sb-title">🔍 Red Flag Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="rf-sb-cap">Forensic Accounting & Fraud-Risk Scoring</div>', unsafe_allow_html=True)

    for s_num, s_name in SCREENS:
        cur = st.session_state.screen
        if cur == s_num:
            st.markdown(f'<div class="rf-step rf-step-now">{s_num}. {s_name}</div>', unsafe_allow_html=True)
        elif screen_reachable(s_num):
            if st.button(f"✓ {s_num}. {s_name}" if cur > s_num else f"○ {s_num}. {s_name}",
                         key=f"nav_{s_num}", width="stretch"):
                goto(s_num)
        else:
            st.markdown(f'<div class="rf-step rf-step-todo">○ {s_num}. {s_name}</div>', unsafe_allow_html=True)

    st.markdown("---")
    eng = st.session_state.engagement
    st.markdown(
        f'<div class="rf-sb-kv">'
        f'<b>Client:</b> {eng.get("client_name") or "—"}<br/>'
        f'<b>Materiality:</b> {fmt_inr(eng.get("materiality", 0))}<br/>'
        f'<b>Data:</b> {st.session_state.data_source_label or "not loaded"}<br/>'
        f'<b>Run ID:</b> <code>{st.session_state.run_id[:8]}</code>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    if st.button("↺ Reset Engagement", width="stretch", key="sb_reset"):
        reset_engagement()
        st.rerun()
    st.caption("ICAI FAIS · BOS study material")


# =============================================================================
# MASTHEAD
# =============================================================================
_e = st.session_state.engagement
st.markdown(
    f"""
<div class="rf-masthead">
  <div class="rf-brand">Red Flag Engine <span>Forensic Accounting & Fraud-Risk Analytics</span></div>
  <div class="rf-meta">
    <b>{_e.get('client_name') or 'No engagement'}</b> &nbsp;·&nbsp; Materiality {fmt_inr(_e.get('materiality', 0))}<br/>
    Run <b>{st.session_state.run_id[:8]}</b> &nbsp;·&nbsp; {datetime.date.today().strftime('%d %B %Y')}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="rf-notice">
<b>Professional Standard Notice —</b> Indicators are not evidence. This engine establishes
<i>predication</i> (a reasonable basis for further examination) under ICAI FAIS 130 / SA 240.
It does not conclude that an offence has occurred, and no output may be represented as a finding of fraud.
</div>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# SCREEN 1 — ENGAGEMENT SETUP
# =============================================================================
if st.session_state.screen == 1:
    st.markdown('<div class="rf-h1">Engagement Setup & Predication</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rf-sub">Record the engagement identity, performance materiality and the predication '
        'rationale. Both materiality and the predication note are written immutably into the chain of '
        'custody before any data is ingested.</div>',
        unsafe_allow_html=True,
    )

    eng = st.session_state.engagement

    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown('<div class="rf-sec">Engagement Identity</div>', unsafe_allow_html=True)
        client_name = st.text_input("Client / Entity Name", value=eng["client_name"],
                                    placeholder="e.g. ABC Manufacturing Private Limited")
        firm_name = st.text_input("Audit Firm", value=eng["firm_name"],
                                  placeholder="e.g. Mahesh Chandra & Associates, Chartered Accountants")
        operator = st.text_input("Lead Auditor / Engagement Partner", value=eng["operator"],
                                 placeholder="e.g. CA Adityavikram Bohra (M. No. 193223)")
        fy_label = st.text_input("Financial Years Under Review", value=eng["financial_years"],
                                 placeholder="e.g. FY 2021-22 to FY 2023-24")
        materiality = st.number_input(
            "Performance Materiality (₹)  •  required",
            min_value=1000.0,
            value=float(eng["materiality"]),
            step=50000.0,
            format="%.0f",
            help="Planning materiality. Every monetary exception is weighted as min(1, value ÷ materiality), "
                 "so this directly drives the ranking of audit leads.",
        )

    with c2:
        st.markdown('<div class="rf-sec">Predication</div>', unsafe_allow_html=True)
        predication_note = st.text_area(
            "Predication Note  •  required",
            value=eng["predication_note"],
            placeholder=("State the circumstances giving rise to this review — whistle-blower complaint, "
                         "statutory audit anomaly, banker's stock-audit observation, management representation "
                         "inconsistency, regulatory correspondence, etc."),
            height=232,
            help="Mandatory under ICAI FAIS 130 / SA 240. Recorded in the chain of custody and reproduced "
                 "on the Evidence Requisition List.",
        )

    with st.expander("Optional benchmark parameters — peer ratios, related parties, prior-period adjustments"):
        st.caption("These unlock additional rules. Rules whose inputs are absent are skipped and disclosed, "
                   "never silently dropped.")
        oc1, oc2 = st.columns([1, 1], gap="large")
        with oc1:
            st.markdown("**Related party ledger names** (one per line)")
            rp_text = st.text_area(
                "Related parties", value="\n".join(eng.get("related_parties", [])),
                placeholder="Balaji Enterprises\nRadha Associates\nShreeji Traders",
                height=110, label_visibility="collapsed",
            )
            st.markdown("**Prior-period adjustments** (one per line)")
            pa_text = st.text_area(
                "Prior adjustments", value="\n".join(eng.get("prior_adjustments", [])),
                placeholder="FY23 — Depreciation recomputation ₹12,40,000",
                height=90, label_visibility="collapsed",
            )
        with oc2:
            st.markdown("**Industry peer ratio benchmarks**")
            pr = eng.get("peer_ratios") or {}
            p1, p2 = st.columns(2)
            with p1:
                gp_m = st.number_input("GP margin — mean", value=float(pr.get("gp_margin", {}).get("mean", 0.25)), step=0.01, format="%.3f")
                np_m = st.number_input("NP margin — mean", value=float(pr.get("np_margin", {}).get("mean", 0.08)), step=0.01, format="%.3f")
                at_m = st.number_input("Asset turnover — mean", value=float(pr.get("asset_turnover", {}).get("mean", 1.2)), step=0.1, format="%.2f")
            with p2:
                gp_s = st.number_input("GP margin — std dev", value=float(pr.get("gp_margin", {}).get("std", 0.03)), step=0.01, format="%.3f")
                np_s = st.number_input("NP margin — std dev", value=float(pr.get("np_margin", {}).get("std", 0.02)), step=0.01, format="%.3f")
                at_s = st.number_input("Asset turnover — std dev", value=float(pr.get("asset_turnover", {}).get("std", 0.2)), step=0.05, format="%.2f")

    with st.expander("Analyst tuning — exception suppression threshold"):
        st.session_state.max_per_rule = st.slider(
            "Maximum subjects reported per rule", min_value=5, max_value=100,
            value=int(st.session_state.max_per_rule), step=5,
            help="A rule firing on 120 ledgers is a systemic observation, not 120 leads. Only the highest-scoring "
                 "subjects per rule reach the lead sheet; the remainder are counted, disclosed and exported.",
        )

    is_ready = bool(materiality > 0 and predication_note.strip())

    st.markdown('<div class="rf-sec">Proceed</div>', unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1.1, 1.1, 3])
    with b1:
        if st.button("Continue to Upload  →", type="primary", disabled=not is_ready, width="stretch"):
            st.session_state.engagement.update({
                "client_name": client_name.strip() or "Unnamed Entity",
                "firm_name": firm_name.strip(),
                "operator": operator.strip() or "Forensic Auditor",
                "financial_years": fy_label.strip(),
                "materiality": float(materiality),
                "predication_note": predication_note.strip(),
                "related_parties": [r.strip() for r in rp_text.split("\n") if r.strip()],
                "prior_adjustments": [r.strip() for r in pa_text.split("\n") if r.strip()],
                "peer_ratios": {
                    "gp_margin": {"mean": gp_m, "std": gp_s},
                    "np_margin": {"mean": np_m, "std": np_s},
                    "asset_turnover": {"mean": at_m, "std": at_s},
                },
            })
            goto(2)
    with b2:
        if st.button("Load demo engagement", width="stretch",
                     help="Pre-fills a worked example so you can run the engine end to end immediately."):
            st.session_state.engagement.update({
                "client_name": "ABC Manufacturing Private Limited",
                "firm_name": "Mahesh Chandra & Associates, Chartered Accountants",
                "operator": "Lead Forensic Auditor",
                "financial_years": "FY 2021-22 to FY 2023-24",
                "materiality": 500000.0,
                "predication_note": (
                    "Banker's stock audit for FY 2023-24 reported drawing-power shortfalls inconsistent with "
                    "the audited receivables position, and an anonymous complaint alleged routing of purchases "
                    "through a non-operating vendor. Review commissioned to establish predication."
                ),
                "related_parties": ["Balaji Enterprises", "Radha Associates", "Shreeji Traders"],
                "prior_adjustments": [],
                "peer_ratios": {
                    "gp_margin": {"mean": 0.25, "std": 0.03},
                    "np_margin": {"mean": 0.08, "std": 0.02},
                    "asset_turnover": {"mean": 1.2, "std": 0.2},
                },
            })
            st.rerun()
    with b3:
        if not is_ready:
            st.info("Supply a performance materiality and a predication note to continue.", icon="⚠️")


# =============================================================================
# SCREEN 2 — UPLOAD & VERIFY
# =============================================================================
elif st.session_state.screen == 2:
    st.markdown('<div class="rf-h1">Upload & Data Verification</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rf-sub">Upload three or more financial years of trial balance data. Each file is '
        'SHA-256 hashed on receipt. Arithmetic integrity is verified before any rule is executed.</div>',
        unsafe_allow_html=True,
    )

    src1, src2 = st.columns([2.6, 1], gap="large")

    with src1:
        uploaded_files = st.file_uploader(
            "Trial balance files (.xlsx, .xls, or text-based .pdf)",
            type=["xlsx", "xls", "pdf"],
            accept_multiple_files=True,
            help="Upload one workbook containing all years, or one file per year. CSV/JSON/XML are refused by design.",
        )

    with src2:
        st.markdown('<div class="rf-sec">Or start from</div>', unsafe_allow_html=True)
        if st.button("📊 Load sample trial balance", width="stretch",
                     help="Three-year worked example with planted manipulations."):
            try:
                with open(SAMPLE_TB, "rb") as f:
                    content = f.read()
                raw = cached_parse(content, "sample_tb_FY22_FY24.xlsx", "excel")
                st.session_state.ledgers_df = normalise_ledgers(raw)
                st.session_state.file_custody_info = [{
                    "filename": "sample_tb_FY22_FY24.xlsx",
                    "sha256": compute_sha256(content),
                    "bytes": len(content),
                    "format": "excel",
                }]
                st.session_state.data_source_label = "sample workbook"
                st.session_state.pdf_in_batch = False
                st.session_state.analysis_results = None
                st.rerun()
            except Exception as ex:
                st.error(f"Could not load the sample workbook: {ex}")

        if os.path.exists(TEMPLATE_TB):
            with open(TEMPLATE_TB, "rb") as f:
                st.download_button("📄 Download blank TB template", data=f.read(),
                                   file_name="trial_balance_template.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   width="stretch")

    if uploaded_files:
        parsed_dfs, custody_info, had_pdf = [], [], False
        try:
            with st.spinner("Hashing and parsing uploaded files…"):
                for uf in uploaded_files:
                    fmt = validate_and_route(uf.name)
                    content = uf.getvalue()
                    custody_info.append({
                        "filename": uf.name,
                        "sha256": compute_sha256(content),
                        "bytes": len(content),
                        "format": fmt,
                    })
                    if fmt == "pdf":
                        had_pdf = True
                    parsed_dfs.append(cached_parse(content, uf.name, fmt))

                combined = pd.concat(parsed_dfs, ignore_index=True)
                new_ledgers = normalise_ledgers(combined)

            sig = hashlib.sha256("|".join(sorted(c["sha256"] for c in custody_info)).encode()).hexdigest()
            if st.session_state.get("_upload_sig") != sig:
                st.session_state._upload_sig = sig
                st.session_state.analysis_results = None
                st.session_state.pdf_confirmed = False
            st.session_state.ledgers_df = new_ledgers
            st.session_state.file_custody_info = custody_info
            st.session_state.pdf_in_batch = had_pdf
            st.session_state.data_source_label = f"{len(custody_info)} uploaded file(s)"

        except ScannedPDFError as spe:
            st.error(f"**Scanned PDF rejected.** {spe}", icon="🚫")
            st.session_state.ledgers_df = None
        except UnsupportedFileFormatError as ufe:
            st.error(f"**Unsupported format.** {ufe}", icon="🚫")
            st.session_state.ledgers_df = None
        except Exception as ex:
            st.error(f"**Extraction failed.** {type(ex).__name__}: {ex}", icon="🚫")
            with st.expander("Technical detail"):
                st.code(traceback.format_exc())
            st.session_state.ledgers_df = None

    if st.session_state.ledgers_df is None:
        st.info("Upload trial balance files, or load the sample workbook, to continue.", icon="📥")
    else:
        ledgers = st.session_state.ledgers_df
        profile = cached_profile(ledgers)
        num_years = profile["num_years"]
        fys = profile["financial_years"]

        st.markdown('<div class="rf-sec">Chain of custody — files received</div>', unsafe_allow_html=True)
        cust_df = pd.DataFrame(st.session_state.file_custody_info)
        if not cust_df.empty:
            disp = cust_df.copy()
            disp["bytes"] = disp["bytes"].map(lambda b: f"{b/1024:,.1f} KB")
            disp["sha256"] = disp["sha256"].map(lambda h: h[:32] + "…")
            disp.columns = ["File name", "SHA-256 (truncated)", "Size", "Format"]
            st.dataframe(arrow_safe(disp), width="stretch", hide_index=True)

        st.markdown('<div class="rf-sec">Arithmetic integrity by financial year</div>', unsafe_allow_html=True)
        cols = st.columns(max(len(fys), 1))
        for idx, rep in enumerate(profile["fy_reports"]):
            with cols[idx % len(cols)]:
                balanced = rep["closing_balanced"]
                st.markdown(
                    f"""
<div class="rf-card {'rf-green' if balanced else 'rf-red'}">
  <div class="rf-card-label">{rep['fy']} — {rep['ledger_count']} ledgers</div>
  <div class="rf-card-value" style="font-size:19px; margin-top:8px;">
    {'Dr = Cr' if balanced else 'Unbalanced'}
  </div>
  <div class="rf-card-foot">
    Σ Debits {fmt_inr(rep['closing_dr_sum'])}<br/>
    Σ Credits {fmt_inr(rep['closing_cr_sum'])}<br/>
    Difference <b>{fmt_inr(rep['closing_difference'])}</b><br/>
    Opening balances: {'present' if rep['has_opening_balances'] else 'missing'}<br/>
    Unclassified: {rep['unclassified_count']} · Nil-balance: {rep['zero_balance_count']}
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )

        if not profile["overall_closing_balanced"]:
            st.warning(
                "One or more years do not balance. The engine will still run, but arithmetic "
                "differences are themselves a reportable condition — confirm the extraction before proceeding.",
                icon="⚠️",
            )

        st.markdown('<div class="rf-sec">Extracted ledgers</div>', unsafe_allow_html=True)
        st.caption(f"{len(ledgers):,} rows across {num_years} year(s) · "
                   f"{ledgers['ledger_name'].nunique():,} distinct ledgers. Edit inline if the extraction "
                   f"needs correction; edits flow into the analysis.")
        edited_df = st.data_editor(ledgers, height=300, width="stretch",
                                   num_rows="fixed", key="tb_editor")
        if not edited_df.equals(ledgers):
            st.session_state.ledgers_df = edited_df
            st.session_state.analysis_results = None

        pdf_ok = True
        if st.session_state.pdf_in_batch:
            st.markdown('<div class="rf-sec">Human verification gate</div>', unsafe_allow_html=True)
            st.warning("One or more files were extracted from PDF. PDF table extraction is not authoritative.", icon="⚠️")
            pdf_ok = st.checkbox("I have verified the extracted figures against the source document.",
                                 value=st.session_state.pdf_confirmed, key="pdf_conf_box")
            st.session_state.pdf_confirmed = pdf_ok

        st.markdown('<div class="rf-sec">Coverage gate</div>', unsafe_allow_html=True)
        if num_years < 3:
            st.error(
                f"**Found {num_years} financial year(s). This engine requires 3.** Longitudinal analysis — "
                f"multi-year trend rules, Beneish M-Score, Altman Z\"-Score and circular-trading persistence — "
                f"cannot be evaluated on fewer than three comparable years. Upload the missing year to continue.",
                icon="🚫",
            )
        else:
            cov = evaluate_coverage(num_years, len(ledgers), profile["has_all_opening_balances"],
                                    st.session_state.engagement)
            st.success(
                f"**{cov['available_count']} of {cov['total_implemented']} implemented forensic methods are ready.** "
                f"{cov['total_declared']} further methods are declared but blocked pending transaction-level data.",
                icon="✅",
            )
            with st.expander("Method-by-method readiness"):
                st.dataframe(arrow_safe(pd.DataFrame(cov["implemented"])), width="stretch", hide_index=True)
                st.dataframe(arrow_safe(pd.DataFrame(cov["not_implemented"])), width="stretch", hide_index=True)

            n1, n2, n3 = st.columns([1.1, 1.1, 3])
            with n1:
                if st.button("←  Back to Setup", width="stretch"):
                    goto(1)
            with n2:
                if st.button("Proceed to Governance  →", type="primary",
                             disabled=not pdf_ok, width="stretch"):
                    st.session_state.custody_entry = record_custody_entry(
                        run_id=st.session_state.run_id,
                        operator=st.session_state.engagement["operator"],
                        predication_note=st.session_state.engagement["predication_note"],
                        files=st.session_state.file_custody_info,
                        parameters={
                            "performance_materiality": st.session_state.engagement["materiality"],
                            "firm_name": st.session_state.engagement.get("firm_name", ""),
                            "client_name": st.session_state.engagement["client_name"],
                            "financial_years": fys,
                            "max_instances_per_rule": st.session_state.max_per_rule,
                        },
                        confirmations=[{
                            "screen": "upload_verify",
                            "pdf_extraction_confirmed": bool(pdf_ok) if st.session_state.pdf_in_batch else "n/a",
                            "arithmetic_balanced": profile["overall_closing_balanced"],
                            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }],
                    )
                    goto(3)


# =============================================================================
# SCREEN 3 — GOVERNANCE QUESTIONNAIRE
# =============================================================================
elif st.session_state.screen == 3:
    st.markdown('<div class="rf-h1">Governance & Qualitative Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rf-sub">Fifteen fraud-risk factors drawn from ICAI FAIS Chapter 6.1.3 and SA 240 Appendix 1. '
        'The result applies a documented ±15% overlay to the entity risk score — it never creates or removes a finding.</div>',
        unsafe_allow_html=True,
    )

    QUESTIONS = [
        ("q1", "Management commits to aggressive or unrealistic forecasts to lenders or analysts"),
        ("q2", "Blurring between promoters' personal and business transactions"),
        ("q3", "Significant part of management compensation tied to reported results"),
        ("q4", "Disputes among shareholders in this closely held entity"),
        ("q5", "Organisational structure complex or unstable relative to entity size"),
        ("q6", "High turnover in accounting, internal audit or IT staff"),
        ("q7", "Strained relationship with the current or previous statutory auditor"),
        ("q8", "Management has failed to remediate known control deficiencies on time"),
        ("q9", "Known history of alleged regulatory or securities-law violations"),
        ("q10", "Excessive management interest in the share price or earnings trend"),
        ("q11", "Entity highly vulnerable to rapid technological or market change"),
        ("q12", "Entity under pressure from declining margins or market saturation"),
        ("q13", "Growth or profitability unusual relative to industry peers"),
        ("q14", "Entity dominates its market enough to dictate non-arm's-length terms"),
        ("q15", "Significant pressure from a pending transaction or contract award"),
    ]

    q1c, q2c, q3c = st.columns([1, 1, 1.4])
    with q1c:
        if st.button("Set all to “No”", width="stretch"):
            for qid, _ in QUESTIONS:
                st.session_state[qid] = 0
            st.rerun()
    with q2c:
        if st.button("Set all to “Partly”", width="stretch"):
            for qid, _ in QUESTIONS:
                st.session_state[qid] = 1
            st.rerun()

    st.markdown('<div class="rf-sec">Fraud risk factors</div>', unsafe_allow_html=True)
    scores = {}
    left, right = st.columns(2, gap="large")
    for idx, (qid, qtext) in enumerate(QUESTIONS):
        with (left if idx < 8 else right):
            scores[qid] = st.radio(
                f"**{idx + 1}.** {qtext}",
                options=[0, 1, 2],
                format_func=lambda x: {0: "No", 1: "Partly", 2: "Yes"}[x],
                horizontal=True,
                key=qid,
            )

    gov_sum = sum(scores.values())
    factor = 0.85 + 0.30 * (gov_sum / 30)
    st.markdown('<div class="rf-sec">Assessment result</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns([1, 1, 2])
    m1.metric("Governance score", f"{gov_sum} / 30")
    m2.metric("Overlay factor", f"×{factor:.3f}")
    m3.caption("Overlay is bounded to ×0.85 – ×1.15. A governance score of 15/30 is neutral. "
               "Skipping the questionnaire records 'not assessed' and applies no overlay.")

    st.markdown('<div class="rf-sec">Run the engine</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1.4, 1.6, 2.2])

    def _run_analysis(gov):
        params = dict(st.session_state.engagement)
        with st.spinner("Deriving statements, executing 44 rules and scoring exceptions…"):
            st.session_state.analysis_results = cached_analysis(
                st.session_state.ledgers_df,
                json.dumps(params, default=str, sort_keys=True),
                json.dumps(gov, sort_keys=True) if gov else "null",
                int(st.session_state.max_per_rule),
            )
        st.session_state.governance_scores = gov
        st.session_state.exports = {}
        st.session_state.lead_page = 0

    with r1:
        if st.button("← Back to Upload", width="stretch"):
            goto(2)
    with r2:
        if st.button("Run Full Forensic Analysis  →", type="primary", width="stretch"):
            _run_analysis(scores)
            goto(4)
    with r3:
        if st.button("Skip — record “not assessed”", width="stretch"):
            _run_analysis(None)
            goto(4)


# =============================================================================
# SCREEN 4 — FINDINGS & AUDIT LEADS
# =============================================================================
elif st.session_state.screen == 4:
    st.markdown('<div class="rf-h1">Forensic Findings & Audit Leads</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rf-sub">Exceptions are de-duplicated across years, ranked, and grouped into an audit '
        'lead sheet — one row per ledger, drilling down to every rule that fired against it.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.analysis_results is None:
        st.warning("No analysis in this session. Return to the Governance screen and run the engine.", icon="⚠️")
        if st.button("← Back to Governance"):
            goto(3)
    else:
        results = st.session_state.analysis_results
        scoring = results["scoring"]
        leads_df = scoring["scored_exceptions"]
        rollup_ledger = scoring["rollup_by_ledger"]
        stats = scoring["stats"]
        bucket = scoring["bucket"]
        score_val = scoring["entity_score"]

        card_cls = {"RED": "rf-red", "YELLOW": "rf-amber", "GREEN": "rf-green"}[bucket]
        needle = min(max(score_val, 0), 100)

        s1, s2, s3 = st.columns([1.15, 1.15, 2], gap="medium")
        with s1:
            st.markdown(
                f"""
<div class="rf-card {card_cls}">
  <div class="rf-card-label">Entity Risk Score</div>
  <div class="rf-card-value">{score_val:.1f}<span style="font-size:16px;color:#8792A2;"> / 100</span></div>
  <div class="rf-card-foot"><b>{bucket}</b> classification</div>
  <div class="rf-scale"><div class="rf-needle" style="left:{needle}%;"></div></div>
  <div class="rf-scale-lbl"><span>0 Green</span><span>18</span><span>40</span><span>100 Red</span></div>
</div>
""",
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"""
<div class="rf-card rf-green">
  <div class="rf-card-label">Green Flag Score</div>
  <div class="rf-card-value">{scoring['green_score']:.1f}<span style="font-size:16px;color:#8792A2;"> / 100</span></div>
  <div class="rf-card-foot">
    Positive indicators / control moats.<br/>
    <b>Never netted</b> against the risk score.
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                f"""
<div class="rf-card rf-navy">
  <div class="rf-card-label">Recommended Audit Action</div>
  <div class="rf-card-value">{scoring['bucket_action']}</div>
  <div class="rf-card-foot" style="margin-top:10px;">
    <b>{stats['distinct_rules_fired']}</b> of {len(results['executed_rules'])} executed rules fired ·
    <b>{stats['distinct_subjects']}</b> distinct subjects<br/>
    {stats['raw_instances']:,} raw instances → {stats['after_dedup']:,} de-duplicated →
    <b>{stats['retained']:,} leads</b> ({stats['suppressed']:,} suppressed as systemic)<br/>
    Governance: <b>{scoring['governance_status']}</b> (overlay ×{scoring['governance_factor']}) ·
    {len(results['skipped_rules'])} rule{'s' if len(results['skipped_rules']) != 1 else ''} skipped
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        with st.expander("How this score was computed"):
            st.markdown(
                f"""
The entity risk score is the **weighted proportion of the executed rule battery that fired**, scaled by
monetary materiality and pervasiveness:

```
entity_score = 100 × Σ(weight × confidence × materiality × pervasiveness)  ÷  Σ(weight × confidence)
             = 100 × {scoring['raw_weighted_sum']} ÷ {scoring['score_denominator']}
             = {scoring['entity_score_pre_governance']}   (before governance overlay)
             × {scoring['governance_factor']}             (governance overlay)
             = {scoring['entity_score']}
```

* **materiality** = min(1, exception value ÷ performance materiality of {fmt_inr(st.session_state.engagement['materiality'])});
  structural (non-monetary) exceptions carry a fixed 0.5.
* **pervasiveness** ∈ [0.70, 1.00] — a rule hitting many distinct ledgers weighs more than one isolated hit.
* Buckets: **≥ 40 RED**, **18 – 40 YELLOW**, **< 18 GREEN**.

Because the score is a bounded proportion, it is comparable between engagements and between years.
                """
            )

        # ---------------- filters ----------------
        st.markdown('<div class="rf-sec">Filters</div>', unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns([1.1, 1.4, 1.4, 1.6])
        with f1:
            sev = st.multiselect("Severity", ["RED", "YELLOW", "GREEN"],
                                 default=["RED", "YELLOW"], key="f_sev")
        with f2:
            mods = sorted(leads_df["module"].dropna().unique().tolist()) if not leads_df.empty else []
            mod_sel = st.multiselect("Module", mods, default=mods, key="f_mod")
        with f3:
            rules_avail = sorted(leads_df["rule_id"].unique().tolist()) if not leads_df.empty else []
            rule_sel = st.multiselect("Rule", rules_avail, default=[], key="f_rule",
                                      help="Leave empty for all rules.")
        with f4:
            query = st.text_input("Search ledger or narrative", key="f_q",
                                  placeholder="Suspense, Ravi Trading, receivable…")

        fdf = leads_df.copy()
        if not fdf.empty:
            if sev:
                fdf = fdf[fdf["flag"].str.upper().isin(sev)]
            if mod_sel:
                fdf = fdf[fdf["module"].isin(mod_sel)]
            if rule_sel:
                fdf = fdf[fdf["rule_id"].isin(rule_sel)]
            if query:
                q = query.strip()
                fdf = fdf[
                    fdf["subject"].astype(str).str.contains(q, case=False, na=False)
                    | fdf["detail"].astype(str).str.contains(q, case=False, na=False)
                    | fdf["rule_name"].astype(str).str.contains(q, case=False, na=False)
                ]

        tabs = st.tabs([
            "📋 Audit Lead Sheet",
            "⚖️ Rule Contribution Register",
            "🏢 By Module",
            "📅 By Year",
            "📈 Ledger Trends",
            "🧾 Coverage, Skipped & Suppressed",
        ])

        # ---------------- TAB 1: grouped lead sheet ----------------
        with tabs[0]:
            if fdf.empty:
                st.info("No exceptions match the active filters.", icon="🔎")
            else:
                subj_order = (
                    fdf.groupby("subject")
                    .agg(total=("flag_score", "sum"), worst=("flag_score", "max"),
                         n=("rule_id", "count"), ml=("ml_outlier_score", "max"))
                    .reset_index()
                    .sort_values(["total", "worst", "ml"], ascending=False)
                    .reset_index(drop=True)
                )

                PAGE = 20
                total_pages = max(1, int(np.ceil(len(subj_order) / PAGE)))
                st.session_state.lead_page = min(st.session_state.lead_page, total_pages - 1)

                h1, h2, h3 = st.columns([2.6, 1, 1])
                with h1:
                    st.caption(
                        f"**{len(subj_order):,} ledgers** carrying **{len(fdf):,} findings** · "
                        f"page {st.session_state.lead_page + 1} of {total_pages}"
                    )
                with h2:
                    if st.button("← Previous", width="stretch",
                                 disabled=st.session_state.lead_page == 0, key="pg_prev"):
                        st.session_state.lead_page -= 1
                        st.rerun()
                with h3:
                    if st.button("Next →", width="stretch",
                                 disabled=st.session_state.lead_page >= total_pages - 1, key="pg_next"):
                        st.session_state.lead_page += 1
                        st.rerun()

                start = st.session_state.lead_page * PAGE
                page_subjects = subj_order.iloc[start:start + PAGE]

                for pos, srow in page_subjects.iterrows():
                    subject = srow["subject"]
                    sub_findings = fdf[fdf["subject"] == subject].sort_values("flag_score", ascending=False)
                    worst_flag = ("RED" if (sub_findings["flag"].str.lower() == "red").any()
                                  else ("YELLOW" if (sub_findings["flag"].str.lower() == "yellow").any() else "GREEN"))
                    icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[worst_flag]
                    rule_ids = ", ".join(sub_findings["rule_id"].unique())
                    label = (f"{icon}  {subject}   —   {int(srow['n'])} finding(s) · "
                             f"aggregate score {srow['total']:.2f}   [{rule_ids}]")

                    with st.expander(label, expanded=(start + (pos - page_subjects.index[0]) < 2)):
                        for _, row in sub_findings.iterrows():
                            st.markdown(
                                f"{flag_pill(row['flag'])} **[{row['rule_id']}] {row['rule_name']}** "
                                f"&nbsp;&nbsp;<span style='color:#5A6472;font-size:12px;'>score "
                                f"{row['flag_score']:.2f}</span>",
                                unsafe_allow_html=True,
                            )
                            d1, d2 = st.columns([1, 1], gap="large")
                            with d1:
                                st.markdown(
                                    f'<div class="rf-kv">'
                                    f'<b>Year(s)</b> {row.get("fy_span", row.get("fy", "—"))}<br/>'
                                    f'<b>Recurrence</b> {int(row.get("occurrences", 1))} year-instance(s)<br/>'
                                    f'<b>Observed</b> {row["observed_value"]}<br/>'
                                    f'<b>Threshold</b> {row["threshold_value"]}<br/>'
                                    f'<b>Materiality factor</b> {row.get("materiality_factor", "—")}'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )
                            with d2:
                                st.markdown(
                                    f'<div class="rf-kv">'
                                    f'<b>ICAI grounding</b> {row.get("source", "—")}<br/>'
                                    f'<b>Fraud tree branch</b> {row.get("branch", "—")}<br/>'
                                    f'<b>Scheme</b> {row.get("scheme", "—")}<br/>'
                                    f'<b>Weight × confidence</b> {row.get("weight", 3)} × {row.get("confidence", 1.0)}<br/>'
                                    f'<b>ML outlier score</b> {row.get("ml_outlier_score", 0):.3f}'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown(f'<div class="rf-kv" style="margin-top:6px;"><b>Detail</b> {row["detail"]}</div>',
                                        unsafe_allow_html=True)
                            st.markdown(f'<div class="rf-hyp"><b>Hypothesis —</b> {build_hypothesis_text(row)}</div>',
                                        unsafe_allow_html=True)
                            proc = row.get("procedure", [])
                            if isinstance(proc, (list, tuple)) and len(proc):
                                items = "".join(f"<li>{p}</li>" for p in proc)
                                st.markdown(
                                    f'<div class="rf-proc"><b>Suggested substantive procedures</b>'
                                    f'<ul style="margin:4px 0 0 18px;">{items}</ul></div>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown("<hr style='margin:14px 0;border:none;border-top:1px solid #E7ECF3;'>",
                                        unsafe_allow_html=True)

                st.markdown('<div class="rf-sec">Lead sheet as a table</div>', unsafe_allow_html=True)
                st.caption("Sortable and copyable — the same leads in flat form.")
                flat = fdf[["rule_id", "rule_name", "module", "flag", "subject", "fy_span",
                            "occurrences", "observed_value", "threshold_value", "flag_score", "detail"]].copy()
                flat.columns = ["Rule", "Rule name", "Module", "Flag", "Subject / ledger", "Year(s)",
                                "Occurrences", "Observed", "Threshold", "Score", "Detail"]
                st.dataframe(arrow_safe(flat), width="stretch", hide_index=True, height=340)
                st.download_button(
                    "⬇ Download this filtered lead sheet (.csv)",
                    data=flat.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"Audit_Lead_Sheet_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv", key="dl_leads_csv",
                )

        # ---------------- TAB 2: rule contributions ----------------
        with tabs[1]:
            st.caption("Every fired rule's contribution to the entity risk score, and the maximum it could "
                       "have contributed. This is the audit trail behind the headline number.")
            contrib = scoring["rule_contributions"].copy()
            if contrib.empty:
                st.info("No rules fired.")
            else:
                contrib["utilisation %"] = (100 * contrib["contribution"] / contrib["max_possible"]).round(1)
                st.dataframe(arrow_safe(contrib), width="stretch", hide_index=True, height=460)
                top = contrib.head(15).sort_values("contribution")
                fig = px.bar(top, x="contribution", y="rule_id", orientation="h",
                             color="flag",
                             color_discrete_map={"RED": "#C0392B", "YELLOW": "#B7791F", "GREEN": "#1E8449"},
                             hover_data=["rule_name", "subjects_hit", "materiality_factor"],
                             labels={"contribution": "Contribution to entity score", "rule_id": ""})
                fig.update_layout(height=440, margin=dict(l=10, r=10, t=30, b=10),
                                  plot_bgcolor="#FFFFFF", legend_title_text="")
                st.plotly_chart(fig, width="stretch")

        # ---------------- TAB 3: by module ----------------
        with tabs[2]:
            rg = scoring["rollup_by_group"]
            st.dataframe(arrow_safe(rg), width="stretch", hide_index=True)
            if not rg.empty:
                fig = px.bar(rg, x="module", y="total_score", color="flag", barmode="group",
                             color_discrete_map={"red": "#C0392B", "yellow": "#B7791F", "green": "#1E8449",
                                                 "RED": "#C0392B", "YELLOW": "#B7791F", "GREEN": "#1E8449"},
                             labels={"total_score": "Aggregate flag score", "module": "Module"})
                fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="#FFFFFF")
                st.plotly_chart(fig, width="stretch")
            st.caption("TB = trial-balance structure · LG = ledger behaviour · FS = financial-statement "
                       "analytics · MS = published forensic models")

        # ---------------- TAB 4: by year ----------------
        with tabs[3]:
            ry = scoring["rollup_by_year"]
            st.dataframe(arrow_safe(ry), width="stretch", hide_index=True)
            if not ry.empty:
                fig = go.Figure()
                fig.add_bar(x=ry["fy"], y=ry["flags_count"], name="Raw exception instances",
                            marker_color="#1F497D")
                fig.add_trace(go.Scatter(x=ry["fy"], y=ry["total_score"], name="Aggregate score",
                                         yaxis="y2", mode="lines+markers", line=dict(color="#C0392B", width=3)))
                fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="#FFFFFF",
                                  yaxis=dict(title="Instances"),
                                  yaxis2=dict(title="Score", overlaying="y", side="right"),
                                  legend=dict(orientation="h", y=1.12))
                st.plotly_chart(fig, width="stretch")

        # ---------------- TAB 5: trends ----------------
        with tabs[4]:
            ledgers_raw = st.session_state.ledgers_df
            candidates = rollup_ledger["subject"].tolist() if not rollup_ledger.empty else []
            default_sel = candidates[:4]
            picked = st.multiselect("Ledgers to chart", candidates, default=default_sel,
                                    help="Defaults to the four highest-scoring ledgers.")
            if not picked:
                st.info("Select one or more ledgers to plot their three-year movement.")
            else:
                sub = ledgers_raw[ledgers_raw["ledger_name"].isin(picked)].sort_values(["ledger_name", "fy"])
                if sub.empty:
                    st.info("No trial-balance rows matched the selected ledgers.")
                else:
                    fig = px.line(sub, x="fy", y="closing_net", color="ledger_name", markers=True,
                                  labels={"closing_net": "Closing balance (₹)", "fy": "Financial year",
                                          "ledger_name": "Ledger"})
                    fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10),
                                      plot_bgcolor="#FFFFFF", legend=dict(orientation="h", y=-0.2))
                    st.plotly_chart(fig, width="stretch")

                    fig2 = px.bar(sub, x="fy", y="turnover_total", color="ledger_name", barmode="group",
                                  labels={"turnover_total": "Total turnover (₹)", "fy": "Financial year",
                                          "ledger_name": "Ledger"})
                    fig2.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10),
                                       plot_bgcolor="#FFFFFF", legend=dict(orientation="h", y=-0.2))
                    st.plotly_chart(fig2, width="stretch")

        # ---------------- TAB 6: coverage / skipped / suppressed ----------------
        with tabs[5]:
            st.markdown('<div class="rf-sec">Rules skipped, with stated reasons</div>', unsafe_allow_html=True)
            st.caption("Under ICAI documentation principles a skipped rule is disclosed, never silently dropped.")
            if results["skipped_rules"]:
                st.dataframe(arrow_safe(pd.DataFrame(results["skipped_rules"])), width="stretch", hide_index=True)
            else:
                st.success("Every rule in the battery executed.", icon="✅")

            st.markdown('<div class="rf-sec">Suppressed as systemic</div>', unsafe_allow_html=True)
            supp_sum = scoring.get("suppression_summary", pd.DataFrame())
            if supp_sum is not None and not supp_sum.empty:
                st.caption(
                    f"{stats['suppressed']:,} further subject-level hits fell below the top "
                    f"{stats['max_instances_per_rule']} for their rule. They are exported in full to the "
                    f"working paper's 'Suppressed' sheet and should be read as systemic conditions."
                )
                st.dataframe(arrow_safe(supp_sum), width="stretch", hide_index=True)
                with st.expander("Full suppressed register"):
                    supp = scoring["suppressed_exceptions"]
                    st.dataframe(
                        arrow_safe(supp[["rule_id", "rule_name", "flag", "subject",
                                         "fy_span", "flag_score", "detail"]]),
                        width="stretch", hide_index=True, height=380,
                    )
            else:
                st.info("Nothing suppressed — every de-duplicated finding is on the lead sheet.")

            st.markdown('<div class="rf-sec">Derived financial statements</div>', unsafe_allow_html=True)
            st.caption("Balance sheet, profit & loss and indirect cash flow derived from the trial balance "
                       "and mapped to Schedule III groupings.")
            _der_t = results["derived"].set_index("fy").T.reset_index()
            _der_t = _der_t.rename(columns={"index": "Line item"})
            st.dataframe(arrow_safe(_der_t), width="stretch", hide_index=True, height=560)

        st.markdown('<div class="rf-sec">Proceed</div>', unsafe_allow_html=True)
        n1, n2, n3 = st.columns([1.2, 1.6, 3])
        with n1:
            if st.button("← Back to Governance", width="stretch"):
                goto(3)
        with n2:
            if st.button("Proceed to Export & Requisition  →", type="primary", width="stretch"):
                goto(5)


# =============================================================================
# SCREEN 5 — EXPORT & REQUISITION
# =============================================================================
elif st.session_state.screen == 5:
    st.markdown('<div class="rf-h1">Working Paper Export & Evidence Requisition</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rf-sub">Generate the multi-sheet Excel working paper, the client-addressed Evidence '
        'Requisition List, and the signed chain-of-custody record.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.analysis_results is None:
        st.warning("No analysis in this session.", icon="⚠️")
        if st.button("← Back to Governance"):
            goto(3)
    else:
        results = st.session_state.analysis_results
        scoring = results["scoring"]
        derived = results["derived"]
        eng = st.session_state.engagement
        custody_entry = st.session_state.custody_entry or {}
        ledgers = st.session_state.ledgers_df
        profile = cached_profile(ledgers)

        cov = evaluate_coverage(
            profile["num_years"], len(ledgers),
            profile["has_all_opening_balances"], eng,
        )

        safe_client = "".join(ch if ch.isalnum() or ch in " -_" else "" for ch in eng["client_name"]).strip().replace(" ", "_") or "Engagement"
        today = datetime.date.today().isoformat()
        cache_key = f"{st.session_state.run_id}|{scoring['entity_score']}|{len(scoring['scored_exceptions'])}"

        st.markdown('<div class="rf-sec">Engagement summary</div>', unsafe_allow_html=True)
        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("Entity risk score", f"{scoring['entity_score']:.1f} / 100", scoring["bucket"])
        sm2.metric("Audit leads", f"{scoring['stats']['retained']:,}")
        sm3.metric("Rules fired", f"{scoring['stats']['distinct_rules_fired']} / {len(results['executed_rules'])}")
        sm4.metric("Methods available", f"{cov['available_count']} / {cov['total_implemented']}")

        st.markdown('<div class="rf-sec">Deliverables</div>', unsafe_allow_html=True)
        d1, d2, d3 = st.columns(3, gap="large")

        with d1:
            st.markdown("##### 📊 Excel Working Paper")
            st.caption("Summary, exceptions by module (TB / LG / FS / MS), suppressed register, forensic model "
                       "outputs, derived statements, hypothesis register with Proved / Disproved / Not-Proved "
                       "tracking columns, coverage matrix and chain of custody.")
            if st.button("Generate working paper", width="stretch", key="gen_wp"):
                with st.spinner("Building workbook…"):
                    st.session_state.exports["wp"] = cached_workpaper(
                        scoring, derived, cov, custody_entry, eng["client_name"], cache_key
                    )
            if st.session_state.exports.get("wp"):
                st.download_button(
                    "📥 Download working paper (.xlsx)",
                    data=st.session_state.exports["wp"],
                    file_name=f"Forensic_Working_Paper_{safe_client}_{today}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary", width="stretch", key="dl_wp",
                )
                st.caption(f"{len(st.session_state.exports['wp'])/1024:,.0f} KB ready.")

        with d2:
            st.markdown("##### 📄 Evidence Requisition List")
            st.caption("Formal client-addressed requisition of the exact books, registers, vouchers and "
                       "third-party records required, each justified by the specific red flags that fired.")
            if st.button("Generate requisition list", width="stretch", key="gen_req"):
                with st.spinner("Building PDF…"):
                    st.session_state.exports["req"] = cached_requisition(
                        scoring, eng["client_name"], f"ENG-{st.session_state.run_id[:8].upper()}",
                        eng.get("firm_name", ""), eng.get("operator", "Lead Forensic Auditor"),
                        eng.get("predication_note", ""), cache_key
                    )
            if st.session_state.exports.get("req"):
                st.download_button(
                    "📥 Download requisition list (.pdf)",
                    data=st.session_state.exports["req"],
                    file_name=f"Evidence_Requisition_List_{safe_client}_{today}.pdf",
                    mime="application/pdf",
                    type="primary", width="stretch", key="dl_req",
                )
                st.caption(f"{len(st.session_state.exports['req'])/1024:,.0f} KB ready.")

        with d3:
            st.markdown("##### 🔒 Chain of Custody")
            st.caption("Immutable run record — source-file SHA-256 hashes, rule-file version hashes, operator, "
                       "predication note, parameters and human confirmations (ICAI Ch. 6.4.1.1).")
            custody_json = json.dumps(custody_entry, indent=2, default=str)
            st.download_button(
                "📥 Download custody log (.json)",
                data=custody_json,
                file_name=f"Custody_Log_{st.session_state.run_id[:8]}.json",
                mime="application/json", width="stretch", key="dl_cust",
            )
            engagement_file = json.dumps({
                "run_id": st.session_state.run_id,
                "engagement": eng,
                "governance_scores": st.session_state.governance_scores,
                "max_instances_per_rule": st.session_state.max_per_rule,
                "files": st.session_state.file_custody_info,
                "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }, indent=2, default=str)
            st.download_button(
                "💾 Save engagement parameters (.json)",
                data=engagement_file,
                file_name=f"Engagement_{safe_client}_{today}.json",
                mime="application/json", width="stretch", key="dl_eng",
            )

        with st.expander("🔍 Preview the chain-of-custody record"):
            st.json(custody_entry, expanded=False)

        st.markdown('<div class="rf-sec">Reopen a saved engagement</div>', unsafe_allow_html=True)
        restore = st.file_uploader("Engagement parameters (.json)", type=["json"], key="restore_eng",
                                   help="Restores materiality, predication note, peer ratios and related parties. "
                                        "Trial balance files must be re-uploaded — they are never stored.")
        if restore is not None:
            try:
                payload = json.loads(restore.getvalue().decode("utf-8"))
                st.session_state.engagement.update(payload.get("engagement", {}))
                st.session_state.max_per_rule = int(payload.get("max_instances_per_rule", 15))
                st.success("Engagement parameters restored. Re-upload the trial balance to run.", icon="✅")
                if st.button("Go to Upload screen", type="primary"):
                    goto(2)
            except Exception as ex:
                st.error(f"Could not read that engagement file: {ex}")

        st.markdown('<div class="rf-sec">Close out</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.3, 1.6, 3])
        with c1:
            if st.button("← Back to Findings", width="stretch"):
                goto(4)
        with c2:
            if st.button("↺ Start a new review", width="stretch"):
                reset_engagement()
                st.rerun()
