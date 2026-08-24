"""Final Thesis page — BUY/HOLD/AVOID recommendation and full report download.

Thesis generation is an explicit, separate action requiring an LLM
call — never triggered automatically — consistent with the rest of
this app's human-in-the-loop design.
"""

from __future__ import annotations

import streamlit as st

from app.core.exceptions import ConfigurationError, LLMProviderError


def _generate_docx_bytes(ctx) -> bytes:
    """Generate the DOCX report to a temp file and return its bytes.
    Extracted as a small helper so the DOCX download button can call it
    directly rather than duplicating the tempfile-staging logic inline."""
    import tempfile
    from pathlib import Path
    from app.reports.docx_export import generate_docx_report

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / f"{ctx.company.ticker}_report.docx"
        generate_docx_report(ctx, docx_path)
        return docx_path.read_bytes()


def render() -> None:
    st.header("Final Thesis & Report")

    company = st.session_state.get("company")
    if company is None:
        st.info("Load a company on the Company Input page first.")
        return

    st.subheader("Investment Thesis")
    st.caption(
        "Generating a thesis requires GOOGLE_API_KEY (free tier) or OPENAI_API_KEY to " \
        "be configured and calls "
        "the LLM. This is never done automatically."
    )

    if st.button("Generate Investment Thesis"):
        from app.config import get_settings
        try:
            get_settings().require_any_llm_key()
        except ConfigurationError as exc:
            st.error(str(exc))
        else:
            from app.ai.llm_client import get_default_llm_client, UsageTrackingLLMClient
            from app.ai.thesis_generator import generate_investment_thesis

            all_interps = (
                st.session_state.get("business_interpretations", [])
                + st.session_state.get("management_interpretations", [])
                + st.session_state.get("governance_interpretations", [])
            )
            claims = [(i.interpretation_id, i.claim) for i in all_interps]

            with st.spinner("Generating thesis..."):
                try:
                    client = get_default_llm_client()
                    usage_log = st.session_state.setdefault("llm_usage_log", [])
                    client = UsageTrackingLLMClient(client, usage_log)
                    thesis = generate_investment_thesis(
                        company_name=company.name,
                        metrics=st.session_state.get("fundamental_metrics", []),
                        trends=st.session_state.get("trends", []),
                        interpretation_claims=claims,
                        llm_client=client,
                    )
                    st.session_state["thesis"] = thesis
                except LLMProviderError as exc:
                    st.error(f"Thesis generation failed: {exc}")

    thesis = st.session_state.get("thesis")
    if thesis:
        st.success(f"Recommendation: **{thesis.recommendation.value.upper()}**")
        st.write(thesis.core_thesis)

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Counterarguments**")
            for c in thesis.counterarguments:
                st.write(f"- {c}")
        with col2:
            st.write("**Catalysts**")
            for c in thesis.catalysts:
                st.write(f"- {c}")

        st.write("**Thesis Invalidation Triggers**")
        for t in thesis.invalidation_triggers:
            st.write(f"- {t.condition} *(basis: {t.threshold_basis})*")

        if thesis.data_limitations:
            st.warning("**Data Limitations**\n" + "\n".join(f"- {d}" for d in thesis.data_limitations))

    st.markdown("---")
    st.subheader("Download Full Report")
    st.caption(
        "Generates the full 19-section report from everything currently loaded, "
        "even if some sections (e.g. thesis) are not yet available."
    )

    if st.button("Generate Report"):
        from app.reports.generator import ReportContext, generate_report

        ctx = ReportContext(
            company=company,
            statements=st.session_state.get("statements", []),
            fundamental_metrics=st.session_state.get("fundamental_metrics", []),
            cashflow_metrics=st.session_state.get("cashflow_metrics", []),
            working_capital_metrics=st.session_state.get("working_capital_metrics", []),
            shareholder_metrics=st.session_state.get("shareholder_metrics", []),
            technical_metrics=st.session_state.get("technical_metrics", []),
            valuation_metrics=st.session_state.get("valuation_metrics", []),
            trends=st.session_state.get("trends", []),
            business_interpretations=st.session_state.get("business_interpretations", []),
            management_interpretations=st.session_state.get("management_interpretations", []),
            governance_interpretations=st.session_state.get("governance_interpretations", []),
            risks=st.session_state.get("risks", []),
            investment_score=st.session_state.get("investment_score"),
            thesis=st.session_state.get("thesis"),
            human_reviews=st.session_state.get("human_reviews", []),
            audit_trail=(
                st.session_state["audit_trail"].entries
                if st.session_state.get("audit_trail") is not None else []
            ),
        )
        report_text = generate_report(ctx)

        from app.reports.history import build_history_entry
        history_entry = build_history_entry(ctx, report_text)
        st.session_state["report_history"] = st.session_state.get("report_history", []) + [history_entry]

        with st.expander("Read Report Here", expanded=True):
            st.caption(
                "Rendered directly in the app — no download needed to read it."
            )
            st.markdown(report_text)

        st.markdown("**Download for offline use / sharing:**")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Report (Word .docx)", data=_generate_docx_bytes(ctx),
                file_name=f"{company.ticker}_equity_research_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                help="Recommended if you want a file to open, print, or "
                     "share — opens directly and readably in Microsoft Word.",
            )
        with col2:
            st.download_button(
                "Download Report (Markdown)", data=report_text,
                file_name=f"{company.ticker}_equity_research_report.md", mime="text/markdown",
                help="Plain text with markdown syntax (##, **, etc.) — useful "
                     "for version control or further editing, but won't render "
                     "nicely if you just double-click it in Windows (opens in "
                     "Notepad showing the raw syntax). Use the .docx download "
                     "or the 'Read Report Here' section above instead if you "
                     "just want to read it.",
            )

        if ctx.audit_trail:
            import json
            from app.reports.generator import generate_audit_trail_export

            audit_json = json.dumps(generate_audit_trail_export(ctx), indent=2, default=str)
            st.download_button(
                f"Download Audit Trail ({len(ctx.audit_trail)} entries, JSON)",
                data=audit_json, file_name=f"{company.ticker}_audit_trail.json",
                mime="application/json",
            )
            with st.expander("Preview Audit Trail"):
                for entry in ctx.audit_trail:
                    st.write(f"**{entry.claim}**")
                    if entry.source:
                        st.caption(f"Source: {entry.source} | Confidence: {entry.confidence.value}")
                    if entry.calculation:
                        st.caption(f"Calculation: {entry.calculation}")
                    if entry.evidence:
                        st.caption(f"Evidence: {entry.evidence}")
                    st.markdown("---")
        else:
            st.caption("No audit trail entries recorded for this run.")

    report_history = st.session_state.get("report_history", [])
    if report_history:
        st.markdown("---")
        st.subheader(f"Report History ({len(report_history)})")
        st.caption(
            "Every report generated in this session, oldest first. Resets when "
            "a new company is loaded on Company Input. Included in Save Session "
            "so history survives across sessions too."
        )

        from app.reports.history import summarize_score_progression

        rows = summarize_score_progression(report_history)
        st.table([{k: v for k, v in row.items() if k != "entry_id"} for row in rows])

        entries_by_id = {e.entry_id: e for e in report_history}
        for row in reversed(rows):  # show newest first for browsing
            entry = entries_by_id[row["entry_id"]]
            with st.expander(f"{row['Generated']} — Score: {row['Score']}, {row['Recommendation']}"):
                st.download_button(
                    "Download This Report (Markdown)", data=entry.report_markdown,
                    file_name=f"{entry.ticker}_report_{entry.generated_at.strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown", key=f"history_download_{entry.entry_id}",
                )
                st.markdown(entry.report_markdown)
