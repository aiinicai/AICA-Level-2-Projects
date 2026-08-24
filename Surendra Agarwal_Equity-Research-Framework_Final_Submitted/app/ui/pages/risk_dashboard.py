"""Risk Dashboard page — risk register, major risks, governance flags,
plus every AI-assisted batch extraction action (risk, business/
management commentary, pledge disclosure).

All three extraction buttons share a common confirm-then-run flow:
1. Click the button -> shows a rough upfront time estimate and asks
   for confirmation (a real user hit a multi-minute, invisible retry
   storm processing a 194-page real document with no warning beforehand
   — this closes that gap).
2. Confirm -> runs with a real progress bar (page N of M), not a
   generic spinner, and a small deliberate pacing delay between calls
   (configurable via LLM_REQUEST_DELAY_SECONDS) that proactively
   reduces how often the account's rate limit gets hit in the first
   place — see app/ai/rate_limiting.py for the full rationale.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st


def risks_to_rows(risks: list) -> list[dict]:
    """Pure function: RiskItem list -> table rows."""
    return [
        {
            "Category": r.category.value.title(), "Severity": r.severity.value.upper(),
            "Description": r.description, "Mitigation": r.mitigation or "—",
        }
        for r in risks
    ]


def _render_confirm_and_run(
    *, state_key: str, button_label: str, num_pages: int,
    execute_fn: Callable[[object, float, Callable[[str], Callable[[int, int], None]]], object],
    on_result: Callable[[object], None],
) -> None:
    """Shared confirm-then-run UI flow for a batch LLM extraction action.

    Args:
        state_key: unique key namespacing this action's session_state
            and widget keys (so multiple instances on one page don't collide).
        button_label: the initial trigger button's label.
        num_pages: page count used for the upfront duration estimate.
        execute_fn: called as execute_fn(client, delay_seconds, make_progress_cb)
            once the user confirms. make_progress_cb(prefix="") returns a
            progress_callback(current, total) function that updates a
            shared progress bar/status text — call it once per logical
            phase if the action involves multiple batch calls (e.g.
            business pages then management pages), each with its own prefix.
        on_result: called with whatever execute_fn returns, to do the
            actual session_state writes and show a final success/warning message.
    """
    from app.ai.rate_limiting import estimate_batch_duration_seconds, format_duration_estimate
    from app.config import get_settings

    settings = get_settings()
    delay = settings.llm_request_delay_seconds
    pending_key = f"_pending_{state_key}"

    if st.button(button_label, key=f"trigger_{state_key}"):
        st.session_state[pending_key] = True

    if not st.session_state.get(pending_key):
        return

    if settings.google_api_key:
        provider_note = f"Google Gemini ({settings.gemini_model})" + (
            ", with OpenAI as an automatic fallback if a Gemini call fails"
            if settings.openai_api_key else ""
        )
    elif settings.openai_api_key:
        provider_note = f"OpenAI ({settings.openai_model})"
    else:
        provider_note = "your configured LLM provider"

    min_s, max_s = estimate_batch_duration_seconds(num_pages, delay)
    st.warning(
        f"This will process {num_pages} page(s) via {num_pages} separate API "
        f"call(s) using **{provider_note}**, estimated "
        f"**{format_duration_estimate(min_s, max_s)}** (a rough estimate — "
        f"actual time depends on rate limits and network conditions). A "
        f"{delay:.1f}s pause between calls is applied to reduce rate-limit retries."
    )
    col1, col2 = st.columns(2)
    confirm = col1.button("Confirm and Run", key=f"confirm_{state_key}")
    cancel = col2.button("Cancel", key=f"cancel_{state_key}")

    if cancel:
        st.session_state[pending_key] = False
        st.rerun()

    if confirm:
        st.session_state[pending_key] = False

        from app.core.exceptions import ConfigurationError
        try:
            get_settings().require_any_llm_key()
        except ConfigurationError as exc:
            st.error(str(exc))
            return

        from app.ai.llm_client import get_default_llm_client, UsageTrackingLLMClient
        client = get_default_llm_client()
        usage_log = st.session_state.setdefault("llm_usage_log", [])
        client = UsageTrackingLLMClient(client, usage_log)

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def make_progress_cb(prefix: str = ""):
            def _cb(current: int, total: int) -> None:
                progress_bar.progress(current / total if total else 1.0)
                label = f"{prefix}{current} of {total}..." if prefix else f"Processing page {current} of {total}..."
                status_text.text(label)
            return _cb

        result = execute_fn(client, delay, make_progress_cb)
        progress_bar.empty()
        status_text.empty()
        on_result(result)


def render() -> None:
    st.header("Risk Dashboard")

    company = st.session_state.get("company")
    if company is None:
        st.info("Load a company on the Company Input page first.")
        return

    risks = st.session_state.get("risks", [])
    if risks:
        severe = sum(1 for r in risks if r.severity.value in ("high", "severe"))
        cols = st.columns(3)
        cols[0].metric("Total Risks Identified", len(risks))
        cols[1].metric("High/Severe", severe)
        cols[2].metric("Low/Moderate", len(risks) - severe)

        st.subheader("Risk Register")
        st.table(risks_to_rows(risks))
    else:
        st.info(
            "No risks identified yet. Deterministic financial risks are computed "
            "automatically on Company Input; qualitative risks require an uploaded "
            "annual report PDF and an OpenAI API key (see Final Thesis page)."
        )

    document_evidence = st.session_state.get("document_evidence", [])

    # --- AI-Assisted Risk Extraction ---
    if document_evidence:
        from app.core.enums import DocumentSectionType
        from app.documents.extractor import filter_by_section

        risk_pages = filter_by_section(document_evidence, DocumentSectionType.RISK)
        risk_pages += filter_by_section(document_evidence, DocumentSectionType.GOVERNANCE)

        st.subheader("AI-Assisted Risk Extraction")
        st.caption(
            f"{len(risk_pages)} document page(s) classified as Risk/Governance "
            "available for extraction. Requires GOOGLE_API_KEY (free tier) or OPENAI_API_KEY."
        )

        def _run_risk_extraction(client, delay, make_progress_cb):
            from app.analysis.risk import extract_risks_batch
            return extract_risks_batch(
                risk_pages, client, delay_seconds=delay, progress_callback=make_progress_cb(),
            )

        def _on_risk_result(new_risks):
            st.session_state["risks"] = st.session_state.get("risks", []) + new_risks
            st.success(f"Extracted {len(new_risks)} additional risk(s). Refresh to see them above.")

        _render_confirm_and_run(
            state_key="risk_extraction", button_label="Extract Qualitative Risks from Document",
            num_pages=len(risk_pages), execute_fn=_run_risk_extraction, on_result=_on_risk_result,
        )

    # --- Business & Management Commentary Extraction ---
    if document_evidence:
        from app.core.enums import DocumentSectionType
        from app.documents.extractor import filter_by_section

        business_pages = filter_by_section(document_evidence, DocumentSectionType.BUSINESS)
        management_pages = filter_by_section(document_evidence, DocumentSectionType.MANAGEMENT_DISCUSSION)
        total_bm_pages = len(business_pages) + len(management_pages)

        st.subheader("Business & Management Commentary Extraction")
        st.caption(
            "Populates the AI-IDS Score's Business/Management component — "
            "without running this, that component stays permanently "
            "'unavailable' since there is no other way to supply this data. "
            "Requires GOOGLE_API_KEY (free tier) or OPENAI_API_KEY."
        )

        def _run_bm_extraction(client, delay, make_progress_cb):
            from app.ai.document_analysis import analyze_evidence_batch
            business_results = analyze_evidence_batch(
                business_pages, client, focus="business overview, products, and competitive position",
                delay_seconds=delay, progress_callback=make_progress_cb("Business page "),
            )
            management_results = analyze_evidence_batch(
                management_pages, client, focus="management commentary, strategic outlook, and capex plans",
                delay_seconds=delay, progress_callback=make_progress_cb("Management page "),
            )
            return business_results, management_results

        def _on_bm_result(result):
            business_results, management_results = result
            st.session_state["business_interpretations"] = (
                st.session_state.get("business_interpretations", []) + business_results
            )
            st.session_state["management_interpretations"] = (
                st.session_state.get("management_interpretations", []) + management_results
            )
            if not business_results and not management_results:
                st.warning(
                    "No business/management-relevant content was found on the "
                    "classified pages available. The Business/Management "
                    "component will remain unavailable."
                )
            else:
                st.success(
                    f"Extracted {len(business_results)} business claim(s) and "
                    f"{len(management_results)} management claim(s). Go to the "
                    "AI-IDS Score page and click Compute AI-IDS Score to see "
                    "this component populated."
                )

        _render_confirm_and_run(
            state_key="bm_extraction", button_label="Extract Business & Management Commentary",
            num_pages=total_bm_pages, execute_fn=_run_bm_extraction, on_result=_on_bm_result,
        )

    # --- Promoter Pledge Disclosure Analysis ---
    pledge_pages = [e for e in document_evidence if e.document_type.value == "pledge_disclosure"]
    if pledge_pages:
        st.subheader("Promoter Pledge Disclosure Analysis")
        st.caption(
            f"{len(pledge_pages)} page(s) from an uploaded pledge-disclosure "
            "document available for analysis. Requires GOOGLE_API_KEY (free tier) or OPENAI_API_KEY. The "
            "extraction distinguishes a pledge on THIS company's shares from "
            "a pledge on an upstream holding entity's shares — only the "
            "former sets Promoter Pledge %."
        )

        def _run_pledge_extraction(client, delay, make_progress_cb):
            from app.ai.pledge_extraction import extract_pledge_disclosure_batch, summarize_pledge_status
            disclosures = extract_pledge_disclosure_batch(
                pledge_pages, client, delay_seconds=delay, progress_callback=make_progress_cb(),
            )
            return summarize_pledge_status(disclosures)

        def _on_pledge_result(summary):
            if summary["latest_pledge_pct"] is None:
                st.warning(
                    "No pledge/encumbrance disclosure content was found in the "
                    "uploaded document — Promoter Pledge remains unavailable. "
                    "This is NOT the same as confirming zero pledge; if you know "
                    "independently that there is no pledge, use the 'I confirm "
                    "there is no promoter pledge currently' checkbox above instead."
                )
                return

            from app.analysis.shareholder import compute_all_shareholder_metrics
            from app.ui.pages.company_input import apply_promoter_override

            statements = st.session_state.get("statements", [])
            updated_statements = apply_promoter_override(
                statements, None, summary["latest_pledge_pct"] / 100.0,
            )
            st.session_state["statements"] = updated_statements
            st.session_state["shareholder_metrics"] = compute_all_shareholder_metrics(updated_statements)

            from app.core.audit import AuditTrail
            trail = st.session_state.get("audit_trail") or AuditTrail()
            trail.record(
                f"Promoter Pledge set to {summary['latest_pledge_pct']:.2f}% "
                f"from AI-extracted pledge disclosure (as of {summary['as_of_date']})",
                source="Pledge Disclosure PDF (AI-extracted)", confidence="medium",
                evidence=summary["summary"] or "",
            )
            st.session_state["audit_trail"] = trail

            st.success(
                f"Promoter Pledge set to {summary['latest_pledge_pct']:.2f}% "
                f"(as of {summary['as_of_date']}). {summary['summary']}"
            )

        _render_confirm_and_run(
            state_key="pledge_extraction", button_label="Analyze Pledge Disclosure",
            num_pages=len(pledge_pages), execute_fn=_run_pledge_extraction, on_result=_on_pledge_result,
        )
