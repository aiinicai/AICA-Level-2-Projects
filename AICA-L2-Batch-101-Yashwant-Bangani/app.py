"""CA Intermediate Paper 6 (FM & SM) companion. Run: streamlit run app.py"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="CA Inter Paper 6 Companion", layout="wide", initial_sidebar_state="expanded")

from components.footer import render_fair_use_banner, render_footer  # noqa: E402
from config.icai_resources import HUB_TILES, emblem_svg, is_canonical_icai_url  # noqa: E402
from modules.dashboard import render_dashboard  # noqa: E402
from modules.evaluation_sandbox import render_sandbox  # noqa: E402
from modules.gemini_tutor import render_tutor  # noqa: E402
from modules.onboarding import render_onboarding  # noqa: E402
from modules.revision_engine import render_revision  # noqa: E402
from modules.study_scheduler import render_scheduler  # noqa: E402

CSS = """
<style>
.stApp { background:#FFFFFF; color:#0F172A; }
section[data-testid="stSidebar"] { background:#F8FAFC; border-right:1px solid #BAE6FD; }
h1,h2,h3,h4,p,li,label { color:#0F172A; }
.hdr { display:flex; align-items:center; gap:16px; padding:14px 18px; background:#F8FAFC;
       border:1px solid #BAE6FD; border-radius:14px; box-shadow:0 4px 14px rgba(15,23,42,.08); margin-bottom:12px; }
.hdr h1 { margin:0; font-size:1.5rem; }
.tile { display:block; padding:16px; border:1px solid #0284C7; border-radius:12px; background:#FFFFFF;
        box-shadow:0 2px 8px rgba(15,23,42,.08); text-decoration:none !important; color:#0F172A !important;
        transition:transform .15s, box-shadow .15s; min-height:84px; }
.tile:hover { transform:translateY(-3px); box-shadow:0 8px 20px rgba(2,132,199,.25); }
.tile b { color:#0284C7; } .tile span { font-size:.82rem; color:#475569; }
.fair-use { font-size:.78rem; color:#334155; background:#F8FAFC; border:1px solid #BAE6FD;
            border-left:4px solid #0284C7; border-radius:10px; padding:10px 14px; margin:8px 0; }
.badge { display:inline-block; border:2px solid #0284C7; border-radius:8px; padding:3px 10px;
         font-weight:700; color:#0F172A; background:#fff; }
.sticky { background:#FEF3C7; border:2px solid #F59E0B; border-radius:6px; padding:8px 14px;
          box-shadow:3px 3px 8px rgba(15,23,42,.12); }
.mapped { background:#E0F2FE; border-left:4px solid #0284C7; padding:8px 12px; border-radius:8px; margin-bottom:10px; }
</style>
"""


def render_header() -> None:
    st.markdown(
        f"<div class='hdr'>{emblem_svg(64)}<div><h1>CA Intermediate: Paper 6 FM &amp; SM Companion</h1>"
        "<span style='color:#475569'>Faculty-led revision, AI doubt-solving and progress tracking</span></div></div>",
        unsafe_allow_html=True,
    )


def render_hub_tiles() -> None:
    cols = st.columns(len(HUB_TILES))
    for col, tile in zip(cols, HUB_TILES):
        if not is_canonical_icai_url(tile.url):
            continue
        col.markdown(
            f"<a class='tile' href='{tile.url}' target='_blank' rel='noopener noreferrer'>"
            f"<b>{tile.title}</b><br><span>{tile.subtitle}</span></a>",
            unsafe_allow_html=True,
        )


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(emblem_svg(56), unsafe_allow_html=True)
        profile = render_onboarding()
        st.markdown("---")
        st.caption("Educational fair-use companion. Not affiliated with ICAI.")

    render_header()
    render_fair_use_banner()
    render_hub_tiles()
    st.write("")
    st.info(f"CA {profile.name}: {profile.diet.label} diet is "
            f"{(profile.diet.exam_date - __import__('datetime').date.today()).days} days away.")

    tabs = st.tabs(["Revision and Cue Cards", "ELA10 AI Tutor", "Self-Evaluation",
                    "Study Scheduler", "Progress Dashboard"])
    with tabs[0]:
        render_revision()
    with tabs[1]:
        render_tutor()
    with tabs[2]:
        render_sandbox()
    with tabs[3]:
        render_scheduler()
    with tabs[4]:
        render_dashboard()
    render_footer()


main()
