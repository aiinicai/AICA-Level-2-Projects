# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""The CSS for each layout + theme, and the small layout previews shown on the Settings page.

No Streamlit import: ``build_css`` and ``layout_preview_html`` just return strings, so they can be tested.
Streamlit's own widgets are restyled through its ``data-testid`` hooks; where a widget cannot be restyled
(the data tables are drawn on a canvas) the dark themes invert them so they match.
"""
import html
from string import Template

from core.themes import LAYOUTS, palette

_FOOTER = Template(
    """
/* ownership line on every page */
[data-testid="stMain"] .block-container { padding-bottom: 3.6rem; }
.lq-footer { position: fixed; left: 0; right: 0; bottom: 0; z-index: 50; text-align: center; padding: 6px 12px; font-size: 0.76rem; color: ${muted} !important; background: ${bg}; border-top: 1px solid ${border}; }
"""
)

_BASE = Template(
    """
.stApp { background: ${bg_css}; color: ${text}; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stMain"] .block-container { padding-top: 2.2rem; max-width: 1600px; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp label, .stApp li,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p, [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: ${text} !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, .stApp small { color: ${muted} !important; }
.stApp a { color: ${accent}; }
.stApp hr { border-color: ${border} !important; }

/* cards: bordered containers, expanders, popovers */
[data-testid="stVerticalBlockBorderWrapper"] { background: ${surface_css}; border: 1px solid ${border} !important; border-radius: ${radius}; box-shadow: ${shadow}; }
[data-testid="stExpander"] { background: ${surface_css}; border: 1px solid ${border} !important; border-radius: ${radius}; }
[data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span { color: ${text} !important; }
[data-testid="stPopoverBody"] { background: ${surface}; border: 1px solid ${border}; }

/* buttons */
/* every kind of button: normal, download, popover trigger (user menu, Appearance), the file uploader's Browse, form submit */
.stButton > button, .stDownloadButton > button, [data-testid^="stBaseButton-secondary"], [data-testid="stPopoverButton"], [data-testid="stFileUploaderDropzone"] button { background: ${surface_css}; color: ${text}; border: 1px solid ${border}; border-radius: 10px; }
.stButton > button p, .stDownloadButton > button p, [data-testid^="stBaseButton"] p, [data-testid="stPopoverButton"] p, [data-testid="stPopoverButton"] span { color: inherit !important; }
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid^="stBaseButton-secondary"]:hover, [data-testid="stPopoverButton"]:hover { border-color: ${accent}; color: ${accent}; }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] { background: ${accent}; color: ${accent_text}; border-color: ${accent}; }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); color: ${accent_text}; }
.stButton > button:disabled { opacity: 0.45; }

/* inputs and dropdowns */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div { background: ${surface} !important; border-color: ${border} !important; }
.stApp input, .stApp textarea, [data-baseweb="select"] div { color: ${text} !important; }
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul { background: ${surface_alt} !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li div { color: ${text} !important; }
[data-baseweb="tag"] { background: ${accent} !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] svg { color: ${accent_text} !important; }
[data-testid="stFileUploaderDropzone"] { background: ${surface_alt}; border-color: ${border}; }
[data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small, [data-testid="stFileUploaderDropzone"] div { color: ${muted} !important; }
[data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploaderDropzone"] button * { color: ${text} !important; }
[data-testid="stFileUploaderFile"] *, [data-testid="stFileUploaderFileName"] { color: ${text} !important; }
button[data-baseweb="tab"] p { color: ${muted} !important; }
button[data-baseweb="tab"][aria-selected="true"] p { color: ${accent} !important; }

/* KPI cards, stat blocks, status pills, rings */
.kpi-card { background: ${surface_css}; border: 1px solid ${border}; border-top: 4px solid var(--kpi-accent, ${kpi_blue}); border-radius: ${radius}; padding: 14px 16px 10px 16px; box-shadow: ${shadow}; height: 100%; }
.kpi-top { display: flex; align-items: center; gap: 10px; }
.kpi-icon { display: inline-flex; width: 34px; height: 34px; border-radius: 10px; align-items: center; justify-content: center; background: color-mix(in srgb, var(--kpi-accent, ${kpi_blue}) 18%, transparent); color: var(--kpi-accent, ${kpi_blue}); flex: none; }
.kpi-icon svg { width: 18px; height: 18px; }
.kpi-label { font-size: 0.85rem; color: ${muted} !important; font-weight: 600; }
.kpi-value { font-size: 1.7rem; font-weight: 700; color: ${text} !important; line-height: 1.25; }
.kpi-compact { padding: 10px 10px 8px 10px; overflow: hidden; }
.kpi-compact .kpi-label { font-size: 0.72rem; white-space: nowrap; }
.kpi-compact .kpi-value { font-size: 0.98rem; white-space: nowrap; }
.kpi-compact .kpi-full { font-size: 0.66rem; white-space: nowrap; word-break: normal; }
.kpi-sub { font-size: 0.8rem; min-height: 1.2em; color: ${muted} !important; }
.kpi-full { font-size: 0.72rem; color: ${muted} !important; }
.kpi-sub.kpi-up { color: ${kpi_green} !important; } .kpi-sub.kpi-down { color: #E5534B !important; }
.kpi-pill { display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.kpi-pill-up { background: color-mix(in srgb, ${kpi_green} 18%, transparent); color: ${kpi_green} !important; }
.kpi-pill-down { background: rgba(229,83,75,0.16); color: #E5534B !important; }
.kpi-pill-flat, .kpi-pill-none { background: ${surface_alt}; color: ${muted} !important; }
.status-pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.ring-row { display: flex; gap: 16px; justify-content: space-around; align-items: center; margin: 4px 0 8px 0; }
.ring { text-align: center; } .ring svg { width: 92px; height: 92px; }
.ring-label { font-size: 0.75rem; color: ${muted} !important; }

/* sidebar */
section[data-testid="stSidebar"] { background: ${sidebar_bg}; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] { display: none; }
section[data-testid="stSidebar"] * { color: ${sidebar_text} !important; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] { border-radius: 8px; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover { background: ${sidebar_hover}; }
section[data-testid="stSidebar"] button { background: transparent; border: 1px solid rgba(255,255,255,0.35); }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }
section[data-testid="stSidebar"] .lq-pro { color: ${accent_text} !important; }  /* the badge keeps its own readable text */
.lq-brand { font-size: 1.5rem; font-weight: 700; letter-spacing: 0.2px; margin-top: 0.4rem; }
.lq-pro { background: ${accent}; color: ${accent_text} !important; border-radius: 6px; padding: 1px 8px; font-size: 0.8rem; margin-left: 4px; vertical-align: middle; }
.lq-tag { font-size: 0.78rem; opacity: 0.8; margin-bottom: 0.6rem; }
.lq-group { font-size: 0.72rem; letter-spacing: 1.2px; text-transform: uppercase; opacity: 0.75; margin: 0.9rem 0 0.2rem 0.4rem; }
"""
)

_DARK_EXTRAS = Template(
    """
/* dark: the data tables are drawn on a canvas, so they are inverted to match; alerts keep their light tints with dark text */
[data-testid="stDataFrame"] { filter: invert(0.93) hue-rotate(180deg); border-radius: 8px; }
[data-testid="stAlert"] p, [data-testid="stAlert"] div, [data-testid="stAlert"] li { color: #1A2233 !important; }
.stApp code, .stApp pre { background: ${surface_alt} !important; color: ${text} !important; }
"""
)

_TOP_NAV = Template(
    """
/* top navigation (no sidebar) */
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }
.st-key-topnav { background: ${surface_css}; border: 1px solid ${border}; border-radius: ${radius}; box-shadow: ${shadow}; padding: 4px 14px; margin-bottom: 14px; }
.st-key-topnav a[data-testid="stPageLink-NavLink"] { border-radius: 999px; }
.st-key-topnav a[data-testid="stPageLink-NavLink"] p { color: ${text} !important; font-weight: 600; }
.st-key-topnav a[data-testid="stPageLink-NavLink"]:hover { background: ${sidebar_hover}; }
.st-key-topnav a[aria-current="page"] { background: ${sidebar_hover}; }
.st-key-topnav a[aria-current="page"] p { color: ${accent} !important; }
.lq-brand-top { font-size: 1.25rem; font-weight: 700; color: ${text} !important; }
.lq-brand-top .lq-pro { background: ${accent}; color: ${accent_text} !important; border-radius: 6px; padding: 1px 8px; font-size: 0.75rem; margin-left: 4px; }
"""
)

_MODERN = Template(
    """
/* modern: gradient greeting banner, glass cards */
.st-key-hero { background: ${hero_css}; border-radius: ${radius}; padding: 20px 28px; margin-bottom: 14px; box-shadow: ${shadow}; }
.st-key-hero h1, .st-key-hero h2, .st-key-hero h3, .st-key-hero p, .st-key-hero span { color: ${hero_text} !important; }
.st-key-hero button { background: #FFFFFF !important; color: #1F2340 !important; border: none !important; border-radius: 999px !important; }
.st-key-hero button p { color: #1F2340 !important; }
[data-testid="stVerticalBlockBorderWrapper"], .kpi-card { backdrop-filter: blur(10px); }
.kpi-card { border-top: 1px solid ${border}; }
"""
)

_PRO = Template(
    """
/* pro: compact control room, glowing accents */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 10px; }
.kpi-card { border: 1px solid var(--kpi-accent, ${kpi_blue}); border-top: 1px solid var(--kpi-accent, ${kpi_blue}); }
"""
)

_PRO_GLOW = Template(
    """
.kpi-card { box-shadow: 0 0 16px color-mix(in srgb, var(--kpi-accent, ${kpi_blue}) 35%, transparent); }
[data-testid="stVerticalBlockBorderWrapper"] { box-shadow: 0 0 0 1px rgba(45,226,196,0.10); }
.ring svg circle.ring-value { filter: drop-shadow(0 0 4px currentColor); }
"""
)

def build_css(layout: str = "classic", theme: str = "light") -> str:
    """The full <style> block for a layout + theme (an unknown value falls back to the default)."""
    p = palette(layout, theme)
    parts = [_BASE.safe_substitute(p), _FOOTER.safe_substitute(p)]
    if p["is_dark"]:
        parts.append(_DARK_EXTRAS.safe_substitute(p))
    if p["nav"] == "top":
        parts.append(_TOP_NAV.safe_substitute(p))
    if p["layout"] == "modern":
        parts.append(_MODERN.safe_substitute(p))
    if p["layout"] == "pro":
        parts.append(_PRO.safe_substitute(p))
        if p["glow"]:
            parts.append(_PRO_GLOW.safe_substitute(p))
    return "<style>\n" + "\n".join(parts) + "\n</style>"


# --------------------------------------------------------------------------- #
# layout previews (Settings page)
# --------------------------------------------------------------------------- #
def layout_preview_html(layout: str, theme: str = "light", selected: bool = False) -> str:
    """A small schematic of a layout in a theme: navigation, KPI row, charts and the lower panels.
    Pure HTML/CSS (no images), so it always matches the theme colours."""
    p = palette(layout, theme)
    box = "background:{};border:1px solid {};border-radius:4px;".format(p["surface"], p["border"])
    kpi = "".join(
        '<div style="{}height:14px;border-top:3px solid {};"></div>'.format(box, p[k])
        for k in ("kpi_blue", "kpi_green", "kpi_purple", "kpi_orange")
    )
    charts = "".join('<div style="{}height:30px;"></div>'.format(box) for _ in range(3))
    lower = (
        '<div style="{b}height:26px;"></div><div style="{b}height:26px;"></div><div style="{b}height:26px;"></div>'
    ).format(b=box)
    if layout == "modern":
        chrome = '<div style="height:9px;background:{};border-radius:4px;margin-bottom:4px;"></div>'.format(p["surface"])
        hero = '<div style="height:16px;background:{};border-radius:6px;margin-bottom:4px;"></div>'.format(p["hero_css"])
        body = chrome + hero
        side = ""
    else:
        body = ""
        side = '<div style="width:16px;background:{};border-radius:4px;flex:none;"></div>'.format(p["sidebar_bg"])
    frame = "border:2px solid {};".format(p["accent"] if selected else p["border"])
    return (
        '<div style="display:flex;gap:4px;padding:6px;background:{bg};{frame}border-radius:8px;height:150px;overflow:hidden;">'
        "{side}"
        '<div style="flex:1;display:flex;flex-direction:column;gap:4px;">{body}'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px;">{kpi}</div>'
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;">{charts}</div>'
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;">{lower}</div>'
        "</div></div>"
        '<div style="text-align:center;font-weight:700;margin-top:4px;">{label}</div>'
    ).format(bg=p["bg"], frame=frame, side=side, body=body, kpi=kpi, charts=charts, lower=lower, label=html.escape(LAYOUTS[layout]["label"]))
