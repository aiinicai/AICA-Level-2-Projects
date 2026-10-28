"""
Cents & Sensibility — Analytical Procedures & Financial Health Assistant (privacy-first)
AICA Level 2 Capstone Project
Run:  streamlit run app.py
"""

import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.data_ingestion import (
    LINE_ITEMS, LABEL_BY_KEY, PERIODS, make_template_bytes, parse_excel,
    derive, balance_check, blank_period,
)
from modules.ratio_engine import compute_ratios, RATIO_GROUPS, variance_table
from modules.forensic_scores import altman_z, beneish_m, health_score, liquidity_stress_flags
from modules import narrative_ai, branding, redaction
from modules.report_export import build_report

# ============================================================================
# Page config & theme
# ============================================================================
st.set_page_config(page_title=branding.APP_FULL, page_icon=branding.APP_ICON, layout="wide")

ACCENT, ACCENT2, WARM, INK, PAPER = "#12634F", "#0E4F3F", "#C79A3B", "#14201C", "#F6F5F0"
MUTED, BORDER, DEEP = "#667570", "#E6E3DA", "#0B2A24"
GREEN, AMBER, RED = "#1F8A64", "#B7791F", "#C0453B"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{ font-family:'Inter',sans-serif; color:{INK}; }}
.stApp {{
  background:
    radial-gradient(900px 420px at 8% -8%, #DCEBE3 0%, rgba(220,235,227,0) 70%),
    radial-gradient(700px 360px at 100% 0%, #F3E8CF 0%, rgba(243,232,207,0) 65%),
    {PAPER};
}}
header[data-testid="stHeader"] {{ background:transparent; }}
#MainMenu, footer {{ visibility:hidden; }}
.block-container {{ max-width:1180px; padding-top:1.6rem; padding-bottom:4rem; }}

/* ---------- sidebar: deep emerald ---------- */
section[data-testid="stSidebar"] {{
  background:linear-gradient(185deg, {DEEP} 0%, #0F3B32 100%); border-right:0; }}
section[data-testid="stSidebar"] * {{ color:#E8F0EC; }}
section[data-testid="stSidebar"] hr {{ border-color:rgba(255,255,255,.12); margin:1rem 0; }}
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {{ color:#CFE0D8; font-size:13px; }}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
  background:rgba(255,255,255,.96) !important; border:0 !important; border-radius:10px !important; }}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] * {{ color:{INK} !important; }}
section[data-testid="stSidebar"] div[data-testid="stAlert"] {{
  background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.14); }}
section[data-testid="stSidebar"] div[data-testid="stAlert"] * {{ color:#DDEBE4 !important; }}
section[data-testid="stSidebar"] button {{ color:{INK}; }}
.fl-brand {{ font-family:'Fraunces',serif; font-size:31px !important; font-weight:600; letter-spacing:-.015em;
  color:#fff !important; line-height:1.05; margin:4px 0 0 0; }}
.fl-brand span {{ color:{WARM} !important; font-style:italic; font-weight:500; }}
.fl-tag {{ font-size:10px !important; letter-spacing:.16em; text-transform:uppercase;
  color:#8FB3A6 !important; margin:8px 0 0 0; }}

/* ---------- hero ---------- */
.fl-hero {{ position:relative; overflow:hidden; border-radius:20px; padding:26px 30px;
  background:linear-gradient(120deg, {DEEP} 0%, #124C3F 55%, #1A6A57 100%);
  box-shadow:0 12px 32px -14px rgba(11,42,36,.55); margin-bottom:22px; }}
.fl-hero:after {{ content:""; position:absolute; right:-60px; top:-70px; width:260px; height:260px;
  border-radius:50%; background:radial-gradient(circle, rgba(199,154,59,.38), rgba(199,154,59,0) 68%); }}
.fl-eyebrow {{ font-size:11px !important; letter-spacing:.2em; text-transform:uppercase; color:{WARM};
  font-weight:600; margin:0 0 6px 0; }}
.fl-title {{ font-family:'Fraunces',serif; font-size:36px !important; font-weight:600; letter-spacing:-.02em;
  color:#fff; margin:0; line-height:1.12; position:relative; z-index:1; }}
.fl-chips {{ margin-top:14px; position:relative; z-index:1; }}
.fl-chip {{ display:inline-block; font-size:12px; font-weight:500; color:#DDEBE4;
  padding:5px 12px; margin:0 6px 6px 0; border-radius:999px;
  background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.16); }}
.fl-chip-warn {{ background:rgba(199,154,59,.22); border-color:rgba(199,154,59,.5); color:#F6E4B8; }}
h1, h2, h3, h4 {{ font-family:'Inter',sans-serif; color:{INK}; letter-spacing:-.015em; font-weight:650; }}
h3 {{ font-size:20px !important; }} h4 {{ font-size:15px !important; }}

/* ---------- steps ---------- */
.fl-steps {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:4px 0 22px 0; }}
.fl-step {{ background:rgba(255,255,255,.75); backdrop-filter:blur(6px); border:1px solid {BORDER};
  border-radius:16px; padding:16px 18px; }}
.fl-step-n {{ width:26px; height:26px; border-radius:50%; background:{ACCENT}; color:#fff;
  font-size:12.5px; font-weight:600; display:flex; align-items:center; justify-content:center; margin-bottom:10px; }}
.fl-step-t {{ font-weight:600; font-size:14.5px !important; margin:0 0 2px 0; }}
.fl-step-d {{ font-size:12.5px !important; color:{MUTED}; margin:0; line-height:1.45; }}

/* ---------- cards & metrics ---------- */
.fl-card {{ position:relative; background:rgba(255,255,255,.92); border:1px solid {BORDER};
  border-radius:16px; padding:18px 20px; box-shadow:0 1px 2px rgba(20,32,28,.04), 0 8px 24px -16px rgba(20,32,28,.18);
  transition:transform .18s ease, box-shadow .18s ease; }}
.fl-card:hover {{ transform:translateY(-2px); box-shadow:0 1px 2px rgba(20,32,28,.05), 0 14px 30px -16px rgba(20,32,28,.28); }}
.fl-card:before {{ content:""; position:absolute; left:20px; top:0; width:34px; height:3px;
  border-radius:0 0 3px 3px; background:linear-gradient(90deg,{ACCENT},{WARM}); }}
.fl-metric-label {{ font-size:11px !important; letter-spacing:.11em; text-transform:uppercase; color:{MUTED}; font-weight:600; }}
.fl-metric-value {{ font-family:'Fraunces',serif; font-size:32px !important; font-weight:600; letter-spacing:-.02em;
  color:{INK}; margin-top:6px; font-variant-numeric:tabular-nums; }}
.fl-metric-delta-up {{ color:{GREEN}; font-size:12.5px; font-weight:600; }}
.fl-metric-delta-down {{ color:{RED}; font-size:12.5px; font-weight:600; }}
.fl-badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font-size:12.5px; font-weight:600; }}
.fl-badge-green {{ background:#DDF1E7; color:{GREEN}; }}
.fl-badge-amber {{ background:#F8EBD0; color:{AMBER}; }}
.fl-badge-red {{ background:#F8DFDC; color:{RED}; }}
.fl-note {{ font-size:12.5px; color:{MUTED}; }}

/* ---------- submitter ---------- */
.fl-submitter {{ border-left:2px solid {WARM}; padding:2px 0 2px 12px; }}
.fl-submitter-eyebrow {{ font-size:10px !important; letter-spacing:.16em; text-transform:uppercase;
  color:#8FB3A6 !important; margin:0 0 3px 0; }}
.fl-submitter-name {{ font-family:'Fraunces',serif; font-size:19px !important; font-weight:600; color:#fff !important;
  margin:0; line-height:1.2; }}
.fl-submitter-batch {{ font-size:11px !important; letter-spacing:.1em; color:{WARM} !important; margin:4px 0 0 0; font-weight:600; }}

/* ---------- tabs: pills (works with old and new Streamlit DOM) ---------- */
[role="tablist"] {{ gap:6px !important; border-bottom:0 !important; padding-bottom:8px; flex-wrap:wrap; }}
[role="tab"] {{ font-weight:500; color:{MUTED}; padding:7px 15px !important; border-radius:999px !important;
  background:rgba(255,255,255,.65) !important; border:1px solid {BORDER} !important; height:auto !important; cursor:pointer; }}
[role="tab"] p {{ font-size:13.5px !important; color:inherit !important; margin:0; }}
[role="tab"]:hover {{ color:{INK}; border-color:#CFCABB !important; }}
[role="tab"][aria-selected="true"] {{ color:#fff !important; background:{ACCENT} !important;
  border-color:{ACCENT} !important; box-shadow:0 8px 16px -9px {ACCENT}; }}
[role="tab"][aria-selected="true"] p {{ font-weight:600; }}
[role="tab"] .react-aria-SelectionIndicator, [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display:none !important; }}

/* ---------- buttons & inputs ---------- */
.stDownloadButton button, .stButton button {{ border-radius:10px; font-weight:500;
  border:1px solid {BORDER}; background:#fff; color:{INK}; transition:all .15s ease; }}
.stDownloadButton button:hover, .stButton button:hover {{ border-color:{ACCENT}; color:{ACCENT}; }}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {{
  background:linear-gradient(135deg,{ACCENT},{ACCENT2}); color:#fff; border:0;
  box-shadow:0 8px 18px -10px {ACCENT}; }}
.stButton button[kind="primary"]:hover {{ color:#fff; transform:translateY(-1px); }}
.stButton button:disabled {{ opacity:.45; }}
div[data-testid="stFileUploader"] section {{ background:rgba(255,255,255,.85); border:1.5px dashed #BFD2C9; border-radius:16px; }}
textarea, .stTextInput input {{ border-radius:10px !important; }}
div[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:14px; overflow:hidden; }}
div[data-testid="stAlert"] {{ border-radius:12px; }}
div[data-testid="stExpander"] {{ border:1px solid {BORDER}; border-radius:14px; background:rgba(255,255,255,.7); }}
hr {{ border-color:{BORDER}; }}
@media (max-width:760px) {{ .fl-steps {{ grid-template-columns:1fr; }} .fl-title {{ font-size:28px; }} }}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter", color=INK, size=12),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=40, b=10),
    colorway=[ACCENT, WARM, "#5E8FA3", "#A8A29A"],
)

# ============================================================================
# Session state
# ============================================================================
ss = st.session_state
ss.setdefault("data", None)             # confirmed canonical data
ss.setdefault("pending", None)          # extracted-but-unconfirmed data (PDF path)
ss.setdefault("pending_notes", [])
ss.setdefault("lens", None)
ss.setdefault("narrative", None)
ss.setdefault("company", "ABC Manufacturing Pvt Ltd")
ss.setdefault("unit", "₹ in Lakhs")
ss.setdefault("privacy", True)           # Privacy mode: redact before any LLM call
ss.setdefault("p_persons", "")           # directors / signatories / KMP (one per line)
ss.setdefault("p_orgs", "")              # auditors, banks, group cos., subsidiaries
ss.setdefault("p_addresses", "")         # registered office, plants, cities
ss.setdefault("p_lines_on", True)       # remove whole lines containing trigger words
ss.setdefault("p_lines", "\n".join(redaction.DEFAULT_LINE_KEYWORDS))
ss.setdefault("p_cuts_on", True)        # drop the signature block after "As per our report..."
ss.setdefault("p_cuts", "\n".join(redaction.DEFAULT_CUT_MARKERS))
ss.setdefault("p_parts", True)           # also mask parts of names (surnames etc.)
ss.setdefault("red_text", None)          # redacted PDF text awaiting approval
ss.setdefault("red_report", None)        # what was replaced
ss.setdefault("red_flags", [])
ss.setdefault("red_pdf_name", None)
ss.setdefault("red_ver", 0)
ss.setdefault("wb_text", None)           # workbook text awaiting approval
ss.setdefault("wb_report", None)
ss.setdefault("wb_flags", [])
ss.setdefault("wb_ver", 0)


def make_redactor():
    """Redactor built from the current Privacy settings (None when Privacy mode is off)."""
    if not ss.privacy:
        return None
    return redaction.Redactor(
        entity=ss.company,
        persons=redaction.parse_terms(ss.p_persons),
        orgs=redaction.parse_terms(ss.p_orgs),
        addresses=redaction.parse_terms(ss.p_addresses),
        mask_name_parts=ss.p_parts,
        line_keywords=redaction.parse_terms(ss.p_lines) if ss.p_lines_on else (),
        cut_markers=redaction.parse_terms(ss.p_cuts) if ss.p_cuts_on else (),
    )

# ============================================================================
# Sidebar
# ============================================================================
with st.sidebar:
    st.markdown('<p class="fl-brand">' + html.escape(branding.BRAND_MAIN) + '<span>' + html.escape(branding.BRAND_ACCENT) + '</span></p>', unsafe_allow_html=True)
    st.markdown('<p class="fl-tag">Analytical procedures · Financial health</p>',
                unsafe_allow_html=True)

    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception as e:
        api_key = ""
        st.warning(f"Secrets not loaded: {e}")
    api_key = (api_key or "").strip()
    if api_key:
        st.success("Claude API connected", icon="✅")
    else:
        api_key = st.text_input("Claude API key", type="password",
                                help="Or set ANTHROPIC_API_KEY in .streamlit/secrets.toml")
        api_key = (api_key or "").strip()
        if not api_key:
            st.info("No API key — AI features run in offline rule-based mode.", icon="ℹ️")
    st.divider()

    ss.company = st.text_input("Entity name", ss.company)
    ss.privacy = st.toggle("🔒 Privacy mode", value=ss.privacy,
                           help="Masks the entity name, directors, identifiers (PAN, GSTIN, CIN…) "
                                "on this computer before anything is sent to the AI.")
    if ss.privacy:
        st.caption("Names & identifiers are masked locally before any AI call. See the 🔒 Privacy tab.")
    else:
        st.warning("Privacy mode is OFF: names and the PDF itself may be sent to the Claude cloud.",
                   icon="⚠️")
    unit_options = ["₹ in Lakhs", "₹ in Crores", "₹ in Millions", "₹ in '000", "₹ in hundreds ('00)", "₹ (absolute)"]
    ss.unit = st.selectbox("Amounts are in", unit_options,
                           index=unit_options.index(ss.unit))
    materiality = st.slider("SA 520 variance threshold (%)", 5, 30, 10,
                            help="Variances beyond this % are flagged for investigation")

    st.divider()
    st.markdown("""<div class="fl-submitter">
      <p class="fl-submitter-eyebrow">Submitted by</p>
      <p class="fl-submitter-name">CA Krishna S</p>
      <p class="fl-submitter-batch">AICA · L2B98 · ERNAKULAM</p>
    </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown('<p class="fl-note">AICA Level 2 Capstone · AI outputs are drafts '
                'requiring professional review.</p>', unsafe_allow_html=True)

# ============================================================================
# Header
# ============================================================================
_priv = ('<span class="fl-chip">🔒 Privacy mode on</span>' if ss.privacy else
         '<span class="fl-chip fl-chip-warn">⚠️ Privacy mode off</span>')
st.markdown(
    f'<div class="fl-hero"><p class="fl-eyebrow">{html.escape(branding.APP_NAME)}</p>'
    f'<p class="fl-title">{html.escape(ss.company)}</p>'
    f'<div class="fl-chips"><span class="fl-chip">{html.escape(ss.unit)}</span>'
    f'<span class="fl-chip">SA 520 threshold {materiality}%</span>{_priv}'
    f'<span class="fl-chip">Financial statement analysis</span></div></div>',
    unsafe_allow_html=True)

tabs = st.tabs(["📥 Data", "📊 Dashboard", "📈 Ratios & Trends",
                "🧭 Auditor's Lens", "📝 AI Narrative", "📄 Export", "🔒 Privacy"])

# ============================================================================
# TAB 1 — DATA
# ============================================================================
with tabs[0]:
    if ss.data is None:
        st.markdown('''<div class="fl-steps">
          <div class="fl-step"><div class="fl-step-n">1</div><p class="fl-step-t">Load statements</p>
            <p class="fl-step-d">Upload the Excel template, a workbook with notes, or a PDF.</p></div>
          <div class="fl-step"><div class="fl-step-n">2</div><p class="fl-step-t">Protect the client</p>
            <p class="fl-step-d">Names, IDs and address lines are masked on your computer first.</p></div>
          <div class="fl-step"><div class="fl-step-n">3</div><p class="fl-step-t">Analyse &amp; report</p>
            <p class="fl-step-d">Ratios, SA 520 workpaper, red-flag scores and a Word report.</p></div>
        </div>''', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("### Excel upload (template)")
        st.download_button("⬇️ Download input template",
                           make_template_bytes(), "CentsSensibility_Template.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        xl = st.file_uploader("Upload completed template", type=["xlsx", "xls"], key="xl")
        if xl is not None and st.button("Parse Excel", type="primary", key="parse_xl"):
            try:
                data, warns = parse_excel(xl)
                ss.data, ss.lens, ss.narrative = data, None, None
                for w in warns:
                    st.warning(w)
                st.success("Excel parsed and loaded. Open the Dashboard tab. ✔")
            except Exception as e:
                st.error(f"Could not parse the file: {e}")

    with c2:
        st.markdown("### PDF upload (AI extraction)")
        pdf = st.file_uploader("Upload financial statements PDF", type=["pdf"], key="pdf")

        if not ss.privacy:
            st.markdown('<p class="fl-note">Privacy mode is OFF: the PDF file itself is sent '
                        'to the Claude API.</p>', unsafe_allow_html=True)
            if pdf is not None and st.button("Extract with Claude", type="primary", key="parse_pdf"):
                if not api_key:
                    st.error("PDF extraction needs a Claude API key (sidebar).")
                else:
                    with st.spinner("Reading the financial statements…"):
                        try:
                            pending, notes = narrative_ai.extract_from_pdf(pdf.read(), api_key)
                            ss.pending, ss.pending_notes = pending, notes
                        except Exception as e:
                            st.error(f"Extraction failed: {e}. Please use the Excel template path.")
        else:
            st.markdown('<p class="fl-note">🔒 Privacy mode: text is read <b>on this computer</b>, '
                        'names and identifiers are masked, and you approve the exact text before '
                        'only that text (never the PDF) is sent.</p>', unsafe_allow_html=True)
            if pdf is not None:
                pdf_bytes = pdf.getvalue()
                try:
                    total_pages = redaction.pdf_page_count(pdf_bytes)
                except Exception as e:
                    total_pages = 0
                    st.error(f"Could not open the PDF: {e}")
                if total_pages:
                    rng = st.text_input(
                        f"Pages to send (PDF has {total_pages})", key="pdf_range",
                        placeholder="e.g. 168-169  (Balance Sheet & P&L only)",
                        help="Send only the statement pages — less data leaves your machine.")
                    if st.button("Prepare redacted preview", type="primary", key="prep_red"):
                        try:
                            pages = redaction.parse_page_range(rng, total_pages)
                            if len(pages) > 40:
                                st.warning("That is a lot of pages. Narrow to the Balance Sheet "
                                           "and P&L pages for accuracy, cost and privacy.")
                            raw_text = redaction.extract_pdf_text(pdf_bytes, pages)
                            red = make_redactor()
                            res = red.redact(raw_text)
                            ss.red_text, ss.red_pdf_name = res.text, pdf.name
                            ss.red_ver += 1
                            ss.red_report = {"entries": res.entries, "unmatched": res.unmatched,
                                             "hits": res.total_hits}
                            ss.red_flags = redaction.review_flags(res.text)
                        except redaction.NoTextLayerError as e:
                            ss.red_text = None
                            st.error(str(e))
                        except Exception as e:
                            ss.red_text = None
                            st.error(f"Could not prepare the preview: {e}")

            if ss.red_text:
                st.markdown("#### Review what will be sent")
                rep_ = ss.red_report or {}
                st.caption(f"{rep_.get('hits', 0)} replacements made locally. "
                           "The originals below stay on your computer.")
                if rep_.get("entries"):
                    st.dataframe(pd.DataFrame(rep_["entries"]).rename(columns={
                        "kind": "Type", "token": "Sent as", "original": "Original (local only)",
                        "hits": "Times"}), hide_index=True, use_container_width=True)
                for u in rep_.get("unmatched", []):
                    st.caption(f"ℹ️ '{u['original']}' ({u['kind']}) was not found in these pages.")
                for f_ in ss.red_flags:
                    st.warning(f"Possible unmasked item — {f_}. Add it in the 🔒 Privacy tab "
                               "or edit the text below.", icon="👀")
                ss.red_text = st.text_area("Redacted text (editable — this exact text is sent)",
                                           ss.red_text, height=260, key=f"red_text_area_{ss.red_ver}")
                ok_send = st.checkbox("I have reviewed this text and approve sending it to the "
                                      "Claude API", key="red_approve")
                if st.button("Send redacted text to Claude", type="primary",
                             disabled=not (ok_send and api_key), key="send_red"):
                    red = make_redactor()
                    with st.spinner("Extracting figures from the redacted text…"):
                        try:
                            pending, notes = narrative_ai.extract_from_text(
                                ss.red_text, api_key, redactor=red)
                            ss.pending, ss.pending_notes = pending, red.restore_obj(notes)
                            ss.red_text = None
                        except redaction.RedactionError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Extraction failed: {e}. Please use the Excel template path.")
                if not api_key:
                    st.caption("Add a Claude API key in the sidebar to enable sending.")

    # --- Excel workbook with notes (multi-sheet, AI-assisted, privacy-aware) ---
    st.divider()
    st.markdown("### Excel workbook with notes")
    st.markdown('<p class="fl-note">Upload your own workbook: Balance Sheet, P&amp;L, <b>notes to '
                'accounts on separate sheets</b>, or a trial balance. Sheets are read on this '
                'computer; you choose which ones are used.</p>', unsafe_allow_html=True)
    wbf = st.file_uploader("Upload workbook (.xlsx / .xlsm)", type=["xlsx", "xlsm"], key="wb")
    wb_bytes, wb_info = None, []
    if wbf is not None:
        wb_bytes = wbf.getvalue()
        try:
            wb_info = redaction.excel_sheet_info(wb_bytes)
        except redaction.RedactionError as e:
            st.error(str(e))
    if wb_info:
        labels = {f"{i['name']}  ({i['rows']} rows{', hidden' if i['hidden'] else ''})": i["name"]
                  for i in wb_info}
        default = [l for l, nme in labels.items() if not any(i["hidden"] and i["name"] == nme for i in wb_info)]
        chosen = st.multiselect("Sheets to use (include the statements and their notes)",
                                list(labels), default=default, key=f"wb_sheets_{wbf.name}")
        if st.button("Prepare preview", type="primary", key="prep_wb", disabled=not chosen):
            try:
                raw_text = redaction.extract_excel_text(wb_bytes, [labels[c] for c in chosen])
                if ss.privacy:
                    res = make_redactor().redact(raw_text)
                    ss.wb_text = res.text
                    ss.wb_report = {"entries": res.entries, "unmatched": res.unmatched,
                                    "hits": res.total_hits}
                    ss.wb_flags = redaction.review_flags(res.text)
                else:
                    ss.wb_text, ss.wb_report, ss.wb_flags = raw_text, None, []
                ss.wb_ver += 1
            except redaction.RedactionError as e:
                ss.wb_text = None
                st.error(str(e))
            except Exception as e:
                ss.wb_text = None
                st.error(f"Could not prepare the preview: {e}")

    if ss.wb_text:
        st.markdown("#### Review what will be sent")
        n_chars = len(ss.wb_text)
        st.caption(f"{n_chars:,} characters (about {n_chars // 4:,} tokens).")
        if n_chars > 300_000:
            st.warning("This is very large. Untick the sheets you do not need (for example "
                       "long ledgers) to improve accuracy and cost.", icon="📏")
        if ss.privacy:
            rep_ = ss.wb_report or {}
            st.caption(f"{rep_.get('hits', 0)} replacements made locally. "
                       "The originals below stay on your computer.")
            if rep_.get("entries"):
                st.dataframe(pd.DataFrame(rep_["entries"]).rename(columns={
                    "kind": "Type", "token": "Sent as", "original": "Original (local only)",
                    "hits": "Times"}), hide_index=True, use_container_width=True)
            for u in rep_.get("unmatched", []):
                st.caption(f"ℹ️ '{u['original']}' ({u['kind']}) was not found in these sheets.")
            for f_ in ss.wb_flags:
                st.warning(f"Possible unmasked item — {f_}. Add it in the 🔒 Privacy tab or "
                           "edit the text below.", icon="👀")
        else:
            st.warning("Privacy mode is OFF: this text is sent exactly as shown, with names.", icon="⚠️")
        ss.wb_text = st.text_area("Workbook text (editable — this exact text is sent)",
                                  ss.wb_text, height=300, key=f"wb_text_area_{ss.wb_ver}")
        wb_ok = st.checkbox("I have reviewed this text and approve sending it to the Claude API",
                            key="wb_approve")
        if st.button("Send to Claude and extract", type="primary",
                     disabled=not (wb_ok and api_key), key="send_wb"):
            red = make_redactor()
            with st.spinner("Reading the statements and notes…"):
                try:
                    pending, notes = narrative_ai.extract_from_text(
                        ss.wb_text, api_key, redactor=red, workbook=True)
                    ss.pending = pending
                    ss.pending_notes = red.restore_obj(notes) if red else notes
                    ss.wb_text = None
                except redaction.RedactionError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Extraction failed: {e}. Please use the Excel template path.")
        if not api_key:
            st.caption("Add a Claude API key in the sidebar to enable sending.")

    # --- Review & confirm screen for PDF extraction (human-in-the-loop) ---
    if ss.pending is not None:
        st.divider()
        st.markdown("### Review & confirm extracted figures")
        for n in ss.pending_notes:
            st.info(n, icon="🔎")
        rows = [{"Line Item": LABEL_BY_KEY[k],
                 "Current Year": ss.pending["CY"][k],
                 "Previous Year": ss.pending["PY"][k]} for k, *_ in LINE_ITEMS]
        edited = st.data_editor(pd.DataFrame(rows), hide_index=True,
                                use_container_width=True, key="review_editor")

        cand = {"CY": blank_period(), "PY": blank_period(), "PY2": None}
        rev = {v.strip().lower(): k for k, v in LABEL_BY_KEY.items()}
        for _, r_ in edited.iterrows():
            k = rev.get(str(r_["Line Item"]).strip().lower())
            if k:
                cand["CY"][k] = float(pd.to_numeric(r_["Current Year"], errors="coerce") or 0)
                cand["PY"][k] = float(pd.to_numeric(r_["Previous Year"], errors="coerce") or 0)

        bc, bp = st.columns(2)
        for col, period in ((bc, "CY"), (bp, "PY")):
            ok, diff = balance_check(cand[period])
            with col:
                if ok:
                    st.success(f"{period}: Balance Sheet ties (Assets = Equity + Liabilities) ✔")
                else:
                    st.error(f"{period}: Balance Sheet difference of {diff:,.2f} — "
                             "please correct the figures above.")

        if st.button("✅ Confirm figures & run analysis", type="primary"):
            ss.data, ss.pending, ss.lens, ss.narrative = cand, None, None, None
            st.success("Figures confirmed. Open the Dashboard tab.")

    if ss.data is not None:
        st.divider()
        d = derive(ss.data["CY"])
        st.markdown(f'<p class="fl-note">Loaded ✔ &nbsp; Total assets (CY): '
                    f'<b>{d["total_assets"]:,.0f}</b> &nbsp;·&nbsp; Revenue (CY): '
                    f'<b>{d["revenue"]:,.0f}</b> &nbsp;·&nbsp; '
                    f'{"3-year data" if ss.data.get("PY2") else "2-year data"}</p>',
                    unsafe_allow_html=True)


def _need_data():
    st.markdown('<div class="fl-card">📥 &nbsp;Load financial data in the '
                '<b>Data</b> tab to begin the analysis.</div>', unsafe_allow_html=True)


# ============================================================================
# TAB 2 — DASHBOARD
# ============================================================================
with tabs[1]:
    if ss.data is None:
        _need_data()
    else:
        cy, py = derive(ss.data["CY"]), derive(ss.data["PY"])
        z = altman_z(ss.data["CY"])
        m = beneish_m(ss.data)
        hs = health_score(ss.data, z, m)

        def metric_card(col, label, cyv, pyv):
            delta = (cyv - pyv) / abs(pyv) * 100 if pyv else None
            arrow = "" if delta is None else (f"▲ {delta:,.1f}%" if delta >= 0
                                              else f"▼ {abs(delta):,.1f}%")
            cls = "fl-metric-delta-up" if (delta or 0) >= 0 else "fl-metric-delta-down"
            col.markdown(f"""<div class="fl-card">
              <div class="fl-metric-label">{label}</div>
              <div class="fl-metric-value">{cyv:,.0f}</div>
              <div class="{cls}">{arrow} <span class="fl-note">vs PY</span></div>
            </div>""", unsafe_allow_html=True)

        c = st.columns(4)
        metric_card(c[0], "Revenue", cy["revenue"], py["revenue"])
        metric_card(c[1], "Profit After Tax", cy["pat"], py["pat"])
        metric_card(c[2], "Net Worth", cy["total_equity"], py["total_equity"])
        metric_card(c[3], "Cash & Bank", cy["cash"], py["cash"])

        st.write("")
        g1, g2 = st.columns([1.2, 1], gap="large")

        with g1:
            band_color = {"Strong": GREEN, "Stable": WARM,
                          "Watchlist": AMBER, "Stressed": RED}[hs["band"]]
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=hs["score"],
                number={"font": {"family": "Fraunces", "size": 54, "color": ACCENT}},
                title={"text": f"Financial Health Score — <b>{hs['band']}</b>",
                       "font": {"size": 16, "color": ACCENT}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#8A9BB4"},
                    "bar": {"color": band_color, "thickness": 0.28},
                    "steps": [
                        {"range": [0, 35], "color": "#F9E4E2"},
                        {"range": [35, 50], "color": "#FBF0DD"},
                        {"range": [50, 70], "color": "#F3EBDA"},
                        {"range": [70, 100], "color": "#E4F4EC"},
                    ],
                },
            ))
            gauge.update_layout(height=320, **PLOTLY_LAYOUT)
            st.plotly_chart(gauge, use_container_width=True)
            st.markdown('<p class="fl-note">Composite of solvency (40%), earnings quality '
                        '(25%), liquidity (20%) and profitability (15%).</p>',
                        unsafe_allow_html=True)

        with g2:
            def badge(txt, kind):
                return f'<span class="fl-badge fl-badge-{kind}">{txt}</span>'

            z_kind = {"Safe Zone": "green", "Grey Zone": "amber",
                      "Distress Zone": "red"}.get(z["zone"], "amber")
            m_kind = "red" if m["verdict"] == "Possible Manipulator" else "green"

            st.markdown(f"""<div class="fl-card">
              <div class="fl-metric-label">Altman Z′-Score (private-firm model)</div>
              <div class="fl-metric-value">{z['score']}</div>
              {badge(z['zone'], z_kind)}
              <p class="fl-note" style="margin-top:8px">Safe &gt; 2.90 · Grey 1.23–2.90 ·
              Distress &lt; 1.23</p>
            </div>""", unsafe_allow_html=True)
            st.write("")
            st.markdown(f"""<div class="fl-card">
              <div class="fl-metric-label">Beneish M-Score (earnings manipulation screen)</div>
              <div class="fl-metric-value">{m['score']}</div>
              {badge(m['verdict'], m_kind)}
              <p class="fl-note" style="margin-top:8px">Threshold −2.22 · a higher score
              suggests possible manipulation (screening indicator, not a conclusion)</p>
            </div>""", unsafe_allow_html=True)

        with st.expander("Model components (for the working paper)"):
            cc1, cc2, cc3 = st.columns(3)
            cc1.markdown("**Altman Z′ components**")
            cc1.dataframe(pd.DataFrame(z["components"].items(),
                                       columns=["Component", "Value"]), hide_index=True)
            cc2.markdown("**Beneish M components**")
            cc2.dataframe(pd.DataFrame(m["components"].items(),
                                       columns=["Index", "Value"]), hide_index=True)
            cc3.markdown("**Health score parts**")
            cc3.dataframe(pd.DataFrame(hs["parts"].items(),
                                       columns=["Component", "Score /100"]), hide_index=True)
            for n in m.get("notes", []):
                st.caption("· " + n)

        st.markdown("#### Stress indicators")
        for f in liquidity_stress_flags(ss.data):
            icon = "✅" if f.startswith("No significant") else "⚠️"
            st.markdown(f"{icon} {f}")

# ============================================================================
# TAB 3 — RATIOS & TRENDS
# ============================================================================
with tabs[2]:
    if ss.data is None:
        _need_data()
    else:
        periods = [p for p in PERIODS if ss.data.get(p)]
        ratios = {p: compute_ratios(ss.data[p]) for p in periods}
        year_names = {"CY": "Current Yr", "PY": "Previous Yr", "PY2": "Yr −2"}

        rows = []
        for grp, names in RATIO_GROUPS.items():
            for name in names:
                row = {"Group": grp, "Ratio": name}
                for p in periods:
                    v = ratios[p].get(name)
                    row[year_names[p]] = round(v, 2) if v is not None else None
                rows.append(row)
        ratio_df = pd.DataFrame(rows)

        st.markdown("### Ratio analysis")
        sel = st.multiselect("Filter groups", list(RATIO_GROUPS),
                             default=list(RATIO_GROUPS))
        st.dataframe(ratio_df[ratio_df["Group"].isin(sel)], hide_index=True,
                     use_container_width=True, height=420)

        st.markdown("### Trends")
        t1, t2 = st.columns(2, gap="large")
        order = [p for p in ["PY2", "PY", "CY"] if p in periods]
        xlabels = [year_names[p] for p in order]

        with t1:
            fig = go.Figure()
            for key, label in [("revenue", "Revenue"), ("pat", "PAT"),
                               ("ebitda", "EBITDA")]:
                fig.add_trace(go.Bar(name=label, x=xlabels,
                                     y=[derive(ss.data[p])[key] for p in order]))
            fig.update_layout(title="Performance trend", barmode="group",
                              height=340, **PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

        with t2:
            fig = go.Figure()
            for name in ["Current Ratio", "Debt-Equity Ratio", "Net Profit Margin %"]:
                fig.add_trace(go.Scatter(name=name, x=xlabels, mode="lines+markers",
                                         y=[ratios[p].get(name) for p in order]))
            fig.update_layout(title="Key ratio trend", height=340, **PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"### SA 520 variance analysis (threshold {materiality}%)")
        vt = variance_table(ss.data, materiality)
        vdf = pd.DataFrame(vt)
        vdf["Investigate"] = vdf.pop("Flag").map({True: "🚩 YES", False: "—"})
        st.dataframe(vdf, hide_index=True, use_container_width=True, height=420)
        flagged_n = sum(r["Flag"] for r in vt)
        st.markdown(f'<p class="fl-note"><b>{flagged_n}</b> item(s) breach the threshold '
                    'and flow into the Auditor’s Lens workpaper.</p>', unsafe_allow_html=True)

# ============================================================================
# TAB 4 — AUDITOR'S LENS
# ============================================================================
with tabs[3]:
    if ss.data is None:
        _need_data()
    else:
        st.markdown("### Auditor's Lens")
        st.markdown('<p class="fl-note">SA 520 analytical-procedures workpaper, SA 570 '
                    'going-concern assessment and management inquiries — drafted by AI, '
                    'for engagement-partner review.</p>', unsafe_allow_html=True)

        mode = "Claude API" if api_key else "Offline rule-based fallback"
        if st.button(f"⚙️ Generate Auditor's Lens ({mode})", type="primary"):
            with st.spinner("Drafting audit documentation…"):
                try:
                    if api_key:
                        ss.lens = narrative_ai.auditors_lens(
                            ss.data, api_key, materiality, ss.company,
                            redactor=make_redactor())
                    else:
                        ss.lens = narrative_ai.auditors_lens_fallback(ss.data, materiality)
                except Exception as e:
                    st.error(f"AI generation failed ({e}) — using offline fallback "
                             "(nothing was sent).")
                    ss.lens = narrative_ai.auditors_lens_fallback(ss.data, materiality)

        if ss.lens:
            st.markdown("#### 1 · Analytical procedures workpaper (SA 520)")
            st.dataframe(pd.DataFrame(ss.lens.get("workpaper", [])),
                         hide_index=True, use_container_width=True)
            st.markdown("#### 2 · Going-concern indicators (SA 570)")
            st.dataframe(pd.DataFrame(ss.lens.get("going_concern", [])),
                         hide_index=True, use_container_width=True)
            st.markdown("#### 3 · Suggested management inquiries")
            for i, q in enumerate(ss.lens.get("inquiries", []), 1):
                st.markdown(f"**{i}.** {q}")
            st.info("Draft documentation only — apply professional judgement and obtain "
                    "corroborating evidence before relying on any point.", icon="⚖️")

# ============================================================================
# TAB 5 — AI NARRATIVE
# ============================================================================
with tabs[4]:
    if ss.data is None:
        _need_data()
    else:
        st.markdown("### AI-drafted financial commentary")
        if st.button("📝 Generate commentary", type="primary",
                     disabled=not api_key,
                     help=None if api_key else "Requires a Claude API key"):
            with st.spinner("Writing the commentary…"):
                z = altman_z(ss.data["CY"])
                m = beneish_m(ss.data)
                hs = health_score(ss.data, z, m)
                try:
                    ss.narrative = narrative_ai.narrative(
                        ss.data, api_key, hs, materiality, ss.company,
                        redactor=make_redactor())
                except Exception as e:
                    st.error(f"Generation failed: {e}")
        if ss.narrative:
            st.markdown(f'<div class="fl-card">{ss.narrative}</div>',
                        unsafe_allow_html=True)

# ============================================================================
# TAB 6 — EXPORT
# ============================================================================
with tabs[5]:
    if ss.data is None:
        _need_data()
    else:
        st.markdown("### Export the full report")
        st.markdown('<p class="fl-note">Generates a formatted Word document containing the '
                    'health summary, ratios, SA 520 variance table, Auditor’s Lens and the '
                    'AI commentary — ready for the audit file.</p>', unsafe_allow_html=True)

        if ss.lens is None:
            st.warning("Tip: generate the Auditor's Lens first so it is included "
                       "in the report.", icon="💡")

        if st.button("📄 Build Word report", type="primary"):
            with st.spinner("Assembling the report…"):
                periods = [p for p in PERIODS if ss.data.get(p)]
                ratios = {p: compute_ratios(ss.data[p]) for p in periods}
                names = {"CY": "Current Yr", "PY": "Previous Yr", "PY2": "Yr −2"}
                rrows = []
                for grp, rl in RATIO_GROUPS.items():
                    for name in rl:
                        row = {"Group": grp, "Ratio": name}
                        for p in periods:
                            v = ratios[p].get(name)
                            row[names[p]] = round(v, 2) if v is not None else None
                        rrows.append(row)
                ratio_df = pd.DataFrame(rrows)
                z = altman_z(ss.data["CY"])
                m = beneish_m(ss.data)
                hs = health_score(ss.data, z, m)
                lens = ss.lens or narrative_ai.auditors_lens_fallback(ss.data, materiality)
                doc_bytes = build_report(ss.company, ratio_df,
                                         variance_table(ss.data, materiality),
                                         z, m, hs, lens, ss.narrative or "", ss.unit)
                st.download_button("⬇️ Download CentsSensibility_Report.docx", doc_bytes,
                                   f"CentsSensibility_Report_{ss.company.replace(' ', '_')}.docx",
                                   "application/vnd.openxmlformats-officedocument."
                                   "wordprocessingml.document")
                st.success("Report ready — click to download.")


# ============================================================================
# TAB 7 — PRIVACY
# ============================================================================
with tabs[6]:
    st.markdown("### 🔒 Privacy layer")
    st.markdown(
        '<p class="fl-note">Before any text reaches the AI, this app replaces names and '
        'identifiers with neutral tokens <i>on your computer</i>, checks the outgoing text '
        'again, and puts the real names back locally in the AI\'s answer.</p>',
        unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("**Names to mask** (one per line). The entity name from the sidebar is "
                    "always included.")
        ss.p_persons = st.text_area("Directors, signatories, KMP, promoters", ss.p_persons,
                                    height=110, placeholder="Mr. Rajesh Kumar\nMrs. Anita Nair")
        ss.p_orgs = st.text_area("Other organisations (auditors, bankers, group companies, "
                                 "subsidiaries)", ss.p_orgs, height=110,
                                 placeholder="XYZ & Associates\nState Bank of India")
        ss.p_addresses = st.text_area("Addresses / places (registered office, plants, cities)",
                                      ss.p_addresses, height=90,
                                      placeholder="12/34 MG Road, Kozhikode")
        ss.p_lines_on = st.toggle("Remove whole lines containing trigger words", ss.p_lines_on,
                                  help="Any line with one of these words is deleted entirely "
                                       "(and the next line too, if the line ends with a colon).")
        ss.p_lines = st.text_area("Trigger words (one per line)", ss.p_lines, height=150,
                                  disabled=not ss.p_lines_on,
                                  help="Whole-word, case-insensitive. Add e.g. Bankers, Folio, Auditor.")
        ss.p_cuts_on = st.toggle("Remove the signature block (everything after the audit-report line)",
                                 ss.p_cuts_on,
                                 help="Drops directors, auditor, membership no., UDIN, place and date "
                                      "that follow phrases like 'As per our report of even date' - "
                                      "to the end of that sheet or page.")
        ss.p_cuts = st.text_area("Cut from a line containing (one per line)", ss.p_cuts, height=80,
                                 disabled=not ss.p_cuts_on)
        ss.p_parts = st.checkbox("Also mask parts of names (e.g. surnames, the distinctive "
                                 "word in the company name)", ss.p_parts)
    with c2:
        st.markdown("**Always detected by pattern**")
        st.markdown(" ".join(f"`{k}`" for k, _ in redaction.describe_patterns()))
        st.caption("PAN, GSTIN, CIN, DIN, TAN, ISIN, UDIN, firm reg. no., membership no., "
                   "e-mail, phone, URL and PIN code — masked wherever they appear.")
        st.markdown("**Live test** — paste any text to see what would be sent:")
        sample = st.text_area("Test text", "", height=90, key="p_test",
                              placeholder="Paste a paragraph from the annual report…")
        if sample:
            if ss.privacy:
                r_ = make_redactor().redact(sample)
                st.code(r_.text, language=None)
            else:
                st.info("Turn Privacy mode on (sidebar) to test.")

    st.divider()
    st.markdown("**What this does — and does not — do**")
    st.markdown(
        "- ✅ Entity, director, organisation and address names, and Indian identifiers "
        "(PAN, GSTIN, CIN, DIN, TAN, ISIN, UDIN, FRN, membership no., e-mail, phone, URL) "
        "never leave your computer.\n"
        "- ✅ In Privacy mode the PDF **file** is never uploaded; only redacted text of the "
        "pages you choose is sent, after you approve it.\n"
        "- ✅ A final guard blocks any request that still contains a registered term.\n"
        "- ⚠️ **Redaction is not anonymisation.** Financial figures and the line items "
        "themselves are still sent, and an informed reader could infer the company from "
        "them. For truly sensitive engagements use the Excel route with Privacy mode on and "
        "the offline Auditor's Lens (no API key).\n"
        "- ⚠️ Scanned PDFs have no text layer and are not supported in Privacy mode.\n"
        "- ⚠️ Pattern detection is not perfect — always read the preview.")
