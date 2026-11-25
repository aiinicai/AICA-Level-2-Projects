"""Shared UI layer: API client, theme CSS and presentation components."""
from __future__ import annotations

import html
import json
import os

import requests
import streamlit as st

API = os.getenv("NOTICEMATE_API_URL", "http://127.0.0.1:8000/api")
DRAFT_BANNER = "Draft assistance only — not a final professional opinion. Every output requires CA review and approval."

CSS = """
<style>
/* NOTICE-MATE V3 theme — champagne grounds, charcoal structure, restrained gold accents */
:root{
 --nm-champagne:#F5EEE1; --nm-ivory:#FFFCF6; --nm-card:#FFFDF9;
 --nm-ink:#1C1915; --nm-charcoal:#2A2520; --nm-muted:#5C5348; --nm-line:#E2D6C1; --nm-line-strong:#CDBB9B;
 --nm-gold:#B4914F; --nm-gold-deep:#7A5B24;
 --nm-green:#2F6B45; --nm-amber:#8A5A12; --nm-red:#9A2B22;
 --nm-navy:var(--nm-charcoal); --nm-blue:var(--nm-charcoal); --nm-teal:var(--nm-gold-deep); --nm-bg:var(--nm-champagne);
}
html, body, [class*="css"], .stApp {font-family:"Segoe UI","Inter",system-ui,-apple-system,sans-serif;color:var(--nm-ink);}
.stApp{background:linear-gradient(180deg,#F7F1E6 0%,#F3EBDC 100%);}
.block-container{padding-top:1.3rem;padding-bottom:3rem;max-width:1400px;}
h1,h2,h3,.nm-sec,.nm-hero h1,.nm-start h2,.nm-brand,.nm-kpi .v{font-family:Georgia,"Cambria","Times New Roman",serif;letter-spacing:.2px}

section[data-testid="stSidebar"]{background:linear-gradient(180deg,#171411 0%,#211C17 70%,#2A231C 100%);border-right:1px solid #3A3127;}
section[data-testid="stSidebar"] *{color:#EFE6D4 !important;}
section[data-testid="stSidebar"] .stRadio label{padding:8px 12px;border-radius:8px;margin-bottom:2px;border:1px solid transparent}
section[data-testid="stSidebar"] .stRadio label:hover{background:rgba(180,145,79,.12);border-color:rgba(180,145,79,.35)}
section[data-testid="stSidebar"] hr{border-color:#3A3127}
section[data-testid="stSidebar"] .stButton>button{background:transparent;border:1px solid #5A4C3B}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] div{background-color:#2E2720 !important;border-color:#5A4C3B !important}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] label,section[data-testid="stSidebar"] [data-testid="stSelectbox"] label div{background-color:transparent !important}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] svg{fill:#D9CCB4 !important}
.nm-brand{font-weight:700;font-size:1.45rem;color:#F7EFDF;margin-bottom:0}
.nm-brand span{color:var(--nm-gold) !important}
.nm-tag{font-size:.78rem;opacity:.75;margin-top:2px}

.nm-hero{background:linear-gradient(120deg,#1C1915 0%,#2A2520 70%,#3A3127 100%);color:#F7EFDF;border-radius:14px;padding:22px 26px;
 margin-bottom:16px;border-bottom:3px solid var(--nm-gold);box-shadow:0 8px 22px rgba(28,25,21,.16)}
.nm-hero h1{font-size:1.6rem;margin:0 0 4px 0;color:#F7EFDF;font-weight:600}
.nm-hero p{margin:0;color:#D9CCB4;font-size:.93rem}

.nm-kpi{background:var(--nm-card);border:1px solid var(--nm-line);border-radius:12px;padding:15px 17px;box-shadow:0 1px 3px rgba(60,45,20,.06);height:100%}
.nm-kpi .v{font-size:1.85rem;font-weight:700;color:var(--nm-ink);line-height:1.15}
.nm-kpi .l{font-size:.74rem;text-transform:uppercase;letter-spacing:.8px;color:var(--nm-muted);font-weight:700}
.nm-kpi .s{font-size:.8rem;color:var(--nm-muted);margin-top:4px}
.nm-kpi.red{border-top:3px solid var(--nm-red)} .nm-kpi.amber{border-top:3px solid #C08A2E}
.nm-kpi.green{border-top:3px solid var(--nm-green)} .nm-kpi.blue{border-top:3px solid var(--nm-charcoal)} .nm-kpi.teal{border-top:3px solid var(--nm-gold)}
.nm-card{background:var(--nm-card);border:1px solid var(--nm-line);border-radius:12px;padding:15px 17px;margin-bottom:12px;box-shadow:0 1px 3px rgba(60,45,20,.05)}
.nm-card h4{margin:0 0 8px 0;font-size:1rem;color:var(--nm-ink)}
.nm-sec{font-size:1.12rem;font-weight:600;color:var(--nm-ink);margin:16px 0 8px 0;padding-bottom:6px;border-bottom:1px solid var(--nm-line-strong);position:relative}
.nm-sec:after{content:"";position:absolute;left:0;bottom:-1px;width:44px;height:2px;background:var(--nm-gold)}

.nm-badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.72rem;font-weight:700;letter-spacing:.3px;margin-right:4px;white-space:nowrap;border:1px solid transparent}
.b-green{background:#E4EFE3;color:#22553A;border-color:#C7DCC5}.b-amber{background:#F7EAD0;color:#7A4E0F;border-color:#E8D2A6}
.b-red{background:#F6E0DB;color:#86251D;border-color:#E9C2BA}.b-blue{background:#ECE6DA;color:#2A2520;border-color:#D8CDB8}
.b-grey{background:#EEEAE3;color:#4A443C;border-color:#DCD5C9}.b-teal{background:#F1E4C7;color:#6E5223;border-color:#E0CB9E}

.nm-alert{border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:.9rem;border:1px solid;border-left-width:4px}
.a-critical{background:#F8E6E1;border-color:#E6BDB3;border-left-color:var(--nm-red);color:#6E1F18}
.a-high{background:#FAF0DC;border-color:#EAD5A9;border-left-color:#C08A2E;color:#5E3F0C}
.a-medium{background:#FBF6EC;border-color:#E8DCC3;border-left-color:var(--nm-gold);color:#3E3527}
.a-info{background:#F7F3EC;border-color:#E3DACB;border-left-color:#8C8272;color:#3B352D}
.nm-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px dashed var(--nm-line);font-size:.9rem}
.nm-row:last-child{border-bottom:none}
.nm-muted{color:var(--nm-muted);font-size:.83rem}
.nm-steps{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 14px 0}
.nm-step{flex:1;min-width:110px;background:var(--nm-card);border:1px solid var(--nm-line);border-radius:10px;padding:8px 10px;font-size:.78rem}
.nm-step.done{border-color:#BFD5BD;background:#F1F6EF}
.nm-step b{display:block;font-size:.8rem;color:var(--nm-ink)}
.nm-banner{background:#FBF3E1;border:1px solid #E7D3A8;color:#5E440F;border-radius:10px;padding:8px 12px;font-size:.85rem;margin-bottom:10px}

div[data-testid="stTabs"] button[role="tab"]{font-weight:600;color:var(--nm-muted)}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{color:var(--nm-ink)}
div[data-baseweb="tab-highlight"]{background-color:var(--nm-gold) !important}
div[data-testid="stExpander"]{border-radius:12px;border:1px solid var(--nm-line);background:var(--nm-card)}
div[data-testid="stForm"]{border:1px solid var(--nm-line);background:var(--nm-ivory);border-radius:12px}
.stButton>button,.stDownloadButton>button,div[data-testid="stFormSubmitButton"]>button,div[data-testid="stPopover"] button{
 border-radius:8px;font-weight:600;background:var(--nm-ivory);color:var(--nm-ink);border:1px solid var(--nm-line-strong)}
.stButton>button:hover,.stDownloadButton>button:hover,div[data-testid="stFormSubmitButton"]>button:hover,div[data-testid="stPopover"] button:hover{
 border-color:var(--nm-gold);color:var(--nm-ink);background:#FFF8EA}
.stButton>button[kind="primary"],div[data-testid="stFormSubmitButton"]>button[kind="primaryFormSubmit"]{
 background:var(--nm-charcoal);color:#F7EFDF;border:1px solid var(--nm-charcoal);box-shadow:inset 0 -2px 0 var(--nm-gold)}
.stButton>button[kind="primary"]:hover,div[data-testid="stFormSubmitButton"]>button[kind="primaryFormSubmit"]:hover{
 background:#000;color:#FFF6E3;border-color:#000}
.stButton>button[kind="primary"] p,div[data-testid="stFormSubmitButton"]>button[kind="primaryFormSubmit"] p{color:#F7EFDF}
div[data-testid="stFileUploaderDropzone"]{background:var(--nm-ivory);border:1px dashed var(--nm-gold)}
a{color:var(--nm-gold-deep)}

/* ---------- V3 guided workflow ---------- */
.nm-start{background:var(--nm-card);border:1px solid var(--nm-line-strong);border-left:4px solid var(--nm-gold);border-radius:14px;
 padding:24px 28px;margin:6px 0 14px 0;box-shadow:0 2px 10px rgba(60,45,20,.06)}
.nm-start h2{margin:0 0 6px 0;color:var(--nm-ink);font-size:1.45rem;font-weight:600}
.nm-start p{margin:0;color:var(--nm-muted)}
.nm-stepper{display:flex;gap:0;margin:6px 0 8px 0}
.nm-stepper .s{flex:1;text-align:center;font-size:0;color:transparent;position:relative;padding-top:28px;height:28px}
.nm-stepper .s:before{content:attr(data-n);position:absolute;top:0;left:50%;transform:translateX(-50%);width:27px;height:27px;border-radius:50%;
 background:var(--nm-ivory);border:1px solid var(--nm-line-strong);color:var(--nm-muted);font-weight:700;line-height:25px;font-size:.8rem;z-index:1}
.nm-stepper .s:after{content:"";position:absolute;top:13px;left:-50%;width:100%;height:1px;background:var(--nm-line-strong);z-index:0}
.nm-stepper .s:first-child:after{display:none}
.nm-stepper .s.done:before{background:var(--nm-charcoal);border-color:var(--nm-charcoal);color:var(--nm-gold);content:"✓"}
.nm-stepper .s.cur:before{background:var(--nm-gold);border-color:var(--nm-gold-deep);color:#1C1915;box-shadow:0 0 0 4px rgba(180,145,79,.22)}
.nm-stepper .s.cur{color:var(--nm-ink);font-weight:700}
.nm-panel{background:var(--nm-ivory);border:1px solid var(--nm-line-strong);border-top:3px solid var(--nm-gold);border-radius:12px;padding:12px 14px}
.nm-panel h3{font-size:1.05rem;margin:0 0 6px 0;color:var(--nm-ink)}
.nm-tr{font-size:.72rem;text-transform:uppercase;letter-spacing:.9px;color:var(--nm-gold-deep);font-weight:800;margin:14px 0 4px 0}
.nm-quote{border-left:3px solid var(--nm-gold);padding:5px 10px;margin:4px 0;color:#2B2620;font-size:.87rem;background:#FFFFFF;border-radius:0 6px 6px 0;font-style:italic}
.nm-src{background:#FFFFFF;border:1px solid var(--nm-line);border-radius:10px;padding:9px 11px;margin:6px 0;font-size:.85rem}
.nm-src.primary{border-left:4px solid var(--nm-charcoal)}.nm-src.secondary{border-left:4px solid #9A9083}.nm-src.ai{border-left:4px solid #C08A2E;background:#FFF9EC}
.nm-src .t{font-weight:700;color:var(--nm-ink)}
.nm-src .m{color:var(--nm-muted);font-size:.79rem;margin-top:2px}
.nm-src a{color:var(--nm-gold-deep);font-weight:700;text-decoration:none;border-bottom:1px solid rgba(122,91,36,.35)}
</style>
"""

STATUS_BADGE = {
    "SUFFICIENT": "green", "PARTIALLY_SUFFICIENT": "amber", "INSUFFICIENT": "red", "NOT_PROVIDED": "red", "CONTRADICTORY": "red",
    "REQUIRES_VERIFICATION": "amber", "OPEN": "blue", "AWAITING_CLIENT": "amber", "UNDER_REVIEW": "teal", "APPROVED": "green",
    "SUBMITTED": "green", "CLOSED": "grey", "RECONCILED": "green", "RECONCILED_WITH_DIFFERENCES": "amber", "UNRECONCILED": "red",
    "MATCHED": "green", "DIFFERENCE": "amber", "NOT_IN_BOOKS": "red", "CONSISTENT": "green", "REVIEW": "amber", "HIGH": "red",
    "MEDIUM": "amber", "LOW": "green", "VERIFIED": "green", "UNVERIFIED": "amber", "DISCARDED": "grey", "PARTLY_VERIFIED": "amber",
    "ACCEPTED": "green", "REJECTED": "red", "DRAFT": "blue", "SENT": "green", "BLOCKED": "red", "FAILED": "red",
    "PENDING_APPROVAL": "amber", "CANCELLED": "grey", "SUPPORTED_BY_DOCUMENTS": "green", "PARTLY_SUPPORTED": "amber",
    "NOT_SUPPORTED": "red", "AVAILABLE": "green", "ESTABLISHED_FACT": "green", "DOCUMENT_AVAILABLE": "blue",
    "MANAGEMENT_EXPLANATION": "amber", "ASSUMPTION": "grey", "UNRESOLVED": "red", "SYSTEM_DERIVED": "teal",
    "ESTABLISHED_BY_DOCUMENT": "green", "PARTLY_SUPPORTED_DOC": "amber", "AWAITING_CLIENT_CONFIRMATION": "red",
    "CLIENT_CONFIRMED": "green", "DOCUMENT_NOT_MARKED_AS_ANNEXURE": "amber", "CHANGES_REQUESTED": "amber", "OK": "green",
    "OCR": "teal", "PARTIAL": "amber",
    "NEEDS_CA_REVIEW": "amber", "OUTDATED": "red", "SUPPORTS": "green", "DIFFERS": "red", "DISTINGUISHABLE": "amber",
    "CONTEXT": "grey", "PRIMARY": "blue", "SECONDARY": "grey", "AI_SUGGESTION": "amber", "READY": "green", "DEGRADED": "amber",
    "UNAVAILABLE": "red", "LOW_CONFIDENCE": "amber", "BLANK": "red", "ESTABLISHED": "green", "CLIENT_EXPLANATION": "amber",
}


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def badge(text, kind: str | None = None) -> str:
    k = kind or STATUS_BADGE.get(str(text), "grey")
    return f'<span class="nm-badge b-{k}">{esc(str(text).replace("_", " "))}</span>'


def inr(x) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "—"
    neg = v < 0
    v = abs(round(v))
    s = str(int(v))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("−₹" if neg else "₹") + s


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str = ""):
    st.markdown(f'<div class="nm-hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)


def kpi(col, label: str, value, sub: str = "", tone: str = "blue"):
    col.markdown(f'<div class="nm-kpi {tone}"><div class="l">{esc(label)}</div><div class="v">{esc(value)}</div>'
                 f'<div class="s">{esc(sub)}</div></div>', unsafe_allow_html=True)


def section(title: str):
    st.markdown(f'<div class="nm-sec">{esc(title)}</div>', unsafe_allow_html=True)


def alert(text: str, level: str = "info"):
    st.markdown(f'<div class="nm-alert a-{esc(level)}">{esc(text)}</div>', unsafe_allow_html=True)


def banner(text: str = DRAFT_BANNER):
    st.markdown(f'<div class="nm-banner">⚠️ {esc(text)}</div>', unsafe_allow_html=True)


def empty(text: str, hint: str = ""):
    st.markdown(f'<div class="nm-card" style="text-align:center;padding:28px"><div style="font-size:1.6rem">🗂️</div>'
                f'<div style="font-weight:600;margin-top:6px">{esc(text)}</div><div class="nm-muted">{esc(hint)}</div></div>',
                unsafe_allow_html=True)


def steps(items: list[tuple[str, bool, str]]):
    """Progress tracker: [(label, done, detail)]."""
    cells = "".join(f'<div class="nm-step {"done" if d else "todo"}"><b>{"✅" if d else "○"} {esc(l)}</b>{esc(x)}</div>'
                    for l, d, x in items)
    st.markdown(f'<div class="nm-steps">{cells}</div>', unsafe_allow_html=True)


def call(method: str, path: str, *, json_body=None, files=None, params=None, raw=False, quiet=False, timeout: int = 240):
    headers = {}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        r = requests.request(method, API + path, json=json_body, files=files, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        if not quiet:
            st.error(f"Backend not reachable at {API} ({type(e).__name__}). Start it with run_api.bat / run_api.sh.")
        return None
    if r.status_code == 401 and path != "/auth/login":
        st.session_state.pop("token", None)
        st.warning("Your session has expired — please sign in again.")
        return None
    if r.status_code >= 400:
        if quiet:
            return None
        try:
            err = r.json()
            st.error(err.get("message") or f"Error {r.status_code}")
            det = err.get("details") or {}
            if det:
                with st.expander("Details"):
                    st.json(det)
        except ValueError:
            st.error(f"Error {r.status_code}")
        return None
    if raw:
        return r
    return r.json() if "application/json" in r.headers.get("content-type", "") else r.text


def toast(msg: str, icon: str = "✅"):
    try:
        st.toast(msg, icon=icon)
    except Exception:
        st.success(msg)


def basis_line(item: dict) -> str:
    if not isinstance(item, dict):
        return esc(item)
    return f'{badge(item.get("basis", "UNRESOLVED"))} {esc(item.get("text", ""))}'


def json_download(label: str, obj, fname: str):
    st.download_button(label, json.dumps(obj, indent=2, ensure_ascii=False, default=str), file_name=fname, mime="application/json")


def stepper(items: list[dict], current: str):
    """items: [{"key","label","done"}]. Visual only — navigation buttons are rendered separately."""
    cells = "".join(f'<div class="s {"done" if it["done"] else ""} {"cur" if it["key"] == current else ""}" data-n="{n}">{esc(it["label"])}</div>'
                    for n, it in enumerate(items, 1))
    st.markdown(f'<div class="nm-stepper">{cells}</div>', unsafe_allow_html=True)


def safe_link(url: str | None, label: str = "Open source ↗") -> str:
    """Only http(s) links are rendered as links; anything else is shown as text."""
    if url and str(url).lower().startswith(("https://", "http://")):
        return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'
    return '<span class="nm-muted">no link recorded</span>'
