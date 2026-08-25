"""AI-IDS Score page — overall score, component scores, confidence, evidence.

Weights are interactively adjustable here via sliders, in addition to
the .env-configured defaults (app/config.py's WEIGHT_* variables).
Slider adjustments are session-only — they never write back to .env —
so this page is a genuine "what if I weighted X differently" tool, not
a way to silently change the project's configured defaults.
"""

from __future__ import annotations

import streamlit as st

from app.core.enums import DataStatus

# Maps investment_score.py's component display names (its ScoreComponent.name
# values, and the keys compute_investment_score() expects in its `weights`
# dict) to config.py's snake_case Settings.score_weights keys — the two
# modules were written independently and use different key conventions,
# so this page needs to translate between them rather than assume they match.
_WEIGHT_KEY_MAP = {
    "Fundamentals": "fundamentals",
    "Cash Flow Quality": "cashflow_quality",
    "Business/Management": "business_management",
    "Valuation": "valuation",
    "Technical": "technical",
    "Risk/Governance": "risk_governance",
}


def normalize_weights(raw_weights: dict[str, float]) -> dict[str, float]:
    """Pure function: renormalize arbitrary non-negative slider values so
    they sum to 1.0. Sliders are independent controls, so users will
    rarely land on an exact 100% total — rather than force an awkward
    "must sum to 100" UI constraint, this renormalizes automatically and
    the caller is expected to display both the raw slider values and the
    resulting effective weights so nothing changes invisibly.

    If every input is 0 (or the dict is empty), falls back to equal
    weighting across all keys rather than dividing by zero or returning
    an all-zero weight set (which compute_investment_score would reject).
    """
    total = sum(raw_weights.values())
    if total <= 0:
        n = len(raw_weights) or 1
        return {k: 1.0 / n for k in raw_weights}
    return {k: v / total for k, v in raw_weights.items()}


def render() -> None:
    st.header("AI-Assisted Investment Decision Score (AI-IDS)")

    company = st.session_state.get("company")
    if company is None:
        st.info("Load a company on the Company Input page first.")
        return

    from app.config import get_settings

    settings = get_settings()
    default_pct = {
        display_name: settings.score_weights[config_key] * 100.0
        for display_name, config_key in _WEIGHT_KEY_MAP.items()
    }

    if not st.session_state.get("weight_sliders"):
        st.session_state["weight_sliders"] = dict(default_pct)

    st.subheader("Component Weights")
    st.caption(
        "Adjust to explore 'what if' scenarios — these are session-only and "
        "never change the .env-configured defaults. Values don't need to sum "
        "to 100%; they're automatically renormalized, and the effective "
        "weights actually used are shown below the sliders."
    )

    col1, col2 = st.columns(2)
    columns = [col1, col2, col1, col2, col1, col2]
    raw_weights: dict[str, float] = {}
    for (display_name, _), col in zip(_WEIGHT_KEY_MAP.items(), columns):
        with col:
            raw_weights[display_name] = st.slider(
                display_name, min_value=0.0, max_value=100.0,
                value=st.session_state["weight_sliders"].get(display_name, default_pct[display_name]),
                step=1.0, format="%.0f%%", key=f"slider_{display_name}",
            )
    st.session_state["weight_sliders"] = raw_weights

    def _reset_weights_callback() -> None:
        # Streamlit sliders bound to a `key` ignore their `value=` argument
        # after the first user interaction — the widget's own
        # st.session_state[key] entry becomes the source of truth. An
        # on_click CALLBACK (rather than an `if st.button(...):` block) is
        # required to reset it: callbacks run BEFORE the script reruns and
        # re-instantiates the widgets, so setting session_state[key] here
        # is safe — doing the same thing after the widgets are already
        # instantiated in a normal rerun raises a StreamlitAPIException.
        for display_name in _WEIGHT_KEY_MAP:
            st.session_state[f"slider_{display_name}"] = default_pct[display_name]
        st.session_state["weight_sliders"] = dict(default_pct)

    st.button("Reset to Configured Defaults", on_click=_reset_weights_callback)

    effective_weights = normalize_weights(raw_weights)
    raw_total = sum(raw_weights.values())
    st.caption(
        f"Raw total: {raw_total:.0f}% → Effective (normalized) weights: "
        + ", ".join(f"{k}: {v:.0%}" for k, v in effective_weights.items())
    )

    if st.button("Compute AI-IDS Score"):
        from app.scoring.investment_score import (
            compute_investment_score, score_business_management, score_cashflow_quality,
            score_fundamentals, score_risk_governance, score_technical, score_valuation,
        )
        from app.analysis.peers import compare_to_peers

        fundamental_metrics = st.session_state.get("fundamental_metrics", [])
        cashflow_metrics = st.session_state.get("cashflow_metrics", [])
        technical_metrics = st.session_state.get("technical_metrics", [])
        valuation_metrics = st.session_state.get("valuation_metrics", [])
        risks = st.session_state.get("risks", [])
        business_interps = (
            st.session_state.get("business_interpretations", [])
            + st.session_state.get("management_interpretations", [])
        )

        val_dict = {m.metric_name: m for m in valuation_metrics}
        peers = st.session_state.get("peers", [])
        peer_comparisons = st.session_state.get("peer_comparisons") or compare_to_peers(val_dict, peers)

        components = [
            score_fundamentals(fundamental_metrics),
            score_cashflow_quality(cashflow_metrics),
            score_business_management(business_interps),
            score_valuation(peer_comparisons),
            score_technical(technical_metrics),
            score_risk_governance(risks),
        ]
        st.session_state["investment_score"] = compute_investment_score(
            components, weights=normalize_weights(st.session_state["weight_sliders"]),
        )

    score = st.session_state.get("investment_score")
    if score is None:
        st.info("Click 'Compute AI-IDS Score' to generate the score from currently loaded data.")
        return

    if score.overall_score is not None:
        st.metric("Overall AI-IDS Score", f"{score.overall_score:.1f} / {score.max_possible_score:.0f}")
        if score.renormalized:
            st.caption(
                f"Weights renormalized — unavailable: {', '.join(score.unavailable_components)}"
            )
    else:
        st.warning("Overall score unavailable — no component had usable data.")

    st.subheader("Component Scores")
    rows = [
        {
            "Component": c.name,
            "Score": f"{c.score:.1f}" if c.score is not None else "N/A",
            "Weight": f"{c.weight:.0%}",
            "Weighted": f"{c.weighted_score:.2f}" if c.weighted_score is not None else "—",
            "Confidence": c.confidence.value,
        }
        for c in score.components
    ]
    st.table(rows)

    st.caption(
        "AI-assisted decision support only. Final investment decisions require "
        "human professional judgement."
    )
