"""Visual building blocks: theme CSS, KPI cards, pills, avatars, headers. 'Classic navy' design."""
import html
from datetime import date, datetime

import streamlit as st

from . import clock

NAVY, NAVY2, TEAL = "#0B1F3A", "#132B4D", "#0D9488"
TONES = {  # background, text
    "slate": ("#F1F5F9", "#475569"), "blue": ("#DBEAFE", "#1D4ED8"), "amber": ("#FEF3C7", "#B45309"),
    "green": ("#DCFCE7", "#15803D"), "red": ("#FEE2E2", "#B91C1C"), "teal": ("#CCFBF1", "#0F766E"),
    "indigo": ("#E0E7FF", "#4338CA"), "violet": ("#EDE9FE", "#6D28D9"), "rose": ("#FFE4E6", "#BE123C"),
    "navy": ("#E2E8F0", NAVY),
}
AVATAR_COLORS = ["#0D9488", "#6366F1", "#F59E0B", "#E11D48", "#0EA5E9", "#8B5CF6", "#10B981", "#F97316"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, p, li, label, input, textarea, h1, h2, h3, h4, h5, h6, td, th,
.stMarkdown, [data-testid="stWidgetLabel"], [data-baseweb="select"] div, button p, a span:not([data-testid="stIconMaterial"]) {
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif; }
.block-container { padding-top: 1.6rem !important; padding-bottom: 3rem !important; max-width: 1400px; }
header[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { color: #0B1F3A; letter-spacing: -0.02em; }

/* ---------- sidebar ---------- */
[data-testid="stSidebarHeader"] { height: 0.5rem; padding: 0; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top: 0.8rem; }
[data-testid="stPageLink"] a { border-radius: 10px; padding: 5px 10px; margin: 1px 0; }
[data-testid="stPageLink"] a:hover { background: rgba(255,255,255,0.06); }
[data-testid="stPageLink"] a[aria-current="page"], [data-testid="stPageLink-NavLink"][aria-current="page"] {
  background: rgba(45,212,191,0.15); }
[data-testid="stPageLink"] a[aria-current="page"] p { color: #FFFFFF !important; font-weight: 600; }
[data-testid="stPageLink"] p { font-size: 0.92rem; }
.pm-sec { color:#64748B; font-size:0.66rem; letter-spacing:0.14em; text-transform:uppercase; font-weight:600;
  margin: 16px 0 4px 10px; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0B1F3A 0%, #0E2647 100%); }
section[data-testid="stSidebar"] * { color: #CBD5E1; }
[data-testid="stSidebarNav"] a { border-radius: 10px; margin: 2px 6px; padding: 6px 10px; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.06); }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(45,212,191,0.14); }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: #FFFFFF !important; font-weight: 600; }
[data-testid="stNavSectionHeader"] { color: #64748B !important; font-size: 0.68rem !important;
  letter-spacing: 0.12em; text-transform: uppercase; }
section[data-testid="stSidebar"] .stButton button { background: rgba(255,255,255,0.06); border: 1px solid #1E3A5F;
  color: #E2E8F0; width: 100%; }
section[data-testid="stSidebar"] .stButton button:hover { border-color: #2DD4BF; color: #FFFFFF; }

/* ---------- cards & widgets ---------- */
div[data-testid="stVerticalBlockBorderWrapper"], div[class*="st-key-card"] {
  background: #FFFFFF; border-radius: 14px !important; }
div[data-testid="stExpander"] details { background: #FFFFFF; border-radius: 12px; }
.stButton button, .stDownloadButton button, .stFormSubmitButton button { border-radius: 10px; font-weight: 600; }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
  background: #0D9488; border-color: #0D9488; box-shadow: 0 4px 12px rgba(13,148,136,0.25); }
div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] { font-weight: 600; padding: 8px 14px; }
div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 14px 16px; }

/* ---------- custom components ---------- */
.pm-head { display:flex; justify-content:space-between; align-items:flex-end; margin: 0 0 1.1rem 0; gap: 1rem; }
.pm-head h1 { font-size: 1.75rem; font-weight: 800; margin: 0; padding: 0; color: #0B1F3A; }
.pm-head p { color: #64748B; margin: 4px 0 0 0; font-size: 0.92rem; }
.pm-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 1.1rem; }
.pm-kpi { background:#FFFFFF; border:1px solid #E5E9F0; border-radius:16px; padding:16px 18px;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 6px 18px rgba(15,23,42,0.04); position:relative; overflow:hidden; }
.pm-kpi:before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background: var(--accent); }
.pm-kpi .lbl { font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; padding-right:26px; color:#64748B; font-weight:600; }
.pm-kpi .val { font-size:1.6rem; font-weight:800; color:#0B1F3A; margin-top:6px; line-height:1.1; }
.pm-kpi .sub { font-size:0.8rem; color:#64748B; margin-top:4px; }
.pm-kpi .ico { position:absolute; right:14px; top:12px; font-size:1.3rem; opacity:0.85; }
.pm-pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.74rem; font-weight:600;
  white-space:nowrap; line-height:1.6; }
.pm-avatar { display:inline-flex; align-items:center; justify-content:center; border-radius:50%; color:#fff;
  font-weight:700; flex-shrink:0; }
.pm-card { background:#FFFFFF; border:1px solid #E5E9F0; border-radius:16px; padding:16px 18px;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04); margin-bottom: 12px; }
.pm-card h4 { margin:0 0 10px 0; font-size:0.98rem; font-weight:700; }
.pm-row { display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px solid #F1F5F9; }
.pm-row:last-child { border-bottom:none; }
.pm-row .main { flex:1; min-width:0; }
.pm-row .t1 { font-weight:600; color:#0F172A; font-size:0.9rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.pm-row .t2 { color:#64748B; font-size:0.78rem; }
.pm-date { width:46px; text-align:center; border-radius:10px; background:#F1F5F9; padding:4px 0; flex-shrink:0; }
.pm-date .d { font-weight:800; font-size:1.05rem; color:#0B1F3A; line-height:1.1; }
.pm-date .m { font-size:0.65rem; text-transform:uppercase; color:#64748B; font-weight:600; }
.pm-bar { height:6px; background:#EEF2F6; border-radius:99px; overflow:hidden; margin-top:5px; }
.pm-bar > div { height:100%; border-radius:99px; }
.pm-live { display:inline-flex; align-items:center; gap:6px; font-size:0.75rem; color:#0F766E; background:#CCFBF1;
  padding:3px 10px; border-radius:99px; font-weight:600; }
.pm-live:before { content:""; width:7px; height:7px; border-radius:50%; background:#14B8A6;
  box-shadow:0 0 0 3px rgba(20,184,166,0.25); animation: pmpulse 1.6s infinite; }
@keyframes pmpulse { 0%{opacity:1} 50%{opacity:0.35} 100%{opacity:1} }
.pm-empty { text-align:center; color:#94A3B8; padding:22px 0; font-size:0.9rem; }
.pm-brand { display:flex; align-items:center; gap:10px; padding: 4px 4px 14px 4px; }
.pm-brand .mark { width:38px; height:38px; border-radius:11px; background: linear-gradient(135deg,#0D9488,#2DD4BF);
  display:flex; align-items:center; justify-content:center; color:#0B1F3A; font-weight:800; font-size:0.95rem; }
.pm-brand .nm { color:#FFFFFF; font-weight:700; font-size:1rem; line-height:1.1; }
.pm-brand .tg { color:#7C93B3; font-size:0.72rem; }
.pm-user { display:flex; align-items:center; gap:10px; padding:10px; border-radius:12px;
  background: rgba(255,255,255,0.05); border:1px solid #1E3A5F; margin-bottom:8px; }
.pm-user .n { color:#FFFFFF; font-weight:600; font-size:0.88rem; }
.pm-user .r { color:#7C93B3; font-size:0.74rem; }

/* Kanban */
.pm-col-head { display:flex; justify-content:space-between; align-items:center; padding:10px 12px; border-radius:12px;
  background:#FFFFFF; border:1px solid #E5E9F0; margin-bottom:10px; font-weight:700; color:#0B1F3A; }
div[class*="st-key-card-"] { border:1px solid #E5E9F0 !important; border-left:4px solid #CBD5E1 !important;
  padding: 10px 12px 4px 12px !important; box-shadow: 0 1px 3px rgba(15,23,42,0.05); }
div[class*="st-key-card-red-"] { border-left-color:#DC2626 !important; }
div[class*="st-key-card-amber-"] { border-left-color:#F59E0B !important; }
div[class*="st-key-card-green-"] { border-left-color:#16A34A !important; }
div[class*="st-key-card-"] .stButton button { padding: 0 8px; min-height: 30px; font-size: 0.8rem; }
.pm-k-client { font-weight:700; color:#0B1F3A; font-size:0.88rem; }
.pm-k-title { color:#334155; font-size:0.84rem; margin:2px 0 6px 0; }
.pm-k-meta { display:flex; flex-wrap:wrap; gap:5px; align-items:center; margin-bottom:6px; }

/* Calendar */
.pm-cal { width:100%; border-collapse:separate; border-spacing:6px; table-layout:fixed; }
.pm-cal th { background:transparent !important; border:none !important; font-size:0.72rem; color:#64748B; text-transform:uppercase; letter-spacing:0.08em; font-weight:600; }
.pm-cal td { background:#FFFFFF; border:1px solid #E5E9F0; border-radius:12px; height:96px; vertical-align:top;
  padding:6px 7px; }
.pm-cal td.off { background:transparent; border:none; }
.pm-cal td.today { border:2px solid #0D9488; }
.pm-cal .dn { font-weight:700; font-size:0.82rem; color:#0B1F3A; }
.pm-cal .ev { display:block; font-size:0.68rem; border-radius:6px; padding:1px 5px; margin-top:3px; overflow:hidden;
  white-space:nowrap; text-overflow:ellipsis; font-weight:600; }

/* Login */
.pm-login-art { background: radial-gradient(1200px 400px at -10% -10%, #1E3A5F 0%, #0B1F3A 55%);
  border-radius: 22px; padding: 42px 38px; color:#E2E8F0; min-height: 540px; position:relative; overflow:hidden; }
.pm-login-art h2 { color:#FFFFFF; font-size:2rem; font-weight:800; line-height:1.15; margin: 26px 0 10px 0; }
.pm-login-art p { color:#94A3B8; }
.pm-login-art li { margin: 10px 0; color:#CBD5E1; list-style:none; }
.pm-login-art li:before { content:"✓"; color:#2DD4BF; font-weight:800; margin-right:10px; }
.pm-login-art .glow { position:absolute; right:-80px; bottom:-80px; width:260px; height:260px; border-radius:50%;
  background: radial-gradient(circle, rgba(45,212,191,0.35), transparent 70%); }
#MainMenu, footer, [data-testid="stStatusWidget"] { visibility: hidden; }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def pill(text, tone="slate") -> str:
    bg, fg = TONES.get(tone, TONES["slate"])
    return f'<span class="pm-pill" style="background:{bg};color:{fg}">{esc(text)}</span>'


def initials(name: str) -> str:
    parts = [p for p in (name or "?").replace("CA ", "").split() if p[0].isalnum()]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def avatar(name: str, size=30) -> str:
    color = AVATAR_COLORS[sum(map(ord, name or "?")) % len(AVATAR_COLORS)]
    return (f'<span class="pm-avatar" title="{esc(name)}" style="width:{size}px;height:{size}px;'
            f'background:{color};font-size:{size * 0.38:.0f}px">{esc(initials(name))}</span>')


def header(title: str, subtitle: str = "", right: str = ""):
    st.markdown(f'<div class="pm-head"><div><h1>{esc(title)}</h1>'
                f'{f"<p>{esc(subtitle)}</p>" if subtitle else ""}</div><div>{right}</div></div>',
                unsafe_allow_html=True)


def kpi_html(label, value, sub="", accent=TEAL, icon="") -> str:
    return (f'<div class="pm-kpi" style="--accent:{accent}"><div class="ico">{icon}</div>'
            f'<div class="lbl">{esc(label)}</div><div class="val">{esc(value)}</div>'
            f'<div class="sub">{sub}</div></div>')


def kpis(cards: list[str]):
    st.markdown(f'<div class="pm-kpis">{"".join(cards)}</div>', unsafe_allow_html=True)


def card(title: str, body_html: str, right: str = ""):
    st.markdown(f'<div class="pm-card"><div style="display:flex;justify-content:space-between;align-items:center">'
                f'<h4>{esc(title)}</h4>{right}</div>{body_html}</div>', unsafe_allow_html=True)


def empty(msg: str) -> str:
    return f'<div class="pm-empty">{esc(msg)}</div>'


def live(ts: datetime | None = None) -> str:
    return f'<span class="pm-live">Live · {(ts or clock.now()).strftime("%H:%M:%S")}</span>'


def bar(pct: float, color=TEAL) -> str:
    pct = max(0, min(100, pct))
    return f'<div class="pm-bar"><div style="width:{pct:.0f}%;background:{color}"></div></div>'


def date_chip(d: date) -> str:
    return f'<div class="pm-date"><div class="d">{d.day}</div><div class="m">{d.strftime("%b")}</div></div>'


def inr(x, short=False) -> str:
    x = float(x or 0)
    if short:
        if abs(x) >= 1e7:
            return f"₹{x / 1e7:.2f} Cr"
        if abs(x) >= 1e5:
            return f"₹{x / 1e5:.2f} L"
    s = f"{abs(int(round(x)))}"
    if len(s) > 3:  # Indian digit grouping 12,34,567
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-" if x < 0 else "") + "₹" + s


def due_tone(due: date, status: str, today: date) -> tuple[str, str]:
    """Returns (tone, label) for a due date."""
    if status == "Done":
        return "green", "Done"
    days = (due - today).days
    if days < 0:
        return "red", f"{-days}d overdue"
    if days == 0:
        return "amber", "Due today"
    if days <= 7:
        return "amber", f"Due in {days}d"
    return "slate", due.strftime("%d %b")


def ago(ts: str) -> str:
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ""
    s = (clock.now() - dt).total_seconds()
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)} min ago"
    if s < 86400:
        return f"{int(s // 3600)} h ago"
    return f"{int(s // 86400)} d ago"


def style_fig(fig, height=300):
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, Segoe UI, sans-serif", color="#334155"),
                      legend=dict(orientation="h", y=-0.18, title=None), bargap=0.35)
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(gridcolor="#EEF2F6", title=None)
    return fig
