"""
Streamlit demo UI wiring all 3 agents + the Tally connector into one place.
Styled to match the L1 app's look (dark navy sidebar nav, card panels, gold
accents) rather than default Streamlit widgets. Calls the agent classes
directly in-process (no separate FastAPI server needed for this demo UI,
though src/main.py exposes the same functionality over HTTP for the deployed
backend).
"""
import csv
import io
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "connectors"))

from agents.compliance import CHECKLISTS, ComplianceAgent
from agents.drafting import DraftingAgent
from agents.onboarding import OnboardingAgent
from schema import CLIENT_MASTER_HEADERS, to_client_master_row
from tally_connector import TallyConnector

st.set_page_config(
    page_title="CA PracticeOS Compliance — AI Agent Layer",
    page_icon="⚖️",
    layout="wide",
)

# ---- Branding: match the L1 app's navy/gold identity, sidebar nav ---------
st.markdown(
    """
    <style>
    :root {
        --navy: #0b1f3a; --blue: #123f73; --gold: #c9a227; --gold2: #e8d08a;
        --green: #16845b; --red: #c62828; --orange: #b76e00; --bg: #f4f7fb;
    }
    .stApp { background: var(--bg); }
    .block-container { padding-top: 2rem; max-width: 1150px; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--navy), #0d2547);
    }
    section[data-testid="stSidebar"] * { color: #d8e3ef !important; }
    section[data-testid="stSidebar"] .stButton button {
        background: transparent; border: 1px solid transparent; text-align: left;
        width: 100%; padding: 10px 14px; border-radius: 9px; font-size: 14px;
        font-weight: 600; justify-content: flex-start;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,.10); border-color: rgba(255,255,255,.15);
    }
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: var(--gold) !important; color: #1d2939 !important;
        border-color: var(--gold) !important;
    }
    section[data-testid="stSidebar"] .stButton button[kind="primary"] * { color: #1d2939 !important; }
    .brand-block { padding: 4px 6px 18px; border-bottom: 1px solid rgba(255,255,255,.14); margin-bottom: 14px; }
    .brand-block h1 { font-size: 20px; margin: 0; color: #fff !important; font-weight: 800; }
    .brand-block .gold { color: var(--gold2) !important; }
    .brand-block p { font-size: 11.5px; color: #9fb2c8 !important; margin: 6px 0 0; }

    /* Page header */
    .page-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 18px; }
    .page-header h2 { margin:0; font-size: 24px; color: var(--navy); }
    .page-header .sub { color:#667085; font-size: 13px; margin-top: 4px; }

    /* Cards */
    .card {
        background: #fff; border: 1px solid #d9e2ec; border-radius: 12px;
        padding: 18px 20px; box-shadow: 0 2px 8px rgba(16,24,40,.04); margin-bottom: 14px;
    }
    .kpi { background:#fff; border:1px solid #d9e2ec; border-radius:12px; padding:14px 16px; }
    .kpi .label { font-size: 12px; color:#667085; }
    .kpi .value { font-size: 26px; font-weight: 800; color: var(--blue); margin-top: 2px; }

    .notice {
        border-left: 4px solid var(--gold); background: #fffaf0; padding: 12px 16px;
        border-radius: 6px; font-size: 13px; color: #6b4e00; margin: 10px 0 18px;
    }

    /* Badges */
    .badge { display: inline-block; padding: 5px 14px; border-radius: 999px; font-weight: 800; font-size: 14px; }
    .badge.green { background: #e7f6ef; color: var(--green); }
    .badge.red { background: #fdecec; color: var(--red); }
    .source-tag { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; background: #eef4fb; color: var(--blue); }

    div[data-testid="stMetricValue"] { color: var(--blue); }
    </style>
    """,
    unsafe_allow_html=True,
)

NAV_ITEMS = [
    ("dashboard", "▦  Dashboard"),
    ("onboarding", "🧾  Agent 1 · Onboarding"),
    ("compliance", "✅  Agent 3 · Compliance"),
    ("pipeline", "🔗  Agent 2 → 3 · Drafting"),
    ("tally", "📊  Tally Connector"),
]

if "view" not in st.session_state:
    st.session_state.view = "dashboard"

with st.sidebar:
    st.markdown(
        """
        <div class="brand-block">
          <h1>CA PracticeOS <span class="gold">Compliance</span></h1>
          <p>AI Agent Layer &middot; AICA Level 2 Capstone</p>
          <p>NSSJ &amp; Co. &middot; CA Shubham Mishra</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for key, label in NAV_ITEMS:
        is_active = st.session_state.view == key
        if st.button(label, key=f"nav_{key}", type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state.view = key
            st.rerun()

view = st.session_state.view


def page_header(title: str, subtitle: str):
    st.markdown(
        f'<div class="page-header"><div><h2>{title}</h2>'
        f'<div class="sub">{subtitle}</div></div></div>',
        unsafe_allow_html=True,
    )


def status_badge(overall: str) -> str:
    if overall == "PASS":
        return '<span class="badge green">✅ PASS</span>'
    return '<span class="badge red">❌ FAIL</span>'


@st.cache_resource
def get_onboarding_agent():
    return OnboardingAgent()


@st.cache_resource
def get_compliance_agent():
    return ComplianceAgent()


@st.cache_resource
def get_drafting_agent():
    return DraftingAgent()


@st.cache_resource
def get_tally_connector():
    connector = TallyConnector()
    connector.authenticate({"company": "Techno Traders Ltd"})
    return connector


# ---- Dashboard --------------------------------------------------------------
if view == "dashboard":
    page_header("Dashboard", "AI Agent Layer &middot; built on top of the CA PracticeOS Compliance L1 document engine")

    st.markdown(
        """
        <div class="notice">
        ★ <b>Agent 3 (Compliance) is the headline feature.</b> It's the product's
        actual differentiator — a genuine multi-step, self-checking workflow that
        validates a drafted document, not one-shot generation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    kpis = [("Agents", "3"), ("Document Types", "6"), ("Connectors", "1 (Tally)"), ("Headline", "Compliance")]
    for c, (label, value) in zip(cols, kpis):
        c.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Quick jump**")
    qcols = st.columns(4)
    quick = [
        ("onboarding", "🧾 Onboarding"),
        ("compliance", "✅ Compliance"),
        ("pipeline", "🔗 Drafting + Compliance"),
        ("tally", "📊 Tally Connector"),
    ]
    for c, (key, label) in zip(qcols, quick):
        if c.button(label, use_container_width=True, key=f"qc_{key}"):
            st.session_state.view = key
            st.rerun()

    with st.container(border=True):
        st.markdown("**What each piece does**")
        st.markdown(
            "- **Agent 1 (Onboarding)** — photo/PDF of a PAN or GST certificate → a validated Client Master row, ready to import into the L1 app.\n"
            "- **Agent 3 (Compliance)** — checks a drafted document against its mandatory-clause checklist; pass/fail with exactly what's missing.\n"
            "- **Agent 2 (Drafting)** — one plain-English line → a filled draft, fed straight into Agent 3.\n"
            "- **Tally Connector** — pulls client/ledger/invoice data via ICAI's Tally Prime MCP Server, with an honest cached fallback when Tally isn't reachable."
        )

# ---- Agent 1: Onboarding ---------------------------------------------------
elif view == "onboarding":
    page_header("Client Onboarding", "Photo or PDF of a PAN card / GST certificate &rarr; a validated Client Master row")

    with st.container(border=True):
        uploaded = st.file_uploader("Upload a PAN card or GST certificate", type=["png", "jpg", "jpeg", "pdf"])
        run = st.button("Extract client details", type="primary", key="extract_btn", disabled=not uploaded)

    if uploaded and run:
        suffix = Path(uploaded.name).suffix
        tmp_path = Path(f"_tmp_upload{suffix}")
        tmp_path.write_bytes(uploaded.getvalue())
        try:
            with st.spinner("Running Agent 1 (perceive → reason → act → validate)..."):
                result = get_onboarding_agent().run(str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

        row = result["row"]
        with st.container(border=True):
            cols = st.columns(3)
            cols[0].metric("Client", row["name"] or "—")
            cols[1].metric("Entity Type", row["entity"] or "—")
            cols[2].metric("State", row["state"] or "—")
            cols = st.columns(3)
            cols[0].metric("PAN", row["pan"] or "—")
            cols[1].metric("GSTIN", row["gstin"] or "—")
            cols[2].metric("SEZ", "Yes" if row["sez"] else "No")

            if result["valid"]:
                st.success("✅ Validated against the Client Master schema — ready to import.")
            else:
                st.warning(f"Validation issues: {result['issues']}")

        with st.expander("Raw extraction JSON"):
            st.json(result)

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CLIENT_MASTER_HEADERS)
        writer.writerow(to_client_master_row(row))
        st.download_button(
            "⬇ Download Client Master CSV row",
            buf.getvalue(),
            file_name="client_master_row.csv",
            mime="text/csv",
        )

# ---- Agent 3: Compliance ---------------------------------------------------
elif view == "compliance":
    page_header("Compliance Checklist", "The product's headline feature &mdash; checks a drafted document against its mandatory-clause checklist")

    with st.container(border=True):
        doc_type = st.selectbox("Document type", ["Auto-detect"] + list(CHECKLISTS.keys()))
        draft_text = st.text_area("Paste the drafted document text", height=260, placeholder="Paste an engagement letter, certificate, or other drafted document here...")
        run_check = st.button("Run compliance check", type="primary", key="check_btn")

    if run_check and draft_text.strip():
        with st.spinner("Running Agent 3 (perceive → reason → self-check → act)..."):
            result = get_compliance_agent().run(
                draft_text, None if doc_type == "Auto-detect" else doc_type
            )
        with st.container(border=True):
            st.markdown(f"{status_badge(result['overall'])} &nbsp; **{result['document_type']}**", unsafe_allow_html=True)
            if result["missing"]:
                st.error(f"Missing clauses: {', '.join(result['missing'])}")
            if result["needs_review"]:
                st.warning(f"Needs human review: {', '.join(result['needs_review'])}")
            if not result["missing"] and not result["needs_review"]:
                st.success("All mandatory clauses present.")

            st.markdown("**Clause-by-clause breakdown**")
            for item in result["items"]:
                icon = {"present": "✅", "absent": "❌", "needs_review": "⚠️"}[item["status"]]
                with st.expander(f"{icon}  {item['name']}"):
                    st.write(f"**Reason:** {item['reason']}")
                    if item["evidence"]:
                        st.write(f"**Evidence:** _{item['evidence']}_")

# ---- Agent 2 -> Agent 3 pipeline -------------------------------------------
elif view == "pipeline":
    page_header("Drafting → Compliance", "One plain-English instruction becomes a draft, immediately compliance-checked &mdash; no manual step in between")

    with st.container(border=True):
        instruction = st.text_input(
            "Describe the document in one line",
            value="Prepare an engagement letter for ABC Pvt Ltd for tax audit AY 2025-26, fees Rs 50,000",
        )
        run_pipeline = st.button("Draft and check", type="primary", key="pipeline_btn")

    if run_pipeline and instruction.strip():
        with st.spinner("Agent 2 drafting..."):
            draft = get_drafting_agent().run(instruction)

        with st.container(border=True):
            st.markdown(f'<span class="source-tag">Agent 2</span> &nbsp; **{draft["doc_type"]}** for **{draft["client_name"]}**', unsafe_allow_html=True)
            st.text_area("Drafted document", draft["draft_text"], height=220)

        with st.spinner("Feeding the draft straight into Agent 3..."):
            compliance = get_compliance_agent().run(draft["draft_text"], draft["doc_type"])

        with st.container(border=True):
            st.markdown(f'<span class="source-tag">Agent 3</span> &nbsp; {status_badge(compliance["overall"])}', unsafe_allow_html=True)
            if compliance["missing"]:
                st.error(f"Missing clauses: {', '.join(compliance['missing'])}")
            if compliance["needs_review"]:
                st.warning(f"Needs human review: {', '.join(compliance['needs_review'])}")
            if not compliance["missing"] and not compliance["needs_review"]:
                st.success("All mandatory clauses present.")

# ---- Tally connector --------------------------------------------------------
elif view == "tally":
    page_header("Tally Connector", "Live when TALLY_MCP_COMMAND is configured and this app runs on the same machine as Tally Prime")
    st.markdown(
        '<div class="notice">Otherwise falls back to a cached real data pull — see '
        '<code>connectors/connector_setup.md</code> for why that\'s the correct behavior, not a bug.</div>',
        unsafe_allow_html=True,
    )

    connector = get_tally_connector()
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Companies**")
            if st.button("Fetch clients (companies)"):
                clients = connector.fetch_clients()
                source = clients[0]["source"] if clients else "n/a"
                st.markdown(f'<span class="source-tag">source: {source}</span>', unsafe_allow_html=True)
                st.json(clients)
    with col2:
        with st.container(border=True):
            st.markdown("**Receivables — Techno Traders Ltd**")
            if st.button("Fetch receivable invoices"):
                invoices = connector.fetch_invoices("Techno Traders Ltd")
                source = invoices[0]["source"] if invoices else "n/a"
                st.markdown(f'<span class="source-tag">source: {source}</span>', unsafe_allow_html=True)
                st.dataframe(invoices, use_container_width=True)
