"""
NR Tax Advisor - Main Streamlit Application
AI-Powered Double Tax Treaty Advisory Suite for Chartered Accountants
Built under Income Tax Act, 2025 | Income Tax Rules, 2026
NR Tax Advisor | AICA Level 2 Capstone 2026
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="NR Tax Advisor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS — Executive Dark Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;800&family=Inter:wght@300;400;500;600&display=swap');

    :root {
        --bg:        #FFFFFF;
        --panel:     #F0F7F0;
        --panel-h:   #E8F5EE;
        --gold:      #1A6B3C;
        --gold-lt:   #2E9B5A;
        --gold-dim:  rgba(26,107,60,0.20);
        --gold-glow: rgba(26,107,60,0.08);
        --text:      #1A2E1A;
        --muted:     #4A7A5A;
        --grid:      rgba(26,107,60,0.04);
        --red:       #DC2626;
        --green:     #1A6B3C;
        --yellow:    #D97706;
    }

    /* App background — clean white with subtle green */
    .stApp {
        background-color: #FFFFFF;
    }
    html, body, [class*="css"] { color: var(--text); font-family: 'Inter', sans-serif; }

    /* Main header — dark executive panel */
    .main-header {
        background: linear-gradient(135deg, #1A6B3C 0%, #0F4A28 50%, #1A6B3C 100%);
        color: var(--text);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        border: 1px solid var(--gold-dim);
        box-shadow: 0 4px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(201,168,76,0.06);
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: "";
        position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent 0%, var(--gold) 30%, var(--gold-lt) 50%, var(--gold) 70%, transparent 100%);
        animation: hdr-shimmer 3s ease-in-out infinite;
    }
    .main-header::after {
        content: "";
        position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, var(--gold-dim), transparent);
    }
    @keyframes hdr-shimmer {
        0%, 100% { opacity: 0.5; }
        50%       { opacity: 1.0; }
    }
    .main-header h1 {
        color: var(--gold);
        margin: 0; font-size: 2.2rem;
        font-family: 'Orbitron', sans-serif; font-weight: 800;
        letter-spacing: 2px;
        text-shadow: 0 0 30px rgba(201,168,76,0.25);
    }
    .main-header p {
        color: var(--muted); margin: 0.5rem 0 0; font-size: 0.875rem;
        font-family: 'Inter', sans-serif; font-weight: 300; letter-spacing: 0.3px;
    }
    .main-header .brand-tag {
        display: inline-block; margin-top: 0.8rem;
        font-family: 'Orbitron', sans-serif; font-size: 0.7rem;
        letter-spacing: 3px; color: #FFFFFF;
        background: linear-gradient(135deg, var(--gold), var(--gold-lt));
        padding: 4px 14px; border-radius: 3px; font-weight: 700;
    }

    /* Risk badges */
    .risk-low  { background: rgba(63,185,80,0.10);  color: #3FB950; padding: 6px 14px;
                 border-radius: 4px; font-weight: 600; font-size: 0.85rem;
                 border: 1px solid rgba(63,185,80,0.30);  font-family: 'Inter', sans-serif; }
    .risk-med  { background: rgba(227,179,65,0.10);  color: #E3B341; padding: 6px 14px;
                 border-radius: 4px; font-weight: 600; font-size: 0.85rem;
                 border: 1px solid rgba(227,179,65,0.30); font-family: 'Inter', sans-serif; }
    .risk-high { background: rgba(248,81,73,0.10);   color: #F85149; padding: 6px 14px;
                 border-radius: 4px; font-weight: 600; font-size: 0.85rem;
                 border: 1px solid rgba(248,81,73,0.30);  font-family: 'Inter', sans-serif; }

    /* Info boxes */
    .ita-box {
        background: #F0F7F0; border-left: 4px solid #1A6B3C;
        border-top: 1px solid rgba(26,107,60,0.20); border-right: 1px solid rgba(26,107,60,0.20);
        border-bottom: 1px solid rgba(26,107,60,0.20);
        padding: 0.9rem 1.2rem; border-radius: 0 8px 8px 0;
        margin: 0.8rem 0; font-size: 0.85rem; color: #1A2E1A;
        font-family: 'Inter', sans-serif;
    }
    .warning-box {
        background: rgba(248,81,73,0.06); border-left: 3px solid var(--red);
        border-top: 1px solid rgba(248,81,73,0.15); border-right: 1px solid rgba(248,81,73,0.15);
        border-bottom: 1px solid rgba(248,81,73,0.15);
        padding: 0.9rem 1.2rem; border-radius: 0 8px 8px 0;
        margin: 0.8rem 0; font-size: 0.85rem; color: var(--red);
        font-family: 'Inter', sans-serif;
    }
    .success-box {
        background: rgba(63,185,80,0.06); border-left: 3px solid var(--green);
        border-top: 1px solid rgba(63,185,80,0.15); border-right: 1px solid rgba(63,185,80,0.15);
        border-bottom: 1px solid rgba(63,185,80,0.15);
        padding: 0.9rem 1.2rem; border-radius: 0 8px 8px 0;
        margin: 0.8rem 0; font-size: 0.85rem; color: var(--green);
        font-family: 'Inter', sans-serif;
    }

    /* Metric cards */
    .metric-card {
        background: var(--panel); border: 1px solid var(--gold-dim);
        border-radius: 10px; padding: 1.2rem 1rem; text-align: center;
        box-shadow: 0 2px 16px rgba(0,0,0,0.3);
        transition: all 0.3s ease; position: relative; overflow: hidden;
    }
    .metric-card::before {
        content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, var(--gold), transparent);
    }
    .metric-card:hover {
        border-color: rgba(201,168,76,0.5);
        box-shadow: 0 4px 24px rgba(201,168,76,0.15); transform: translateY(-2px);
    }
    .metric-card h3 {
        color: var(--gold); font-size: 2rem; margin: 0;
        font-family: 'Orbitron', sans-serif; font-weight: 700;
        text-shadow: 0 0 20px rgba(201,168,76,0.25);
    }
    .metric-card p {
        color: var(--muted); font-size: 0.72rem; margin: 0.4rem 0 0;
        font-family: 'Inter', sans-serif; letter-spacing: 1.5px;
        text-transform: uppercase; font-weight: 500;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1A6B3C, #0F4A28);
        border-right: 1px solid var(--gold-dim);
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, var(--gold), var(--gold-lt));
        color: #FFFFFF; font-family: 'Orbitron', sans-serif; font-weight: 700;
        border: none; border-radius: 6px; letter-spacing: 0.8px;
        box-shadow: 0 2px 16px rgba(201,168,76,0.25);
        transition: all 0.3s ease; font-size: 0.8rem;
    }
    .stButton > button:hover {
        box-shadow: 0 4px 24px rgba(201,168,76,0.45);
        transform: translateY(-2px);
        background: linear-gradient(135deg, var(--gold-lt), var(--gold));
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--panel); border-radius: 8px 8px 0 0;
        border-bottom: 1px solid var(--gold-dim); gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif; color: var(--muted);
        font-size: 0.8rem; font-weight: 500;
        border-bottom: 2px solid transparent; transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        color: var(--gold) !important;
        border-bottom-color: var(--gold) !important;
        background: var(--gold-glow) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--gold-lt) !important; background: var(--gold-glow) !important;
    }

    /* Output area */
    .output-box-old {
        background: var(--panel); border: 1px solid var(--gold-dim);
        border-left: 3px solid var(--gold);
        border-radius: 8px; padding: 1.5rem;
        font-family: 'Inter', sans-serif; line-height: 1.8;
        color: var(--text); box-shadow: 0 2px 16px rgba(0,0,0,0.2);
    }

    /* Headings */
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: var(--gold); }

    /* Inputs */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background: var(--panel) !important; border-color: var(--gold-dim) !important;
        color: var(--text) !important; border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* st.metric native */
    [data-testid="metric-container"] {
        background: var(--panel); border: 1px solid var(--gold-dim);
        border-radius: 10px; padding: 1rem;
    }
    [data-testid="metric-container"] [data-testid="stMetricLabel"] { color: var(--muted) !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: var(--gold) !important; font-family: 'Orbitron', sans-serif;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: var(--panel) !important; color: var(--text) !important;
        border: 1px solid var(--gold-dim) !important; border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Dividers */
    hr { border-color: var(--gold-dim) !important; }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--gold-dim); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--gold); }

    /* Captions */
    .stCaption { color: var(--muted) !important; font-family: 'Inter', sans-serif !important; }

    /* st.info / st.success / st.warning / st.error — native alert boxes
       (these default to light backgrounds and were left unstyled, which is
       why they showed up as solid white blocks against the dark theme) */
    [data-testid="stAlert"] {
        background: var(--panel) !important;
        border: 1px solid var(--gold-dim) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stAlert"] p { color: var(--text) !important; }
    [data-testid="stAlertContentInfo"]    { border-left: 3px solid var(--gold) !important; }
    [data-testid="stAlertContentSuccess"] { border-left: 3px solid var(--green) !important; }
    [data-testid="stAlertContentWarning"] { border-left: 3px solid var(--yellow) !important; }
    [data-testid="stAlertContentError"]   { border-left: 3px solid var(--red) !important; }

    /* Dropdown / select menus render in a portal outside .stApp, so they
       need to be targeted separately or they fall back to white */
    div[data-baseweb="popover"] ul[data-baseweb="menu"],
    div[data-baseweb="select"] div[role="listbox"] {
        background: var(--panel) !important;
        border: 1px solid var(--gold-dim) !important;
    }
    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li {
        background: var(--panel) !important;
        color: var(--text) !important;
    }
    div[data-baseweb="popover"] li:hover {
        background: var(--gold-glow) !important;
    }

    /* Radio / checkbox labels */
    .stRadio label, .stCheckbox label, .stMultiSelect label,
    .stSelectbox label, .stTextInput label, .stTextArea label,
    .stNumberInput label, .stDateInput label, .stFileUploader label {
        color: var(--text) !important; font-family: 'Inter', sans-serif !important;
    }
    .stRadio [role="radiogroup"] label span,
    .stCheckbox label span { color: var(--text) !important; }

    /* Multiselect selected-item tags */
    .stMultiSelect [data-baseweb="tag"] {
        background: var(--gold-dim) !important; color: var(--text) !important;
    }

    /* File uploader dropzone */
    [data-testid="stFileUploaderDropzone"] {
        background: var(--panel) !important; border: 1px dashed var(--gold-dim) !important;
    }
    [data-testid="stFileUploaderDropzone"] * { color: var(--muted) !important; }

    /* Date input */
    .stDateInput input {
        background: var(--panel) !important; color: var(--text) !important;
        border-color: var(--gold-dim) !important;
    }

    /* Expander body */
    .streamlit-expanderContent {
        background: rgba(22,27,34,0.6) !important; color: var(--text) !important;
        border: 1px solid var(--gold-dim) !important; border-top: none !important;
    }

    /* st.dataframe / st.table wrapper */
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        background: var(--panel) !important; border-radius: 8px;
        border: 1px solid var(--gold-dim);
    }

    /* Sidebar text + widgets */
    section[data-testid="stSidebar"] * { color: var(--text); }
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        background: var(--panel-h) !important; border-color: var(--gold-dim) !important;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Hide sidebar completely */
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    .css-1d391kg { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

</style>
""", unsafe_allow_html=True)

# ── OPENING SOUND (plays a short chime once when the app loads) ────────────
_CHIME_B64 = "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"
st.markdown(f"""
""", unsafe_allow_html=True)


# ── MARKDOWN STRIPPER — for clean plain text downloads ───────────────────────
def strip_markdown(text):
    import re
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'^---+$', '─' * 60, text, flags=re.MULTILINE)
    text = re.sub(r'^\|[-| :]+\|$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|(.+)\|$', lambda m: '  '.join(
        c.strip() for c in m.group(1).split('|') if c.strip()
    ), text, flags=re.MULTILINE)
    text = re.sub(r'`{1,3}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── IMPORTS (lazy to handle missing packages gracefully) ──────────────────
def import_modules():
    try:
        from treaty_reader import (get_available_treaties, get_all_treaty_names,
                                   detect_country_from_filename, TREATIES_FOLDER)
        from advisor import (generate_advisory, generate_notice_reply,
                             generate_rate_comparison, classify_form_145,
                             get_claude_client)
        return True, get_available_treaties, get_all_treaty_names, \
               detect_country_from_filename, TREATIES_FOLDER, \
               generate_advisory, generate_notice_reply, \
               generate_rate_comparison, classify_form_145, get_claude_client
    except ImportError as e:
        return False, str(e), None, None, None, None, None, None, None, None


result = import_modules()
MODULES_OK = result[0]


# ── HEADER ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="position:relative;overflow:hidden;background:linear-gradient(135deg,#1A6B3C 0%,#0F4A28 60%,#1A6B3C 100%);padding:1.4rem 1.8rem;border-radius:12px;margin-bottom:0.8rem;">
    <div style="position:absolute;top:0;right:0;bottom:0;width:38%;opacity:0.12;background:url('data:image/png;base64,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') center/cover no-repeat;"></div>
    <div style="position:relative;z-index:2;display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap;">
        <img src="data:image/png;base64,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" style="height:52px;width:auto;border-radius:8px;background:white;padding:4px;flex-shrink:0;" />
        <div style="flex:1;min-width:200px;">
            <div style="display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;">
                <span style="font-size:1.7rem;font-weight:800;color:#FFFFFF;font-family:'Orbitron',sans-serif;letter-spacing:2px;">⚖️ NR TAX ADVISOR</span>
                <img src="data:image/png;base64,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" style="height:24px;width:auto;border-radius:3px;" />
            </div>
            <p style="margin:0.35rem 0 0;color:#C6E9D4;font-size:0.85rem;font-family:'Inter',sans-serif;">
                AI-Powered Double Tax Treaty Advisory Suite &nbsp;|&nbsp; Built under Income Tax Act, 2025 &nbsp;|&nbsp; Income Tax Rules, 2026
            </p>
        </div>
        <div style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.35);border-radius:6px;padding:0.35rem 1rem;font-family:'Orbitron',sans-serif;font-size:0.68rem;letter-spacing:2px;color:#FFFFFF;font-weight:700;flex-shrink:0;white-space:nowrap;">
            BESPOKE TAX ADVISORS
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── WORLD CLOCK (self-contained component so the live-updating script runs) ─
_WORLD_CLOCK_HTML = """
<div style="font-family:'Inter', sans-serif;">
<div id="world-clock" style="display:flex;flex-wrap:wrap;gap:0.6rem;">
    <div class="wc-card" data-tz="Asia/Kolkata" data-city="India (IST)"></div>
    <div class="wc-card" data-tz="America/New_York" data-city="USA (EST/EDT)"></div>
    <div class="wc-card" data-tz="Europe/London" data-city="UK (GMT/BST)"></div>
    <div class="wc-card" data-tz="Asia/Dubai" data-city="UAE (GST)"></div>
    <div class="wc-card" data-tz="Asia/Singapore" data-city="Singapore (SGT)"></div>
    <div class="wc-card" data-tz="Australia/Sydney" data-city="Australia (AEST/AEDT)"></div>
</div>
</div>
<style>
    body { margin: 0; background: transparent; }
    .wc-card { background: #F0F7F0; border: 1px solid rgba(26,107,60,0.25); border-radius: 8px;
               padding: 0.55rem 0.9rem; min-width: 128px; text-align: center;
               box-shadow: 0 2px 12px rgba(0,0,0,0.4); }
    .wc-city { font-family: 'Inter', sans-serif; font-size: 0.68rem;
               letter-spacing: 0.8px; text-transform: uppercase; color: #4A7A5A; font-weight: 500; }
    .wc-time { font-family: 'Orbitron', sans-serif; font-size: 1.1rem;
               font-weight: 700; color: #1A6B3C; margin-top: 2px;
               text-shadow: 0 0 6px rgba(26,107,60,0.15); }
    .wc-date { font-family: 'Inter', sans-serif; font-size: 0.62rem;
               color: #4A7A5A; margin-top: 1px; font-weight: 400; }
</style>
<script>
(function() {
    var cards = document.querySelectorAll("#world-clock .wc-card");
    cards.forEach(function(card) {
        var city = card.getAttribute("data-city");
        card.innerHTML = '<div class="wc-city">' + city + '</div>' +
                          '<div class="wc-time">--:--:--</div>' +
                          '<div class="wc-date">--</div>';
    });
    function tick() {
        var now = new Date();
        cards.forEach(function(card) {
            var tz = card.getAttribute("data-tz");
            try {
                var timeStr = new Intl.DateTimeFormat("en-GB", {
                    timeZone: tz, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
                }).format(now);
                var dateStr = new Intl.DateTimeFormat("en-GB", {
                    timeZone: tz, day: "2-digit", month: "short", year: "numeric"
                }).format(now);
                card.querySelector(".wc-time").textContent = timeStr;
                card.querySelector(".wc-date").textContent = dateStr;
            } catch (e) { /* timezone lookup unsupported in this browser */ }
        });
    }
    tick();
    setInterval(tick, 1000);
})();
</script>
"""
components.html(_WORLD_CLOCK_HTML, height=110, scrolling=False)




# ITA 2025 banner
st.markdown("""
<div class="ita-box">
<b>ITA 2025 Active:</b> Form 145 (replaces 15CA) &nbsp;|&nbsp;
Form 146 (replaces 15CB) &nbsp;|&nbsp;
Form 41 mandatory (replaces Form 10F) &nbsp;|&nbsp;
Section 393 (replaces Section 195) &nbsp;|&nbsp;
Rule 220(3) exempt list — 33 categories
</div>
""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────
# Load API key silently from Streamlit Secrets
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
else:
    os.environ.pop("ANTHROPIC_API_KEY", None)

# Treaties path — used across tabs
treaties_path = Path(__file__).parent / "treaties"


# ── STATS ROW ─────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="metric-card"><h3>25</h3><p>Indian DTAAs</p></div>',
                unsafe_allow_html=True)
with col2:
    treaties_path = Path(__file__).parent / "treaties"
    count = len(list(treaties_path.glob("*.pdf"))) if treaties_path.exists() else 0
    st.markdown(f'<div class="metric-card"><h3>{count}</h3><p>PDFs Loaded</p></div>',
                unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><h3>5</h3><p>Core Modules</p></div>',
                unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-card"><h3>&lt;10m</h3><p>Per Advisory</p></div>',
                unsafe_allow_html=True)

st.markdown("---")


# ── TABS ──────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔍 DTAA Rate Lookup",
    "📋 AI Advisory",
    "📄 Form 145 Classifier",
    "📨 Notice Reply Drafter",
    "📚 Treaty Search",
    "📝 Form 145 Draft",
    "🏛️ Form 146 Draft",
    "📋 Form 41 Template",
    "🌐 Residential Status"
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — DTAA RATE LOOKUP
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 🔍 DTAA Rate Comparator")
    st.caption("Compare DTAA rates vs domestic Section 393 rates. "
               "Green = DTAA beneficial. ⚠️ = Use domestic rate.")

    # Rate database
    rate_data = {
        "Country": ["USA", "UK", "UAE", "Singapore", "Mauritius", "Germany",
                    "Japan", "Canada", "Australia", "Netherlands", "France",
                    "Switzerland", "Hong Kong", "Malaysia", "China",
                    "New Zealand", "South Africa", "Sri Lanka", "Thailand", "Italy"],
        "Dividend DTAA%": [15, 15, 10, 15, "Nil", 10, 10, 15, 15, 10,
                            10, 10, 5, 10, 10, 15, 10, 15, 15, 15],
        "Interest DTAA%": [15, 15, 12.5, 15, "Nil", 10, 10, 15, 15, 10,
                            10, 10, 10, 10, 10, 10, 10, 10, 15, 15],
        "Royalty DTAA%": [15, 15, 10, 10, 15, 10, 10, 15, 10, 10,
                           10, 10, 10, 10, 10, 10, 10, 10, 15, 20],
        "FTS DTAA%": [15, 15, "N/A", 10, "N/A", 10, 10, 15, 10, 10,
                       10, 10, 10, 10, 10, "N/A", 10, 10, 15, 20],
        "Cap Gains DTAA%": ["Domestic", "Domestic", "Exempt", "Domestic",
                             "Domestic*", "Domestic", "Domestic", "Domestic",
                             "Domestic", "Domestic", "Domestic", "Domestic",
                             "Exempt", "Exempt", "Domestic", "Domestic",
                             "Domestic", "Domestic", "Domestic", "Domestic"],
        "MLI": ["No", "Yes", "Yes", "Yes", "Yes", "Yes", "No", "Yes", "Yes",
                 "Yes", "Yes", "Yes", "No", "Yes", "Partial", "Yes",
                 "No", "No", "No", "Yes"],
        "GAAR Risk": ["LOW", "MEDIUM", "MEDIUM", "MEDIUM", "HIGH", "MEDIUM",
                       "LOW", "MEDIUM", "MEDIUM", "MEDIUM", "MEDIUM", "MEDIUM",
                       "LOW", "MEDIUM", "MEDIUM", "LOW", "LOW", "LOW",
                       "LOW", "MEDIUM"],
    }

    df = pd.DataFrame(rate_data)

    col_a, col_b = st.columns([1, 2])
    with col_a:
        selected_country = st.selectbox(
            "Select Country",
            options=["All Countries"] + df["Country"].tolist()
        )
        income_filter = st.selectbox(
            "Income Type",
            ["All", "Dividend", "Interest", "Royalty", "FTS", "Capital Gains"]
        )

    with col_b:
        # Domestic rates reference
        st.markdown("""
        <div class="ita-box">
        <b>Domestic Rates (Section 393 ITA 2025):</b><br>
        Dividend: 20% + SC + Cess &nbsp;|&nbsp;
        Interest: 20% + SC + Cess &nbsp;|&nbsp;
        Royalty: 10% + SC + Cess &nbsp;|&nbsp;
        FTS: 10% + SC + Cess &nbsp;|&nbsp;
        Capital Gains: 12.5% (LTCG Sec 112A) / 20% (STCG)
        </div>
        """, unsafe_allow_html=True)

        if selected_country == "Italy":
            st.markdown("""
            <div class="warning-box">
            ⚠️ <b>Italy Royalty Trap:</b> DTAA rate is 20% vs domestic 10%.
            Always use domestic rate for India-Italy royalty payments.
            </div>
            """, unsafe_allow_html=True)

        if selected_country == "Mauritius" and income_filter in ["Capital Gains", "All"]:
            st.markdown("""
            <div class="warning-box">
            ⚠️ <b>Mauritius Capital Gains:</b> Post-2016 Protocol — shares acquired after 1 April 2017
            taxable at full domestic rate (12.5% LTCG). Grandfathering only for pre-April 2017 acquisitions.
            HIGH GAAR risk — substance in Mauritius must be demonstrated.
            </div>
            """, unsafe_allow_html=True)

    # Display table
    if selected_country != "All Countries":
        display_df = df[df["Country"] == selected_country]
    else:
        display_df = df

    # Filter columns based on income type
    if income_filter == "Dividend":
        display_df = display_df[["Country", "Dividend DTAA%", "MLI", "GAAR Risk"]]
    elif income_filter == "Interest":
        display_df = display_df[["Country", "Interest DTAA%", "MLI", "GAAR Risk"]]
    elif income_filter == "Royalty":
        display_df = display_df[["Country", "Royalty DTAA%", "MLI", "GAAR Risk"]]
    elif income_filter == "FTS":
        display_df = display_df[["Country", "FTS DTAA%", "MLI", "GAAR Risk"]]
    elif income_filter == "Capital Gains":
        display_df = display_df[["Country", "Cap Gains DTAA%", "MLI", "GAAR Risk"]]

    # Color code GAAR risk
    def color_gaar(val):
        colors = {"HIGH": "background-color: #FCE4D6; color: #9C0006",
                  "MEDIUM": "background-color: #FFF2CC; color: #7D6608",
                  "LOW": "background-color: #E2EFDA; color: #375623"}
        return colors.get(val, "")

    if "GAAR Risk" in display_df.columns:
        styled_df = display_df.style.map(color_gaar, subset=["GAAR Risk"])
    else:
        styled_df = display_df.style
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    if selected_country != "All Countries":
        row = df[df["Country"] == selected_country].iloc[0]
        st.markdown("#### Key Notes")
        c1, c2, c3 = st.columns(3)
        with c1:
            risk = row["GAAR Risk"]
            icon = "🔴" if risk == "HIGH" else "🟡" if risk == "MEDIUM" else "🟢"
            st.metric("GAAR Risk", f"{icon} {risk}")
        with c2:
            st.metric("MLI Applies", "✅ Yes" if row["MLI"] == "Yes" else "❌ No")
        with c3:
            st.metric("Form 41", "✅ Mandatory")

        # AI Rate Analysis button
        if st.button(f"🤖 Get AI Rate Analysis for {selected_country}", type="primary"):
            with st.spinner(f"Analysing India-{selected_country} DTAA rates..."):
                try:
                    from advisor import generate_rate_comparison
                    result = generate_rate_comparison(selected_country)
                    st.markdown("#### AI Rate Analysis")
                    st.markdown(
                        f'<div class="output-box">{result}</div>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI ADVISORY
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📋 AI-Powered NR Tax Advisory")
    st.caption("Describe your cross-border transaction. "
               "The AI reads the actual treaty PDF and generates a structured advisory.")

    col1, col2 = st.columns(2)
    with col1:
        adv_country = st.selectbox(
            "Country of Payee/Recipient",
            ["USA", "UK", "UAE", "Singapore", "Mauritius", "Germany",
             "Japan", "Canada", "Australia", "Netherlands", "France",
             "Switzerland", "Hong Kong", "Malaysia", "China",
             "New Zealand", "South Africa", "Sri Lanka", "Thailand", "Italy"],
            key="adv_country"
        )
        adv_income = st.selectbox(
            "Nature of Income",
            ["Royalty / Software Licence", "Fees for Technical Services (FTS)",
             "Dividend", "Interest", "Capital Gains", "Salary / Employment Income",
             "Business Profits / PE income", "Other Income"],
            key="adv_income"
        )

    with col2:
        adv_amount = st.number_input(
            "Transaction Amount (Rs. Lakhs)",
            min_value=0.0, value=25.0, step=1.0
        )
        adv_trc = st.selectbox(
            "TRC Available?",
            ["Yes — TRC obtained", "No — TRC not yet obtained",
             "In process of obtaining"]
        )

    adv_details = st.text_area(
        "Transaction Details",
        placeholder="Describe the transaction: e.g. Indian company paying annual software licence "
                    "fee of Rs. 25 lakhs to a US-based company. Services involve use of proprietary "
                    "software under EULA. No copyright rights transferred.",
        height=100
    )

    use_treaty_pdf = st.checkbox(
        "📄 Use actual treaty PDF for analysis (recommended)",
        value=True
    )

    # Demo scenarios

    if st.button("🤖 Generate NR Tax Advisory", type="primary", key="gen_advisory"):
        if not adv_details.strip():
            st.warning("Please describe the transaction details.")

        else:
            income_map = {
                "Royalty / Software Licence": "royalty",
                "Fees for Technical Services (FTS)": "fts",
                "Dividend": "dividend",
                "Interest": "interest",
                "Capital Gains": "capital gains",
                "Salary / Employment Income": "salary",
                "Business Profits / PE income": "business profits",
                "Other Income": "other"
            }
            income_type = income_map.get(adv_income, adv_income.lower())
            full_details = (f"{adv_details}\n\nAmount: Rs. {adv_amount} lakhs. "
                           f"TRC status: {adv_trc}.")

            with st.spinner("Reading treaty PDF and generating advisory... (20-30 seconds)"):
                try:
                    from advisor import generate_advisory
                    result = generate_advisory(
                        adv_country, income_type,
                        full_details, use_treaty_pdf
                    )
                    st.markdown("#### Advisory Output")
                    st.markdown(result)
                    st.download_button(
                        "📥 Download Advisory as Text",
                        data=strip_markdown(result),
                        file_name=f"DTAA_Advisory_{adv_country}_{income_type}.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Error generating advisory: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — FORM 145 CLASSIFIER
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📄 Form 145 / Form 146 Classifier")
    st.markdown("""
    <div class="ita-box">
    <b>ITA 2025 Update (w.e.f. 1 April 2026):</b>
    Form 15CA → <b>Form 145</b> &nbsp;|&nbsp;
    Form 15CB → <b>Form 146</b> &nbsp;|&nbsp;
    Rule 37BB → <b>Rule 220(3)</b> (33 exempt categories) &nbsp;|&nbsp;
    Form 10F → <b>Form 41</b> (mandatory)
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        f_payment = st.selectbox(
            "Nature of Payment",
            ["Royalty / Software Licence", "Fees for Technical Services",
             "Dividend to NRI", "Interest to NR Lender",
             "Capital Gains (NR seller)", "Salary to NR Employee",
             "Import of Goods", "Professional Services",
             "Rent of Foreign Property", "Partnership Profit",
             "RBI Exempt List Payment"]
        )
    with col2:
        f_amount = st.number_input("Amount (Rs. Lakhs)", min_value=0.0, value=10.0)
    with col3:
        f_taxable = st.selectbox(
            "Taxable in India?",
            ["Yes — chargeable to tax", "No — not chargeable", "Exempt under Rule 220(3)"]
        )

    f_dtaa = st.selectbox(
        "DTAA Benefit Claimed?",
        ["Yes — DTAA rate applied", "No — domestic rate applied",
         "Nil TDS — Article 7 (Business Profits, no PE)"]
    )

    # Instant classification logic
    st.markdown("#### Instant Classification")

    if f_payment == "Import of Goods" or "Exempt" in f_taxable:
        part = "PART D"
        part_color = "#DDEBF7"
        part_text_color = "#185FA5"
        form146 = "❌ Not Required"
        form41 = "❌ Not Required"
        note = "RBI exempt list under Rule 220(3) — No Form 145 required at all."
    elif "not chargeable" in f_taxable and f_amount <= 5:
        part = "PART A"
        part_color = "#E2EFDA"
        part_text_color = "#375623"
        form146 = "❌ Not Required"
        form41 = "✅ Required if DTAA claimed"
        note = "Non-taxable, ≤ Rs. 5 lakh. Remitter files on portal. No CA required."
    elif "not chargeable" in f_taxable and f_amount > 5:
        part = "PART B"
        part_color = "#FFF2CC"
        part_text_color = "#7D6608"
        form146 = "✅ REQUIRED"
        form41 = "✅ Mandatory"
        note = "Non-taxable but > Rs. 5 lakh. AO certificate OR Form 146 needed."
    else:
        part = "PART C"
        part_color = "#FCE4D6"
        part_text_color = "#9C0006"
        form146 = "✅ REQUIRED — Upload BEFORE Form 145 Part C"
        form41 = "✅ MANDATORY under Rule 75 / Section 159(8) ITA 2025"
        note = "Chargeable remittance. Form 146 (CA Certificate) mandatory."

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        st.markdown(
            f'<div style="background:{part_color};color:{part_text_color};'
            f'padding:1rem;border-radius:8px;text-align:center;">'
            f'<b style="font-size:1.4rem">{part}</b><br>'
            f'<small>Form 145</small></div>',
            unsafe_allow_html=True
        )
    with col_r2:
        st.markdown(
            f'<div style="background:#F0F0F0;padding:1rem;border-radius:8px;">'
            f'<b>Form 146</b><br>{form146}</div>',
            unsafe_allow_html=True
        )
    with col_r3:
        st.markdown(
            f'<div style="background:#F0F0F0;padding:1rem;border-radius:8px;">'
            f'<b>Form 41 (ITA 2025)</b><br>{form41}</div>',
            unsafe_allow_html=True
        )
    with col_r4:
        st.markdown(
            f'<div style="background:#F0F0F0;padding:1rem;border-radius:8px;">'
            f'<b>TRC Required</b><br>{"✅ Yes" if "Not Required" not in form41 else "❌ No"}</div>',
            unsafe_allow_html=True
        )

    st.info(f"📌 {note}")

    if st.button("🤖 Get Detailed AI Classification", key="classify_btn"):
        with st.spinner("Generating detailed classification..."):
                try:
                    from advisor import classify_form_145
                    result = classify_form_145(f_payment, f_amount, f_taxable, f_dtaa)
                    st.markdown(
                        f'<div class="output-box">{result}</div>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — NOTICE REPLY DRAFTER
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 📨 IT Department Notice Reply Drafter")
    st.caption("Generate submission-ready formal replies citing treaty articles, "
               "Supreme Court judgments, and CBDT circulars.")

    col1, col2 = st.columns(2)
    with col1:
        n_country = st.selectbox(
            "Country of Foreign Entity",
            ["USA", "UK", "UAE", "Singapore", "Mauritius", "Germany",
             "Japan", "Canada", "Australia", "Netherlands", "France",
             "Switzerland", "Hong Kong", "Malaysia", "China"],
            key="n_country"
        )
        n_type = st.selectbox(
            "Notice Type",
            ["FTS / Royalty characterisation dispute",
             "PE allegation — Business Profits",
             "GAAR / Treaty Shopping challenge",
             "Short deduction / Non-deduction of TDS",
             "MFN clause dispute",
             "Beneficial ownership challenge",
             "Transfer Pricing adjustment"]
        )
    with col2:
        n_article = st.text_input(
            "Treaty Article in dispute",
            placeholder="e.g. Article 12 (FTS) vs Article 7 (Business Profits)"
        )
        n_section = st.text_input(
            "ITA 2025 Section",
            placeholder="e.g. Section 393"
        )

    n_facts = st.text_area(
        "Facts of the Case",
        placeholder="Describe: what payment was made, to whom, what TDS was deducted, "
                    "what is the department's objection, what documents were obtained...",
        height=120
    )

    if st.button("📝 Draft Notice Reply", type="primary", key="draft_notice"):
        if not n_facts.strip():
            st.warning("Please describe the facts of the case.")

        else:
            with st.spinner("Drafting formal reply (30-40 seconds)..."):
                try:
                    from advisor import generate_notice_reply
                    result = generate_notice_reply(n_type, n_country, n_facts, n_article)
                    st.markdown("#### Draft Notice Reply")
                    st.markdown(result)
                    st.download_button(
                        "📥 Download Reply as Text",
                        data=strip_markdown(result),
                        file_name=f"Notice_Reply_{n_country}_{n_type[:20]}.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — TREATY SEARCH
# ════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 📚 Treaty Text Search")
    st.caption("Search and view actual CBDT treaty text from the treaty library.")

    treaties_path = Path(__file__).parent / "treaties"

    if not treaties_path.exists():
        st.error("❌ Treaties folder not found")
        st.info("Add a 'treaties/' folder to your GitHub repository and commit your treaty PDFs into it.")
    else:
        pdfs = sorted([p for p in treaties_path.glob("*.pdf")
                       if "afghanistan" not in p.name.lower()])

        if not pdfs:
            st.warning("No PDF files found in the treaties/ folder in your repository.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                selected_pdf = st.selectbox(
                    "Select Treaty PDF",
                    options=[p.name for p in pdfs]
                )
            with col2:
                search_topic = st.text_input(
                    "Search Topic",
                    placeholder="e.g. royalties, dividends, permanent establishment, FTS"
                )

            if st.button("🔍 Search Treaty", key="search_treaty"):
                selected_path = treaties_path / selected_pdf
                with st.spinner("Reading PDF and finding relevant sections..."):
                        try:
                            from treaty_reader import (extract_text_from_pdf,
                                                        find_relevant_sections)
                            text = extract_text_from_pdf(selected_path, max_pages=80)

                            if search_topic:
                                relevant = find_relevant_sections(text, search_topic)
                                if relevant:
                                    st.success(f"✅ Found relevant sections for '{search_topic}'")
                                    st.markdown(f"#### Treaty Text — Results for '{search_topic}'")
                                    # Clean and display in scrollable text area
                                    clean_text = relevant.replace("---", "\n" + "─"*60 + "\n")
                                    st.text_area(
                                        label="Relevant Treaty Sections",
                                        value=clean_text,
                                        height=400,
                                        label_visibility="collapsed"
                                    )
                                    st.download_button(
                                        "📥 Download Treaty Extract",
                                        data=clean_text,
                                        file_name=f"Treaty_{selected_pdf[:20]}_{search_topic[:20]}.txt",
                                        mime="text/plain"
                                    )
                                else:
                                    st.info(f"No specific results for '{search_topic}'. Showing first 2000 characters.")
                                    st.text_area(
                                        label="Treaty Text",
                                        value=text[:2000],
                                        height=400,
                                        label_visibility="collapsed"
                                    )
                            else:
                                st.markdown("#### Treaty Text (first 3000 characters)")
                                st.text_area(
                                    label="Treaty Text",
                                    value=text[:3000],
                                    height=400,
                                    label_visibility="collapsed"
                                )

                        except Exception as e:
                            st.error(f"Error reading PDF: {str(e)}")

            # Show PDF info
            st.markdown("#### Available Treaties")
            pdf_info = []
            for p in pdfs:
                size_kb = p.stat().st_size // 1024
                pdf_info.append({
                    "File Name": p.name[:60],
                    "Size (KB)": size_kb,
                    "Type": "MLI Synthesised" if "synthes" in p.name.lower()
                            else "Comprehensive"
                })
            st.dataframe(pd.DataFrame(pdf_info), use_container_width=True, hide_index=True)




# ════════════════════════════════════════════════════════════════════════════
# TAB 6 — FORM 145 DRAFT GENERATOR
# ════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("### 📝 Form 145 Draft Generator")
    st.markdown("""
    <div class="ita-box">
    <b>ITA 2025:</b> Form 145 replaces Form 15CA (w.e.f. 1 April 2026) — Section 397(3)(d) |
    Rule 220 IT Rules 2026 | File on TRACES portal before remittance
    </div>
    """, unsafe_allow_html=True)
    st.caption("Generate a pre-filled Form 145 draft. CA to review and upload on TRACES portal.")

    col1, col2 = st.columns(2)
    with col1:
        f145_remitter_name = st.text_input("Remitter Name (Indian Entity)", placeholder="e.g. TechSoft Pvt Ltd")
        f145_remitter_pan = st.text_input("Remitter PAN", placeholder="e.g. AAACT1234A")
        f145_remitter_address = st.text_area("Remitter Address", height=80, placeholder="Full address with PIN")
        f145_country = st.selectbox("Country of Remittance", [
            "USA", "UK", "UAE", "Singapore", "Mauritius", "Germany",
            "Japan", "Canada", "Australia", "Netherlands", "France",
            "Switzerland", "Hong Kong", "Malaysia", "China", "New Zealand",
            "South Africa", "Sri Lanka", "Thailand", "Italy"
        ])
        f145_currency = st.selectbox("Currency", ["USD", "GBP", "AED", "EUR", "SGD", "JPY", "CAD", "AUD"])

    with col2:
        f145_payee_name = st.text_input("Payee Name (Foreign Entity)", placeholder="e.g. DataCorp LLC")
        f145_payee_address = st.text_area("Payee Address (Foreign)", height=80, placeholder="Full foreign address")
        f145_nature = st.selectbox("Nature of Remittance", [
            "Royalty / Software Licence",
            "Fees for Technical Services (FTS)",
            "Dividend",
            "Interest",
            "Capital Gains",
            "Salary / Employment Income",
            "Business Profits",
            "Other"
        ])
        f145_amount_foreign = st.number_input("Amount (Foreign Currency)", min_value=0.0, step=1000.0)
        f145_amount_inr = st.number_input("Amount (Rs. Lakhs)", min_value=0.0, step=0.5)
        f145_tds_rate = st.number_input("TDS Rate (%)", min_value=0.0, max_value=40.0, step=0.5, value=10.0)
        f145_part = st.selectbox("Form 145 Part", ["Part A", "Part B", "Part C", "Part D"])

    f145_dtaa = st.checkbox("DTAA Benefit Claimed", value=True)
    f145_trc = st.checkbox("TRC Obtained from Payee", value=True)
    f145_form41 = st.checkbox("Form 41 Obtained from Payee", value=True)
    f145_form146 = st.checkbox("Form 146 (CA Certificate) Obtained", value=True)
    f145_purpose = st.text_input("Purpose Code (RBI)", placeholder="e.g. P0802 for software royalty")
    f145_remarks = st.text_area("Additional Remarks", height=60)

    if st.button("📝 Generate Form 145 Draft", type="primary", key="gen_f145"):
        if not f145_remitter_name or not f145_payee_name:
            st.warning("Please fill Remitter Name and Payee Name.")
        else:
            tds_amount = (f145_amount_inr * f145_tds_rate / 100)
            net_remittance = f145_amount_inr - tds_amount

            draft = f"""
FORM 145 — DRAFT
[Under Section 397(3)(d) of Income Tax Act, 2025 read with Rule 220 of Income Tax Rules, 2026]
[Replaces erstwhile Form 15CA]

{'='*70}
FORM 145 — {f145_part.upper()}
{'='*70}

PART I — REMITTER DETAILS
Name of Remitter        : {f145_remitter_name}
PAN of Remitter         : {f145_remitter_pan or '[TO BE FILLED]'}
Address                 : {f145_remitter_address or '[TO BE FILLED]'}
Status                  : Company / Firm / Individual [select]
Residential Status      : Resident

PART II — PAYEE DETAILS
Name of Payee           : {f145_payee_name}
Address (Foreign)       : {f145_payee_address or '[TO BE FILLED]'}
Country of Residence    : {f145_country}
PAN / Tax ID            : [TO BE FILLED — Payee TIN]
Email                   : [TO BE FILLED]

PART III — REMITTANCE DETAILS
Nature of Remittance    : {f145_nature}
Currency                : {f145_currency}
Amount (Foreign Curr.)  : {f145_currency} {f145_amount_foreign:,.2f}
Amount (Indian Rs.)     : Rs. {f145_amount_inr:.2f} Lakhs
Purpose Code (RBI)      : {f145_purpose or '[TO BE FILLED]'}
Country of Remittance   : {f145_country}
Bank through which      : [TO BE FILLED — AD Bank Name and Branch]
  remittance is made
Date of Remittance      : [TO BE FILLED]

PART IV — TAX DEDUCTION DETAILS
Applicable Rate         : {f145_tds_rate}%
TDS Amount Deducted     : Rs. {tds_amount:.2f} Lakhs
Net Remittance Amount   : Rs. {net_remittance:.2f} Lakhs
TDS Challan No.         : [TO BE FILLED after TDS deposit]
BSR Code of Bank        : [TO BE FILLED]
Date of TDS Deposit     : [TO BE FILLED]

PART V — DTAA AND COMPLIANCE DETAILS
DTAA Benefit Claimed    : {'Yes' if f145_dtaa else 'No'}
Applicable DTAA         : India-{f145_country} DTAA
Applicable Article      : [TO BE FILLED — Article No.]
TRC Obtained            : {'Yes' if f145_trc else 'No'}
Form 41 Obtained        : {'Yes' if f145_form41 else 'No'}
Form 146 Obtained       : {'Yes' if f145_form146 else 'No — Obtain before filing'}
Form 146 Cert No.       : [TO BE FILLED — from CA]
Form 146 Date           : [TO BE FILLED]

PART VI — DECLARATION
I/We hereby declare that the information given above is true and correct
to the best of my/our knowledge and belief.

Name of Authorised Person : [TO BE FILLED]
Designation               : [TO BE FILLED]
Date                      : [TO BE FILLED]
Place                     : [TO BE FILLED]

{'='*70}
ADDITIONAL REMARKS: {f145_remarks or 'Nil'}
{'='*70}

IMPORTANT NOTES:
1. This is a DRAFT only. Review carefully before filing on TRACES portal.
2. Form 145 {f145_part} to be filed at: https://www.tdscpc.gov.in
3. Form 146 (CA Certificate) must be uploaded BEFORE Form 145 Part C/D.
4. Form 41 must be obtained from payee BEFORE remittance.
5. TDS to be deposited via Challan 281 within 7 days of deduction.
6. File Form 27Q quarterly return for TDS on non-resident payments.

ITA 2025 References:
- Section 397(3)(d) — Form 145 filing requirement
- Rule 220 IT Rules 2026 — Form 145 Parts A/B/C/D
- Section 393 — TDS on payments to non-residents
- Section 159(8) / Rule 75 — Form 41 mandatory

DISCLAIMER: This draft is for reference only. Actual Form 145 must be
filed on the TRACES portal (www.tdscpc.gov.in) by the authorised person.
Portal submission cannot be automated and requires DSC/OTP authentication.
"""
            st.markdown("#### Form 145 Draft")
            st.text_area("Draft Output", value=draft, height=500, label_visibility="collapsed")
            st.download_button(
                "📥 Download Form 145 Draft",
                data=draft,
                file_name=f"Form145_Draft_{f145_remitter_name[:15]}_{f145_country}.txt",
                mime="text/plain"
            )
            st.info("📌 Upload this on TRACES portal after review. Form 146 must be uploaded first.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 7 — FORM 146 DRAFT GENERATOR
# ════════════════════════════════════════════════════════════════════════════
with tab7:
    st.markdown("### 🏛️ Form 146 Draft Generator")
    st.markdown("""
    <div class="ita-box">
    <b>ITA 2025:</b> Form 146 replaces Form 15CB (w.e.f. 1 April 2026) — Section 397(3)(d) |
    Must be certified by a Practising Chartered Accountant | Upload on TRACES before Form 145
    </div>
    """, unsafe_allow_html=True)
    st.caption("Generate Form 146 CA Certificate draft. CA to review, certify with DSC and upload on TRACES.")


    col1, col2 = st.columns(2)
    with col1:
        f146_remitter = st.text_input("Remitter Name", placeholder="e.g. TechSoft Pvt Ltd", key="f146_rem")
        f146_remitter_pan = st.text_input("Remitter PAN", placeholder="e.g. AAACT1234A", key="f146_rpan")
        f146_payee = st.text_input("Payee Name (NR)", placeholder="e.g. DataCorp LLC", key="f146_pay")
        f146_country = st.selectbox("Country", [
            "USA", "UK", "UAE", "Singapore", "Mauritius", "Germany",
            "Japan", "Canada", "Australia", "Netherlands", "France",
            "Switzerland", "Hong Kong", "Malaysia", "China", "New Zealand"
        ], key="f146_cty")
        f146_nature = st.selectbox("Nature of Payment", [
            "Royalty / Software Licence",
            "Fees for Technical Services (FTS)",
            "Dividend", "Interest", "Capital Gains", "Business Profits"
        ], key="f146_nat")

    with col2:
        f146_amount = st.number_input("Amount (Rs. Lakhs)", min_value=0.0, step=0.5, key="f146_amt")
        f146_dtaa_article = st.text_input("Applicable DTAA Article", placeholder="e.g. Article 12", key="f146_art")
        f146_dtaa_rate = st.number_input("DTAA Rate (%)", min_value=0.0, max_value=40.0, step=0.5, key="f146_rate")
        f146_domestic_rate = st.number_input("Domestic Rate (%)", min_value=0.0, max_value=40.0, step=0.5, value=10.0, key="f146_dom")
        f146_applicable_rate = st.number_input("Applicable Rate (Lower of above) (%)", min_value=0.0, max_value=40.0, step=0.5, key="f146_app")
        f146_trc = st.selectbox("TRC Status", ["Obtained and Verified", "Not Obtained"], key="f146_trc")
        f146_form41 = st.selectbox("Form 41 Status", ["Obtained and Verified", "Not Obtained"], key="f146_f41")

    f146_ca_name = st.text_input("CA Name", placeholder="e.g. CA Vaishali Kapoor", key="f146_ca")
    f146_ca_memno = st.text_input("CA Membership Number", placeholder="e.g. 078991", key="f146_mem")
    f146_ca_firm = st.text_input("CA Firm Name", placeholder="e.g. Kapoor Kumar & Associates", key="f146_firm")
    f146_remarks = st.text_area("CA Remarks / Qualifications", height=80,
            placeholder="Any qualifications or conditions...", key="f146_rem2")

    if st.button("🏛️ Generate Form 146 Draft", type="primary", key="gen_f146"):
        if not f146_remitter or not f146_payee or not f146_ca_name:
            st.warning("Please fill Remitter, Payee, and CA Name.")
        else:
            tds_amount = f146_amount * f146_applicable_rate / 100

            draft146 = f"""
FORM 146 — DRAFT
[Under Section 397(3)(d) of Income Tax Act, 2025 read with Rule 220 of Income Tax Rules, 2026]
[Replaces erstwhile Form 15CB]
[To be certified by a Practising Chartered Accountant]

{'='*70}
CERTIFICATE UNDER SECTION 397(3)(d) OF INCOME TAX ACT, 2025
FORM 146 — CA CERTIFICATE
{'='*70}

I, {f146_ca_name}, Chartered Accountant, Membership No. {f146_ca_memno},
{f'Partner/Proprietor of {f146_ca_firm},' if f146_ca_firm else ''}
having been appointed to certify the particulars relating to remittance
by {f146_remitter} (PAN: {f146_remitter_pan or '[PAN]'}) hereby certify as follows:

PART I — DETAILS OF REMITTER
Name                    : {f146_remitter}
PAN                     : {f146_remitter_pan or '[TO BE FILLED]'}
Status                  : [Company / Firm / Individual]
Address                 : [TO BE FILLED]

PART II — DETAILS OF PAYEE / BENEFICIARY
Name                    : {f146_payee}
Country of Residence    : {f146_country}
Tax Identification No.  : [TO BE FILLED — Payee TIN in {f146_country}]
Address                 : [TO BE FILLED]

PART III — DETAILS OF REMITTANCE
Nature of Remittance    : {f146_nature}
Amount of Remittance    : Rs. {f146_amount:.2f} Lakhs
Currency                : [TO BE FILLED]
Purpose Code (RBI)      : [TO BE FILLED]
Proposed Date           : [TO BE FILLED]

PART IV — DTAA ANALYSIS AND RATE CERTIFICATION

Applicable DTAA         : India-{f146_country} Double Taxation Avoidance Agreement
Applicable Article      : {f146_dtaa_article or '[TO BE FILLED]'}
DTAA Rate               : {f146_dtaa_rate}% (as per {f146_dtaa_article or 'applicable article'})
Domestic Rate           : {f146_domestic_rate}% (Section 393 read with Section 115A ITA 2025)
More Beneficial Rate    : {f146_applicable_rate}% (being lower of DTAA and Domestic rate)
                          [Under Section 159(2) ITA 2025]

TDS Amount Certifiable  : Rs. {tds_amount:.2f} Lakhs

PART V — DOCUMENTATION VERIFICATION

Tax Residency Certificate (TRC): {f146_trc}
  - Issued by              : Tax Authority of {f146_country}
  - Period covered         : [TO BE FILLED]
  - Reference No.          : [TO BE FILLED]

Form 41 (erstwhile Form 10F): {f146_form41}
  - Submitted by           : {f146_payee}
  - Under Rule 75, Section 159(8) ITA 2025
  - Contains               : Status, Nationality, TIN, Period, Address ✓

PART VI — BENEFICIAL OWNERSHIP VERIFICATION
I hereby certify that based on my examination of available information
and documents, {f146_payee} is the beneficial owner of the above income
and is not a conduit entity.

PART VII — GAAR / PPT ASSESSMENT
Based on my examination, the transaction appears to be:
□ Commercially motivated and not primarily tax-driven
□ Beneficial ownership is clear and not challenged
□ No conduit arrangement is evident
□ MLI PPT / GAAR risk: [LOW / MEDIUM / HIGH — CA to assess]

PART VIII — CA CERTIFICATION

I hereby certify that:
(a) The information furnished above is based on the books of account,
    documents and other records produced before me;
(b) The proposed remittance is in accordance with the provisions of the
    Income Tax Act, 2025 and Income Tax Rules, 2026;
(c) The rate of TDS deducted/to be deducted is correct as per the
    applicable provisions;
(d) Form 41 and Tax Residency Certificate have been duly obtained and
    verified;
(e) To the best of my knowledge and belief, no information material to
    this certificate has been suppressed.

{'CA REMARKS / QUALIFICATIONS:' if f146_remarks else ''}
{f146_remarks if f146_remarks else ''}

Signature of Chartered Accountant: _______________
Name                              : {f146_ca_name}
Membership Number                 : {f146_ca_memno}
Firm Name                         : {f146_ca_firm or '[FIRM NAME]'}
FRN                               : [TO BE FILLED]
Date                              : [TO BE FILLED]
Place                             : [TO BE FILLED]
UDIN                              : [TO BE FILLED — Generate on ICAI portal]

{'='*70}
IMPORTANT NOTES FOR CA:
1. This draft requires your professional review before certification.
2. Generate UDIN on ICAI portal (www.udin.icai.org) before signing.
3. Upload on TRACES portal BEFORE Form 145 is filed.
4. This certificate is valid only with your DSC/OTP authentication.
5. Portal: https://www.tdscpc.gov.in

ITA 2025 References:
- Section 397(3)(d) — Form 146 certification requirement
- Rule 220 IT Rules 2026 — CA Certificate requirement
- Section 159(2) — Beneficial rate selection
- Section 159(8) / Rule 75 — Form 41 verification

DISCLAIMER: This is a DRAFT for reference. The certifying CA is solely
responsible for the accuracy of this certificate. Actual filing on
TRACES portal requires DSC authentication and cannot be automated.
{'='*70}
"""
            st.markdown("#### Form 146 Draft")
            st.text_area("Draft Output", value=draft146, height=500, label_visibility="collapsed")
            st.download_button(
                    "📥 Download Form 146 Draft",
                    data=draft146,
                    file_name=f"Form146_Draft_{f146_remitter[:15]}_{f146_country}.txt",
                    mime="text/plain"
                )
            st.warning("⚠️ CA must review, generate UDIN, sign with DSC and upload on TRACES portal.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 8 — FORM 41 TEMPLATE GENERATOR
# ════════════════════════════════════════════════════════════════════════════
with tab8:
    st.markdown("### 📋 Form 41 Template Generator")
    st.markdown("""
    <div class="ita-box">
    <b>ITA 2025:</b> Form 41 replaces Form 10F (w.e.f. 1 April 2026) — Rule 75, Section 159(8) |
    MANDATORY for ALL DTAA benefit claims | To be furnished by Non-Resident payee
    </div>
    """, unsafe_allow_html=True)
    st.caption("Generate Form 41 data collection template to send to your non-resident payee.")

    col1, col2 = st.columns(2)
    with col1:
        f41_payee_name = st.text_input("Payee Name (NR Entity)", placeholder="e.g. DataCorp LLC", key="f41_name")
        f41_country = st.selectbox("Country of Residence", [
            "USA", "UK", "UAE", "Singapore", "Mauritius", "Germany",
            "Japan", "Canada", "Australia", "Netherlands", "France",
            "Switzerland", "Hong Kong", "Malaysia", "China", "New Zealand"
        ], key="f41_cty")
        f41_status = st.selectbox("Status of Payee", [
            "Company", "Firm", "Individual", "Trust", "LLP", "LLC", "Other"
        ], key="f41_status")
        f41_nature = st.selectbox("Nature of Income", [
            "Royalty / Software Licence",
            "Fees for Technical Services",
            "Dividend", "Interest", "Capital Gains", "Business Profits"
        ], key="f41_nat")

    with col2:
        f41_dtaa_article = st.text_input("DTAA Article being claimed",
            placeholder="e.g. Article 12 — Royalties", key="f41_art")
        f41_fy = st.text_input("Financial Year", value="2025-26", key="f41_fy")
        f41_remitter = st.text_input("Indian Remitter Name", placeholder="e.g. TechSoft Pvt Ltd", key="f41_rem")
        f41_ca_name = st.text_input("CA Name (for letter)", placeholder="e.g. CA Vaishali Kapoor", key="f41_ca")

    if st.button("📋 Generate Form 41 Template", type="primary", key="gen_f41"):
        if not f41_payee_name or not f41_remitter:
            st.warning("Please fill Payee Name and Remitter Name.")
        else:
            template41 = f"""
FORM 41 — DATA COLLECTION TEMPLATE
[Under Rule 75 read with Section 159(8) of Income Tax Act, 2025]
[Replaces erstwhile Form 10F]
[To be completed by Non-Resident Payee and returned to Indian Remitter]

{'='*70}
REQUEST FOR FORM 41 PARTICULARS
{'='*70}

Date: [TO BE FILLED by {f41_payee_name}]

To,
The Authorised Signatory
{f41_payee_name}
{f41_country}

Sub: Request for Form 41 Particulars under Section 159(8) of ITA 2025

Dear Sir/Madam,

We, {f41_remitter}, are required to deduct TDS on the payment to be made
to you under Section 393 of the Income Tax Act, 2025.

To avail the benefit of India-{f41_country} DTAA under {f41_dtaa_article},
we are required to obtain the following particulars from you in Form 41
as mandated by Rule 75 of Income Tax Rules, 2026.

Please furnish the following information:

{'='*70}
FORM 41 — PARTICULARS TO BE FURNISHED BY {f41_payee_name.upper()}
{'='*70}

MANDATORY FIELDS (Rule 75, Section 159(8) ITA 2025):

1. STATUS OF THE PERSON
   Status (tick): □ Company  □ Firm  □ Individual  □ Trust  □ LLC  □ LLP  □ Other
   Suggested: {f41_status}
   Your Response: _______________________________________________

2. NATIONALITY / COUNTRY OF INCORPORATION
   Country: _______________________________________________
   (Suggested: {f41_country})

3. TAX IDENTIFICATION NUMBER IN COUNTRY OF RESIDENCE
   TIN / EIN / UTR / UEN (as applicable): _______________________________________________
   Name of Issuing Authority: _______________________________________________

4. PERIOD FOR WHICH RESIDENTIAL STATUS IS CLAIMED
   From Date: _______________ To Date: _______________
   Financial Year: {f41_fy}
   Confirm residence in {f41_country} for above period: □ Yes  □ No

5. ADDRESS IN COUNTRY OF RESIDENCE
   Registered/Official Address:
   _______________________________________________
   _______________________________________________
   _______________________________________________
   City/State/ZIP: _______________________________________________
   Country: {f41_country}

6. DTAA BENEFIT CLAIMED
   Treaty: India-{f41_country} DTAA
   Article being claimed: {f41_dtaa_article or '[TO BE FILLED]'}
   Nature of Income: {f41_nature}

7. BENEFICIAL OWNERSHIP DECLARATION
   I/We hereby declare that:
   (a) We are the beneficial owner of the income described above
   (b) We are NOT a conduit or pass-through entity
   (c) The income will not be passed on to a resident of a third country
       to obtain treaty benefits not otherwise available

   Confirmation: □ Yes, we confirm the above declarations

8. PERMANENT ESTABLISHMENT (PE) DECLARATION
   Do you have a PE in India? □ Yes  □ No
   If yes, income attributable to PE: _______________________________________________

9. TAX RESIDENCY CERTIFICATE (TRC)
   TRC Enclosed: □ Yes  □ No — Will provide by: _______________
   TRC issued by: _______________________________________________
   TRC Reference Number: _______________________________________________
   TRC Valid for period: _______________________________________________

{'='*70}
DECLARATION BY AUTHORISED SIGNATORY OF {f41_payee_name.upper()}
{'='*70}

I, _________________________, being duly authorised, hereby declare that:

(a) The information furnished above is true and correct;
(b) The entity is a tax resident of {f41_country} for the period stated;
(c) The Tax Identification Number stated above is correct;
(d) We are eligible to claim benefits under India-{f41_country} DTAA;
(e) We will immediately inform {f41_remitter} of any change in residential
    status or any other information affecting the above declaration.

Name of Authorised Person  : _______________________________________________
Designation                : _______________________________________________
Date                       : _______________________________________________
Place                      : _______________________________________________
Signature                  : _______________________________________________
Official Stamp             : [AFFIX COMPANY STAMP]

{'='*70}
IMPORTANT NOTES FOR {f41_payee_name.upper()}:
1. This form is MANDATORY under Section 159(8) of ITA 2025.
2. Without this form, {f41_remitter} CANNOT avail DTAA benefit and must
   deduct TDS at the higher domestic rate of 20-40%.
3. Enclose a copy of your Tax Residency Certificate (TRC) with this form.
4. Return the signed form along with TRC to {f41_remitter} / {f41_ca_name or 'the CA'}.
5. This information will be used for Form 146 CA Certificate preparation.

FOR QUERIES CONTACT:
{f41_ca_name or '[CA NAME]'}
Chartered Accountant
[Contact details]

{'='*70}
LEGAL REFERENCE:
Rule 75, Income Tax Rules, 2026 (Form 41 requirements)
Section 159(8), Income Tax Act, 2025 (mandatory for DTAA benefit)
Replaces erstwhile Form 10F under Rule 21AB of Income Tax Rules, 1962

DISCLAIMER: This template is for guidance only. The non-resident entity
is responsible for accuracy of declarations made in Form 41.
{'='*70}
"""
            st.markdown("#### Form 41 Template")
            st.text_area("Template Output", value=template41, height=500, label_visibility="collapsed")
            st.download_button(
                "📥 Download Form 41 Template",
                data=template41,
                file_name=f"Form41_Template_{f41_payee_name[:15]}_{f41_country}.txt",
                mime="text/plain"
            )
            st.success("✅ Send this to your non-resident payee for completion. Collect signed copy before remittance.")
            st.info("📌 Form 41 must be signed by authorised signatory of the foreign entity and returned along with TRC.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 9 — RESIDENTIAL STATUS CHECKER (Section 6, Income Tax Act, 2025)
# ════════════════════════════════════════════════════════════════════════════
with tab9:
    st.markdown("### 🌐 Residential Status Checker")
    st.caption("Determine residential status under **Section 6 of the Income Tax Act, 2025** "
               "(applicable to tax years beginning on or after 1 April 2026). "
               "Covers Resident & Ordinarily Resident (ROR), Resident but Not Ordinarily "
               "Resident (RNOR), Non-Resident (NR), and the deemed-resident rule for "
               "high-income citizens under Section 6(1A).")

    st.markdown("""
    <div class="ita-box">
    <b>Note:</b> The basic day-count tests under ITA 2025 are unchanged from Section 6(1) of the
    Income-tax Act, 1961. This calculator is a practitioner aid for a first-cut assessment only —
    always verify against the exact facts, travel records and the final Act/Rules text before
    advising a client or filing a return.
    </div>
    """, unsafe_allow_html=True)

    assessee_type = st.radio(
        "Type of Assessee",
        ["Individual", "Hindu Undivided Family (HUF)", "Firm / AOP / BOI", "Company"],
        horizontal=True,
        key="rs_assessee_type"
    )

    st.markdown("---")

    # ── INDIVIDUAL ──────────────────────────────────────────────────────
    if assessee_type == "Individual":
        col1, col2 = st.columns(2)
        with col1:
            rs_days_this_year = st.number_input(
                "Days stayed in India during the relevant tax year",
                min_value=0, max_value=366, value=0, key="rs_days_ty"
            )
            rs_days_prev4 = st.number_input(
                "Total days stayed in India during the 4 tax years immediately preceding",
                min_value=0, max_value=1464, value=0, key="rs_days_p4"
            )
            rs_category = st.selectbox(
                "Category of Individual",
                ["Ordinary case (not covered by the categories below)",
                 "Indian citizen leaving India for employment outside India, or as a crew "
                 "member of an Indian ship",
                 "Indian citizen / Person of Indian Origin (PIO) coming on a visit to India"],
                key="rs_category"
            )
        with col2:
            rs_indian_income = st.number_input(
                "Total income from Indian sources, excluding foreign income (₹ Lakhs) — "
                "for this tax year",
                min_value=0.0, value=0.0, step=1.0, key="rs_income",
                help="Relevant only for the 'visit to India' category and for the deemed-"
                     "resident test under Section 6(1A)."
            )
            rs_is_citizen = st.checkbox(
                "Individual is an Indian citizen",
                value=False, key="rs_is_citizen"
            )
            rs_liable_tax_elsewhere = st.radio(
                "Liable to tax in any other country/territory by reason of domicile, "
                "residence or a similar criterion?",
                ["Yes", "No"], horizontal=True, key="rs_liable_elsewhere",
                help="Used only for the Section 6(1A) deemed-resident test, which applies "
                     "when the normal day-count tests do NOT make the individual a resident."
            )

        st.markdown("##### For the Ordinarily Resident (ROR) test — only needed if Resident")
        col3, col4 = st.columns(2)
        with col3:
            rs_resident_years_10 = st.number_input(
                "Resident in India in how many of the preceding 10 tax years?",
                min_value=0, max_value=10, value=0, key="rs_res_10"
            )
        with col4:
            rs_days_prev7 = st.number_input(
                "Total days stayed in India during the preceding 7 tax years",
                min_value=0, max_value=2562, value=0, key="rs_days_p7"
            )

        if st.button("🧮 Determine Residential Status", type="primary", key="rs_calc_individual"):
            notes = []
            # Determine effective "60-day" threshold per category
            if rs_category.startswith("Indian citizen leaving India for employment"):
                threshold = 182
                notes.append("Category: citizen leaving for employment abroad / ship crew — "
                              "the 60-day limb is replaced with 182 days, so effectively only "
                              "the 182-day test applies.")
            elif rs_category.startswith("Indian citizen / Person of Indian Origin"):
                if rs_indian_income > 15:
                    threshold = 120
                    notes.append("Category: citizen/PIO on a visit to India with Indian-source "
                                  "income above ₹15 lakh — the 60-day limb is replaced with 120 days.")
                else:
                    threshold = 182
                    notes.append("Category: citizen/PIO on a visit to India with Indian-source "
                                  "income up to ₹15 lakh — the 60-day limb is replaced with 182 "
                                  "days, so effectively only the 182-day test applies.")
            else:
                threshold = 60

            cond_a = rs_days_this_year >= 182
            cond_b = (rs_days_this_year >= threshold) and (rs_days_prev4 >= 365)
            is_resident = cond_a or cond_b

            deemed_resident = False
            if not is_resident:
                if (rs_is_citizen and rs_indian_income > 15
                        and rs_liable_tax_elsewhere == "No"):
                    deemed_resident = True
                    is_resident = True
                    notes.append("Deemed Resident under Section 6(1A): Indian citizen, "
                                  "Indian-source income above ₹15 lakh, and not liable to tax "
                                  "in any other country by reason of domicile/residence.")

            if not is_resident:
                st.markdown("""
                <div class="warning-box">
                <b>Result: NON-RESIDENT (NR)</b><br>
                Neither the 182-day test nor the 60/120/182-day + 365-day test (nor the Section
                6(1A) deemed-resident rule) is satisfied. Only income received/accruing in
                India is taxable in India.
                </div>
                """, unsafe_allow_html=True)
            else:
                # RNOR direct-trigger: visiting citizen/PIO, income > 15L, resident only via
                # the 120-day route (i.e. stayed 120–181 days, not the full 182)
                direct_rnor = (
                    rs_category.startswith("Indian citizen / Person of Indian Origin")
                    and rs_indian_income > 15
                    and not cond_a and cond_b
                )
                ror_conditions_met = (rs_resident_years_10 >= 2) and (rs_days_prev7 >= 730)

                if deemed_resident:
                    final_status = "RNOR"
                    notes.append("A deemed resident under Section 6(1A) is always classified "
                                  "as Resident but Not Ordinarily Resident (RNOR).")
                elif direct_rnor:
                    final_status = "RNOR"
                    notes.append("Resident only via the 120-day route for a high-income "
                                  "citizen/PIO visiting India — classified directly as RNOR.")
                elif ror_conditions_met:
                    final_status = "ROR"
                else:
                    final_status = "RNOR"

                if final_status == "ROR":
                    st.markdown("""
                    <div class="success-box">
                    <b>Result: RESIDENT AND ORDINARILY RESIDENT (ROR)</b><br>
                    Global (worldwide) income is taxable in India.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="ita-box">
                    <b>Result: RESIDENT BUT NOT ORDINARILY RESIDENT (RNOR)</b><br>
                    Indian-source income is taxable. Foreign income is taxable only if it is
                    derived from a business controlled from, or a profession set up in, India.
                    </div>
                    """, unsafe_allow_html=True)

            with st.expander("Show reasoning / basis"):
                st.write(f"182-day test satisfied: **{cond_a}**")
                st.write(f"{threshold}-day + 365-day (preceding 4 years) test satisfied: **{cond_b}**")
                for n in notes:
                    st.caption(f"• {n}")
                st.caption("Legal basis: Section 6, Income Tax Act, 2025 (basic conditions, "
                           "citizen/PIO relaxations, Section 6(1A) deemed-resident rule, and "
                           "the ROR test of 2-out-of-10 preceding years + 730 days in the "
                           "preceding 7 years).")

    # ── HUF ──────────────────────────────────────────────────────────────
    elif assessee_type == "Hindu Undivided Family (HUF)":
        rs_huf_control = st.radio(
            "Is the control and management of the HUF's affairs situated "
            "**wholly outside India** during the relevant tax year?",
            ["Yes — wholly outside India", "No — wholly or partly in India"],
            key="rs_huf_control"
        )
        st.markdown("##### Karta's residential history (needed only if the HUF is Resident)")
        col1, col2 = st.columns(2)
        with col1:
            rs_karta_years_10 = st.number_input(
                "Karta resident in India in how many of the preceding 10 tax years?",
                min_value=0, max_value=10, value=0, key="rs_karta_10"
            )
        with col2:
            rs_karta_days_7 = st.number_input(
                "Karta's total days in India during the preceding 7 tax years",
                min_value=0, max_value=2562, value=0, key="rs_karta_7"
            )

        if st.button("🧮 Determine Residential Status", type="primary", key="rs_calc_huf"):
            if rs_huf_control.startswith("Yes"):
                st.markdown("""
                <div class="warning-box"><b>Result: NON-RESIDENT (NR)</b><br>
                Control and management is wholly outside India during the year.
                </div>""", unsafe_allow_html=True)
            else:
                ror = (rs_karta_years_10 >= 2) and (rs_karta_days_7 >= 730)
                if ror:
                    st.markdown("""
                    <div class="success-box"><b>Result: RESIDENT AND ORDINARILY RESIDENT (ROR)</b><br>
                    Global income is taxable in India.</div>""", unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="ita-box"><b>Result: RESIDENT BUT NOT ORDINARILY RESIDENT (RNOR)</b><br>
                    Based on the Karta not satisfying the ROR conditions (resident in at least
                    2 of the preceding 10 years, and 730+ days in India in the preceding 7 years).
                    </div>""", unsafe_allow_html=True)

    # ── FIRM / AOP / BOI ─────────────────────────────────────────────────
    elif assessee_type == "Firm / AOP / BOI":
        rs_firm_control = st.radio(
            "Is the control and management of the affairs of the firm / AOP / BOI "
            "situated **wholly outside India** during the relevant tax year?",
            ["Yes — wholly outside India", "No — wholly or partly in India"],
            key="rs_firm_control"
        )
        if st.button("🧮 Determine Residential Status", type="primary", key="rs_calc_firm"):
            if rs_firm_control.startswith("Yes"):
                st.markdown("""
                <div class="warning-box"><b>Result: NON-RESIDENT (NR)</b></div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="success-box"><b>Result: RESIDENT</b><br>
                Firms, AOPs and BOIs can only be Resident or Non-Resident — there is no
                RNOR category for these entities.</div>
                """, unsafe_allow_html=True)

    # ── COMPANY ──────────────────────────────────────────────────────────
    else:
        rs_incorporated_india = st.radio(
            "Is the company incorporated in India?",
            ["Yes", "No"], horizontal=True, key="rs_co_incorp"
        )
        rs_poem_india = st.radio(
            "Is the Place of Effective Management (POEM) of the company in India "
            "during the relevant tax year?",
            ["Yes", "No"], horizontal=True, key="rs_co_poem"
        )
        if st.button("🧮 Determine Residential Status", type="primary", key="rs_calc_company"):
            if rs_incorporated_india == "Yes" or rs_poem_india == "Yes":
                st.markdown("""
                <div class="success-box"><b>Result: RESIDENT</b><br>
                A company is resident in India if it is incorporated in India, or if its
                POEM is in India during the year.</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="warning-box"><b>Result: NON-RESIDENT (NR)</b></div>
                """, unsafe_allow_html=True)


# ── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#6B7570; font-size:0.8rem; font-family:'Share Tech Mono', monospace;">
🤖 NR TAX ADVISOR &nbsp;|&nbsp;
AICA Level 2 Capstone 2026 &nbsp;|&nbsp;
Built under Income Tax Act, 2025 | Income Tax Rules, 2026 &nbsp;|&nbsp;
Form 145 | Form 146 | Form 41 | Section 393<br>
<i>This tool is for professional guidance only. Verify with actual treaty text before filing.</i>
</div>
""", unsafe_allow_html=True)
