# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Look and feel shared by every page: the chosen theme and layout, the navigation (sidebar or top bar),
the brand and the Plan & Usage box.

UI layer (Streamlit). The colours and CSS come from ``core.themes`` and ``theme_css``.
"""
import os
from datetime import datetime

import streamlit as st

from core.branding import COPYRIGHT, OWNERSHIP, TAGLINE
from core.themes import DEFAULT_LAYOUT, DEFAULT_THEME, palette
from core.workflow import count_ai_extractions_since, count_user_leases_in_status
from db.database import get_session
from theme_css import build_css


def user_palette(user: dict) -> dict:
    """The colour tokens for this user's saved layout and theme."""
    return palette(user.get("dashboard_layout", DEFAULT_LAYOUT), user.get("theme", DEFAULT_THEME))


def inject_css(user: dict = None) -> dict:
    """Apply the user's layout + theme to the page. Returns the palette in use."""
    tokens = user_palette(user or {})
    st.markdown(build_css(tokens["layout"], tokens["theme"]), unsafe_allow_html=True)
    st.markdown('<div class="lq-footer">{} | {}</div>'.format(OWNERSHIP, COPYRIGHT), unsafe_allow_html=True)
    return tokens


def _pending_count(user: dict) -> int:
    with get_session() as session:
        return count_user_leases_in_status(session, user["user_id"], "Pending Review")


def _plan_usage(user: dict) -> tuple:
    limit = int(os.getenv("PLAN_AI_EXTRACTIONS_PER_MONTH") or 100)
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    with get_session() as session:
        used = count_ai_extractions_since(session, user["user_id"], month_start)
    return used, limit


def render_brand_and_nav(user: dict) -> None:
    """Sidebar layouts: brand, tagline and navigation (the built-in page list is hidden by the CSS). Each person sees only the
    pages their access allows."""
    pending = _pending_count(user)
    rights = set(user.get("rights") or [])
    st.sidebar.markdown(
        '<div class="lq-brand">LeaseIQ <span class="lq-pro">Pro</span></div>'
        '<div class="lq-tag">{}</div>'.format(TAGLINE),
        unsafe_allow_html=True,
    )
    st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard", icon="📊")
    st.sidebar.markdown('<div class="lq-group">Leases</div>', unsafe_allow_html=True)  # a plain label: always readable
    st.sidebar.page_link("pages/2_Leases.py", label="All leases", icon="📄")
    if "edit" in rights:
        st.sidebar.page_link("pages/3_Bulk_Upload.py", label="Bulk Upload", icon="📥")
    if rights & {"approve", "audit"}:
        st.sidebar.markdown('<div class="lq-group">Workflow</div>', unsafe_allow_html=True)
        if "approve" in rights:
            st.sidebar.page_link(
                "pages/4_Approvals.py", label="Approvals" + ("  ({})".format(pending) if pending else ""), icon="✅"
            )
        if "audit" in rights:
            st.sidebar.page_link("pages/5_Audit_Log.py", label="Audit Log", icon="🧾")
    st.sidebar.markdown('<div class="lq-group">Reports</div>', unsafe_allow_html=True)  # the outputs
    st.sidebar.page_link("pages/7_Reports.py", label="Disclosure reports", icon="📑")
    st.sidebar.markdown('<div class="lq-group">Account</div>', unsafe_allow_html=True)
    st.sidebar.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")
    st.sidebar.page_link("pages/8_Future_Roadmap.py", label="Future roadmap", icon=":material/flag:")
    st.sidebar.divider()


def render_plan_box(user: dict) -> None:
    """Sidebar layouts: 'Plan & Usage', how many documents the AI has read this month against a guide limit."""
    used, limit = _plan_usage(user)
    st.sidebar.divider()
    st.sidebar.markdown("**Plan & Usage**")
    st.sidebar.progress(min(1.0, used / limit), text="AI extractions this month: {} of {}".format(used, limit))
    st.sidebar.caption("Free plan (guide limit)")


def render_top_nav(user: dict) -> None:
    """Top-navigation layout: brand, links and a profile menu (name, plan usage) in one bar."""
    pending = _pending_count(user)
    rights = set(user.get("rights") or [])
    with st.container(key="topnav"):
        brand, dash, leases, bulk, approvals, audit, reports, settings, roadmap, account = st.columns(
            [1.3, 0.95, 0.8, 1.0, 1.2, 0.9, 0.9, 0.9, 0.95, 1.5]
        )
        brand.markdown('<div class="lq-brand-top">LeaseIQ <span class="lq-pro">Pro</span></div>', unsafe_allow_html=True)
        dash.page_link("pages/1_Dashboard.py", label="Dashboard")
        leases.page_link("pages/2_Leases.py", label="Leases")
        if "edit" in rights:
            bulk.page_link("pages/3_Bulk_Upload.py", label="Bulk Upload")
        if "approve" in rights:
            approvals.page_link("pages/4_Approvals.py", label="Approvals" + ("  ({})".format(pending) if pending else ""))
        if "audit" in rights:
            audit.page_link("pages/5_Audit_Log.py", label="Audit Log")
        reports.page_link("pages/7_Reports.py", label="Reports")
        settings.page_link("pages/6_Settings.py", label="Settings")
        roadmap.page_link("pages/8_Future_Roadmap.py", label="Roadmap")
        with account.popover(user["name"], icon=":material/account_circle:"):
            st.markdown("**{}**  \nEvaluation edition (no sign-in)".format(user["name"]))
            used, limit = _plan_usage(user)
            st.progress(min(1.0, used / limit), text="AI extractions this month: {} of {}".format(used, limit))
            st.caption("No sign-in is needed in this edition.")


def apply_appearance(user: dict) -> dict:
    """Everything shared by all pages, in the layout the user chose. Returns the palette in use."""
    tokens = inject_css(user)
    if tokens["nav"] == "top":
        render_top_nav(user)
    else:
        render_brand_and_nav(user)
        st.sidebar.markdown("**{}**  \nEvaluation edition (no sign-in)".format(user["name"]))
        render_plan_box(user)
    return tokens
