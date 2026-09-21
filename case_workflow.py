"""Session-scoped pre-drafting workflow and dependency invalidation."""
from hashlib import sha256
import json
import streamlit as st
from services.case_service import CaseService
from services.research_service import ResearchService
from services.evidence_service import MAX_FILES, MAX_BATCH_BYTES, extract_supporting_document
from services.demo_case import demo_plan, demo_research, demo_strategy
from utils.helpers import escape_markdown
from utils.validators import AppError


def invalidate_strategy() -> None:
    st.session_state.pop("case_strategy", None)
    st.session_state.pop("case_strategy_signature", None)
    if st.session_state.get("draft_reply"):
        st.session_state["case_draft_stale"] = True


def evidence_changed() -> None:
    st.session_state["case_evidence_dirty"] = True
    invalidate_strategy()


def research_changed() -> None:
    st.session_state.pop("case_research", None)
    st.session_state.pop("case_researched_at", None)
    invalidate_strategy()


def case_record() -> dict:
    plan = st.session_state.get("case_plan")
    research = st.session_state.get("case_research")
    return {
        "notice": st.session_state["analysis"].model_dump(mode="json"),
        "availability_labels_are_unverified_client_reports": True,
        "document_availability": [{"name": d.name, "origin": d.origin, "status": st.session_state.get(f"case_need_{i}", "Awaiting client")} for i, d in enumerate(plan.documents if plan else [])],
        "evidence": [{"id": d["id"], "filename": d["name"], "findings": d["review"].model_dump(mode="json"), "extraction_warnings": d["warnings"]} for d in st.session_state.get("case_files", [])],
        "client_explanation_unverified": st.session_state.get("case_client_notes", ""),
        "research": research.model_dump(mode="json") if research else None,
        "research_scope": st.session_state.get("case_topics", ""),
        "research_checked_at": st.session_state.get("case_researched_at", "Not searched"),
        "research_limitation": "Live research was explicitly omitted; no external authorities may be invented." if st.session_state.get("case_skip_research") and not research else "Source links are located, not certified legal conclusions; jurisdiction, year and subsequent treatment need CA review.",
    }


def record_signature() -> str:
    return sha256(json.dumps(case_record(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def strategy_ready() -> bool:
    return bool(st.session_state.get("case_strategy")) and not st.session_state.get("case_evidence_dirty", False) and st.session_state.get("case_strategy_signature") == record_signature()


def safe_action(action) -> None:
    try:
        action()
        st.session_state.pop("case_error", None)
    except AppError as exc:
        st.session_state["case_error"] = str(exc)
    except Exception:
        st.session_state["case_error"] = "This stage could not be completed. Existing work is preserved; please retry."


def identify_documents() -> None:
    with st.spinner("Identifying the evidence needed for each issue…"):
        analysis = st.session_state["analysis"]
        plan = demo_plan(analysis) if st.session_state.get("demo") else CaseService().plan_documents(analysis)
        st.session_state["case_plan"] = plan
        st.session_state["case_topics"] = "\n\n".join(plan.public_research_topics)
        research_changed()


def review_evidence() -> None:
    uploaded = st.session_state.get("case_uploads", [])
    if st.session_state.get("demo") and uploaded:
        raise AppError("Offline sample mode does not analyze real client files. Decode a notice in live mode first, or continue the sample with no files.")
    if len(uploaded) > MAX_FILES or sum(f.size for f in uploaded) > MAX_BATCH_BYTES:
        raise AppError("Upload at most 10 supporting documents, totaling no more than 50 MB.")
    prepared = []
    cache = st.session_state.setdefault("case_file_cache", {})
    with st.status("Reviewing available client documents…", expanded=True) as progress:
        service = CaseService() if uploaded else None
        for file in uploaded:
            data = file.getvalue()
            digest = sha256(data).hexdigest()
            progress.update(label=f"Reviewing document {len(prepared) + 1} of {len(uploaded)}…")
            # Cache by extension too: identical bytes with a different declared format must be revalidated.
            key = (digest, file.name.rsplit(".", 1)[-1].lower())
            if key not in cache:
                text, warnings = extract_supporting_document(data, file.name)
                cache[key] = {"text": text, "warnings": warnings}
            stored = cache[key]
            if "review" not in stored:
                stored["review"] = service.review_document(stored["text"], st.session_state["analysis"])
            prepared.append({"id": f"E{len(prepared) + 1}", "name": file.name, "hash": digest, **stored})
        st.session_state["case_files"] = prepared
        st.session_state["case_evidence_dirty"] = False
        invalidate_strategy()
        progress.update(label="Available evidence reviewed" if prepared else "No supporting files provided; gaps retained", state="complete", expanded=False)


def run_research() -> None:
    with st.spinner("Researching provisions and judgments on both sides…"):
        if st.session_state.get("demo"):
            research, timestamp = demo_research(), "Offline example — no web search"
        else:
            research, timestamp = ResearchService().research(st.session_state.get("case_topics", ""))
        st.session_state["case_research"] = research
        st.session_state["case_researched_at"] = timestamp
        invalidate_strategy()


def prepare_strategy() -> None:
    if st.session_state.get("case_evidence_dirty"):
        raise AppError("Review the changed supporting files before preparing the strategy.")
    if not st.session_state.get("case_research") and not st.session_state.get("case_skip_research"):
        raise AppError("Run legal research first or explicitly record that it remains outstanding.")
    with st.spinner("Building the issue-by-issue strategy and checking weaknesses…"):
        case = case_record()
        strategy = demo_strategy(st.session_state["analysis"], case) if st.session_state.get("demo") else CaseService().prepare_strategy(case)
        st.session_state["case_strategy"] = strategy
        st.session_state["case_strategy_signature"] = record_signature()


def show_authorities(authorities) -> None:
    for authority in authorities:
        with st.container(border=True):
            st.markdown(f"**{escape_markdown(authority.title)}**")
            st.caption(f"{authority.kind} · {authority.position}")
            st.text(f"Reference: {authority.reference}\nCourt / issuer: {authority.court_or_issuer}\nDate / applicable period: {authority.date_or_effective_period}")
            st.text(f"Proposition: {authority.proposition}\nIssue: {authority.issue}\nApplication / distinctions: {authority.relevance_and_distinctions}")
            st.text(f"Pinpoint: {authority.pinpoint or 'Not established'}\nStatus checks: {authority.status_checks}")
            st.link_button("Open official source", authority.source_url)
            st.caption("Source link located by search. Legal applicability and subsequent treatment require review.")


def render_case_workflow() -> bool:
    st.divider()
    st.subheader("3 · Gather & analyse client documents")
    st.caption("Provide what is available. Missing evidence stays visible and is never assumed to support the client.")
    if not st.session_state.get("case_plan"):
        st.button("Identify key documents", on_click=lambda: safe_action(identify_documents), type="primary")
        st.info("Identify the document requirements before preparing the reply.")
        if st.session_state.get("case_error"):
            st.error(st.session_state["case_error"])
        return False
    plan = st.session_state["case_plan"]
    for index, need in enumerate(plan.documents):
        with st.expander(f"{index + 1}. {escape_markdown(need.name)}", expanded=False):
            st.caption(need.origin)
            st.text(f"Issue: {need.issue}\nWhy needed: {need.purpose}")
            st.selectbox("Client availability", ["Awaiting client", "Provided — upload below", "Unavailable", "Not applicable — explain below"], key=f"case_need_{index}", on_change=invalidate_strategy)
    st.file_uploader("Upload available supporting documents", type=["pdf", "docx", "xlsx", "csv", "txt"], accept_multiple_files=True, key="case_uploads", on_change=evidence_changed, help="Up to 10 files; 20 MB each; 50 MB combined. PDF supports scanned pages. Export photos to PDF.")
    st.caption("Uploads go to the configured AI provider for document review. They are not attached to the final reply automatically.")
    st.text_area("Client explanation & missing-document notes", key="case_client_notes", height=120, on_change=invalidate_strategy, max_chars=12000, placeholder="Explain documents still awaited, factual instructions, and why any requirement is not applicable. Client statements remain unverified until supported.")
    st.button("Analyse available documents", on_click=lambda: safe_action(review_evidence))
    if st.session_state.get("case_evidence_dirty"):
        st.warning("Supporting files changed. Analyse them before rebuilding the strategy.")
    for file in st.session_state.get("case_files", []):
        with st.expander(escape_markdown(f"{file['id']} · {file['name']} — evidence review")):
            for warning in file["warnings"]:
                st.warning(warning)
            for finding in file["review"].findings:
                st.text(f"{finding.effect}: {finding.observation}\nRelevance: {finding.relevance}\nSource excerpt: {finding.source_quote}")
            for gap in file["review"].missing_information:
                st.text(f"Gap: {gap}")

    st.subheader("4 · Research applicable provisions")
    st.caption("Research acts, rules, regulations, circulars and notifications for the relevant period. Keep this separate from sections invoked in the notice.")
    st.text_area("Public legal research topics", key="case_topics", height=160, max_chars=5000, on_change=research_changed)
    st.caption("Review these topics before searching. Only this field is sent to web search; remove client names, identifiers, amounts and private facts. Include the legal period and jurisdiction where known.")
    st.button("Research law & case law", type="primary", on_click=lambda: safe_action(run_research))
    research = st.session_state.get("case_research")
    if research:
        st.caption(f"Research run: {st.session_state.get('case_researched_at', '')}")
        st.text(research.search_summary)
        show_authorities([a for a in research.authorities if a.kind != "Case law"])
        if not any(a.kind != "Case law" for a in research.authorities):
            st.info("No source-linked statutory instruments are available from this run.")

    st.subheader("5 · Examine case law on both sides")
    st.caption("Assess the holding, factual fit, binding value and subsequent treatment—not just a favorable headnote.")
    if research:
        for position in ("For client", "Against client", "Mixed / neutral"):
            st.markdown(f"**{position}**")
            cases = [a for a in research.authorities if a.kind == "Case law" and a.position == position]
            show_authorities(cases)
            if not cases:
                st.caption("No source-linked judgment established in this category. This is a research gap, not proof that no authority exists.")
        for gap in research.gaps:
            st.warning(gap)
    else:
        st.info("Run the research step to find judgments supporting and challenging the proposed position.")
        st.checkbox("Proceed with legal research outstanding; keep this limitation in the strategy", key="case_skip_research", on_change=invalidate_strategy)

    st.subheader("6 · Settle the response strategy")
    st.caption("Combine the notice, available evidence, competing authorities and procedural checks. Review the proposed position before generating the final reply.")
    st.button("Prepare strategy", type="primary", disabled=bool(st.session_state.get("case_evidence_dirty")) or (not research and not st.session_state.get("case_skip_research")), on_click=lambda: safe_action(prepare_strategy))
    strategy = st.session_state.get("case_strategy")
    if strategy and strategy_ready():
        st.text(strategy.overall_approach)
        for issue in strategy.issues:
            with st.expander(escape_markdown(issue.issue), expanded=True):
                for label, values in [("Established facts", issue.established_facts), ("Evidence references", issue.evidence_references), ("Missing facts", issue.missing_facts), ("Authorities to use", issue.authorities_to_use)]:
                    st.text(f"{label}: " + ("\n• " + "\n• ".join(values) if values else "Not established"))
                st.text(f"Primary position: {issue.primary_position}\nAlternative: {issue.alternative_position}\nAdverse arguments and response: {issue.adverse_arguments_and_response}")
        for label, values in [("Procedural checks", strategy.procedural_checks), ("Contradictions to resolve", strategy.contradictions), ("Before filing", strategy.pre_filing_actions)]:
            if values:
                st.markdown(f"**{label}**")
                for value in values:
                    st.text(f"• {value}")
    if st.session_state.get("case_error"):
        st.error(st.session_state["case_error"])
    return strategy_ready()
