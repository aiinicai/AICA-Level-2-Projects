"""Streamlit dashboard shell — Module 14 UI.

This module owns navigation and session state only. Every page's actual
content lives in app/ui/pages/*.py, and every page's actual analysis
logic lives in app/data, app/analysis, app/valuation, app/scoring,
app/reports — this file and the page modules never compute anything
themselves, only call into the already-tested pipeline and display the
result.

Session state keys (all optional; pages must handle any of these being
None/empty, since a user can land on any page before running analysis):
    company, statements, price_df, fundamental_metrics, cashflow_metrics,
    working_capital_metrics, technical_metrics, valuation_metrics,
    trends, risks, business_interpretations, management_interpretations,
    governance_interpretations, investment_score, thesis, human_reviews
"""

from __future__ import annotations

import logging

import streamlit as st

from app.config import get_settings
from app.core.logging_config import configure_logging

logger = logging.getLogger(__name__)

_SESSION_DEFAULTS = {
    "company": None,
    "statements": [],
    "price_df": None,
    "fundamental_metrics": [],
    "cashflow_metrics": [],
    "working_capital_metrics": [],
    "shareholder_metrics": [],
    "technical_metrics": [],
    "valuation_metrics": [],
    "trends": [],
    "risks": [],
    "business_interpretations": [],
    "management_interpretations": [],
    "governance_interpretations": [],
    "investment_score": None,
    "thesis": None,
    "human_reviews": [],
    "document_evidence": [],
    "audit_trail": None,
    "reviewer_name": "",
    "peer_comparisons": [],
    "peers": [],
    "last_dcf_assumptions": None,
    "scenario_set": None,
    "sensitivity_grid": None,
    "weight_sliders": None,
    "report_history": [],
    "llm_usage_log": [],
}

_PAGES = [
    "Company Input",
    "Financial Dashboard",
    "Technical Dashboard",
    "Valuation Dashboard",
    "Risk Dashboard",
    "AI-IDS Score",
    "Human Review",
    "Final Thesis & Report",
]


def _init_session_state() -> None:
    for key, default in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def run() -> None:
    """Main dashboard entry point, called from app/main.py."""
    settings = get_settings()
    configure_logging(settings.log_dir, level=settings.log_level)
    settings.ensure_directories()

    st.set_page_config(
        page_title="Equity Research & Investment Decision Framework",
        page_icon="📊", layout="wide",
    )
    _init_session_state()

    from app.ui.styling import inject_accent_css
    inject_accent_css()

    st.sidebar.title("Equity Research Framework")
    if st.session_state["company"]:
        st.sidebar.success(f"Loaded: {st.session_state['company'].name}")
    else:
        st.sidebar.info("No company loaded yet — start on Company Input.")

    page = st.sidebar.radio("Navigate", _PAGES)

    st.sidebar.markdown("---")
    _render_session_save_load()

    st.sidebar.markdown("---")
    _render_cost_estimate()

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "AI-assisted decision support only. Final investment decisions "
        "require human professional judgement."
    )

    _render_page(page)


def _render_cost_estimate() -> None:
    """Sidebar rough cost estimate — sums estimated_cost_usd across
    every LLM call made this session (both providers, wherever a call
    actually went via FallbackLLMClient). Deliberately labeled as a
    rough estimate, not a bill: token counts come from each provider's
    own API response (accurate), but the per-token PRICING TABLE
    (app/ai/pricing.py) is a periodically-verified snapshot, not a live
    feed — always confirm actual spend against the provider's own
    dashboard, linked directly here for convenience.
    """
    usage_log = st.session_state.get("llm_usage_log", [])
    st.sidebar.subheader("Estimated Session Cost")

    if not usage_log:
        st.sidebar.caption("No AI-assisted calls made yet this session.")
        return

    priced_entries = [e for e in usage_log if e["estimated_cost_usd"] is not None]
    unpriced_count = len(usage_log) - len(priced_entries)
    total_cost = sum(e["estimated_cost_usd"] for e in priced_entries)

    by_provider: dict[str, float] = {}
    for e in priced_entries:
        by_provider[e["provider"]] = by_provider.get(e["provider"], 0.0) + e["estimated_cost_usd"]

    st.sidebar.metric("Total (this session)", f"${total_cost:.4f}")
    for provider, cost in sorted(by_provider.items()):
        st.sidebar.caption(f"{provider}: ${cost:.4f}")

    if unpriced_count:
        st.sidebar.caption(
            f"{unpriced_count} call(s) excluded — model not in the pricing "
            "table or token counts unavailable, never silently counted as $0."
        )

    from app.ai.pricing import PRICING_LAST_VERIFIED
    st.sidebar.caption(
        f"Rough estimate only (pricing table verified {PRICING_LAST_VERIFIED}) — "
        "confirm actual spend at [platform.openai.com/account/usage]"
        "(https://platform.openai.com/account/usage) or "
        "[aistudio.google.com/usage](https://aistudio.google.com/usage)."
    )


def _render_session_save_load() -> None:
    """Sidebar Save/Load Session controls — visible on every page since
    a user might want to save their progress regardless of which page
    they're currently on.

    IMPORTANT: this must build its snapshot from session_io.TRACKED_SESSION_KEYS
    via .get() on each key individually — NEVER dict(st.session_state)
    directly. The sidebar renders BEFORE the current page's body in
    run() below, so on any rerun triggered while viewing a page with
    dynamic widget keys (e.g. the AI-IDS Score sliders), those widgets
    have not been re-declared yet at the point this function executes.
    dict(st.session_state) touches every key present, including those
    not-yet-re-registered widget keys, which Streamlit raises a KeyError
    for — a real crash that was caught by testing this against the
    exact pinned Streamlit version rather than a newer one that
    happened not to trigger it.
    """
    from app.ui.session_io import TRACKED_SESSION_KEYS, deserialize_session, serialize_session

    st.sidebar.subheader("Session")

    if st.session_state.get("company"):
        snapshot = {key: st.session_state.get(key) for key in TRACKED_SESSION_KEYS}
        session_json = serialize_session(snapshot)
        ticker = st.session_state["company"].ticker
        st.sidebar.download_button(
            "Save Session", data=session_json,
            file_name=f"{ticker}_session.json", mime="application/json",
            help="Downloads everything computed so far — financials, metrics, "
                 "risks, thesis, human reviews — so you can resume later "
                 "without re-uploading files or re-running analysis.",
        )
    else:
        st.sidebar.caption("Load a company first to enable Save Session.")

    uploaded_session = st.sidebar.file_uploader(
        "Load Session", type=["json"], key="session_upload",
        help="Restores a previously saved session.json file.",
    )
    if uploaded_session is not None and st.sidebar.button("Restore This Session"):
        try:
            text = uploaded_session.getvalue().decode("utf-8")
            restored, warnings = deserialize_session(text)
        except ValueError as exc:
            st.sidebar.error(f"Could not load session file: {exc}")
        else:
            for key, value in restored.items():
                st.session_state[key] = value
            if warnings:
                st.sidebar.warning(
                    f"Session restored with {len(warnings)} issue(s):\n"
                    + "\n".join(f"- {w}" for w in warnings)
                )
            else:
                st.sidebar.success("Session fully restored.")
            st.rerun()


def _render_page(page: str) -> None:
    # Imported lazily inside the dispatch (not at module top) so that
    # importing dashboard.py alone (e.g. for testing navigation wiring)
    # doesn't require every page module's own heavier imports to succeed.
    if page == "Company Input":
        from app.ui.pages import company_input
        company_input.render()
    elif page == "Financial Dashboard":
        from app.ui.pages import financial_dashboard
        financial_dashboard.render()
    elif page == "Technical Dashboard":
        from app.ui.pages import technical_dashboard
        technical_dashboard.render()
    elif page == "Valuation Dashboard":
        from app.ui.pages import valuation_dashboard
        valuation_dashboard.render()
    elif page == "Risk Dashboard":
        from app.ui.pages import risk_dashboard
        risk_dashboard.render()
    elif page == "AI-IDS Score":
        from app.ui.pages import ai_ids_dashboard
        ai_ids_dashboard.render()
    elif page == "Human Review":
        from app.ui.pages import human_review
        human_review.render()
    elif page == "Final Thesis & Report":
        from app.ui.pages import final_thesis
        final_thesis.render()
