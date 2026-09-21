"""Run with: streamlit run app.py"""
from hashlib import sha256
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from services.demo_service import SAMPLE_TEXT, sample_analysis, sample_draft
from services.document_service import generate_docx
from services.llm_service import LLMService
from services.pdf_service import extract_text_from_pdf
from utils.helpers import clipboard_html, escape_markdown, safe_filename
from utils.ui import apply_styles, render_header, render_metadata, render_deadline, render_summary, render_issue_heading, render_amount, render_section
from utils.validators import AppError, validate_pdf
from services.case_service import CaseService
from services.demo_case import demo_plan
from utils.case_workflow import render_case_workflow, strategy_ready, case_record, record_signature

load_dotenv(Path(__file__).with_name(".env"))
st.set_page_config(page_title="1-Click Tax Notice Decoder", page_icon="📄", layout="centered")

PRIVACY = "Tax documents may contain confidential information. Ensure your organisation permits processing through the configured AI provider."
DISCLAIMER = "AI-assisted draft. Verify facts, legal provisions, portal requirements, attachments and deadlines before submission."
RESULT_KEYS = ("notice_text", "analysis", "draft_reply", "uploaded_filename", "file_hash", "extraction", "demo", "error", "previous_draft")


def clear_result() -> None:
    for key in list(st.session_state):
        if key in RESULT_KEYS or key.startswith(("document_", "case_")):
            del st.session_state[key]


def start_over() -> None:
    clear_result()
    st.session_state["uploader_generation"] = st.session_state.get("uploader_generation", 0) + 1


def use_sample() -> None:
    start_over()
    st.session_state.update(
        notice_text=SAMPLE_TEXT, analysis=sample_analysis(), draft_reply="",
        uploaded_filename="Demo Notice", demo=True, draft_style="Detailed",
        case_plan=demo_plan(sample_analysis()),
        case_topics="\n\n".join(demo_plan(sample_analysis()).public_research_topics),
    )


def regenerate() -> None:
    try:
        if not strategy_ready():
            raise AppError("Prepare an up-to-date strategy using the available evidence and research before generating the reply.")
        analysis = st.session_state["analysis"]
        style = st.session_state.get("draft_style", "Detailed")
        with st.spinner("Drafting your reply…"):
            if st.session_state.get("demo"):
                reply, notes = sample_draft(style), ["Offline example: no client documents or external authorities have been reviewed. Complete all placeholders and legal research before filing."]
            else:
                reply, notes = CaseService().comprehensive_draft(case_record(), st.session_state["case_strategy"], style)
        st.session_state["previous_draft"] = st.session_state.get("draft_reply", "")
        st.session_state["case_previous_draft_signature"] = st.session_state.get("case_draft_signature")
        st.session_state["draft_reply"] = reply
        st.session_state["case_draft_signature"] = record_signature()
        st.session_state["case_draft_stale"] = False
        st.session_state["case_review_notes"] = notes
        st.session_state.pop("error", None)
    except AppError as exc:
        st.session_state["error"] = str(exc)
    except Exception:
        st.session_state["error"] = "The reply could not be generated. Your current edits are preserved. Please retry."


def restore_draft() -> None:
    st.session_state["draft_reply"], st.session_state["previous_draft"] = (
        st.session_state["previous_draft"], st.session_state.get("draft_reply", "")
    )
    st.session_state["case_draft_signature"], st.session_state["case_previous_draft_signature"] = (
        st.session_state.get("case_previous_draft_signature"), st.session_state.get("case_draft_signature")
    )


def process_upload(uploaded) -> None:
    with st.status("Reading notice…", expanded=True) as status:
        try:
            data = uploaded.getvalue()
            validate_pdf(data, uploaded.name, uploaded.type)
            digest = sha256(data).hexdigest()
            if st.session_state.get("file_hash") != digest:
                clear_result()
                st.session_state["file_hash"] = digest
                st.session_state["uploaded_filename"] = uploaded.name
            if not st.session_state.get("notice_text"):
                extraction = extract_text_from_pdf(data, uploaded.name, uploaded.type, lambda msg: status.update(label=msg))
                st.session_state["notice_text"] = extraction.text
                st.session_state["extraction"] = extraction
            service = LLMService()
            if not st.session_state.get("analysis"):
                analysis = service.analyze(st.session_state["notice_text"], lambda msg: status.update(label=msg))
                status.update(label="Checking sections & deadlines…")
                st.session_state["analysis"] = analysis
            if not st.session_state.get("case_plan"):
                status.update(label="Identifying documents to review before drafting…")
                plan = CaseService().plan_documents(st.session_state["analysis"])
                st.session_state["case_plan"] = plan
                st.session_state["case_topics"] = "\n\n".join(plan.public_research_topics)
            st.session_state.pop("error", None)
            status.update(label="Notice decoded", state="complete", expanded=False)
        except AppError as exc:
            st.session_state["error"] = str(exc)
            status.update(label="Processing needs attention", state="error", expanded=False)
        except Exception:
            st.session_state["error"] = "The notice could not be processed. Please retry with a readable PDF."
            status.update(label="Processing needs attention", state="error", expanded=False)


def render_results() -> None:
    analysis = st.session_state["analysis"]
    st.divider()
    if st.session_state.get("demo"):
        st.info("Demo Notice · Fictional training example. Analysis and replies are prepared offline; no AI request is made.")
    st.markdown('<div class="section-eyebrow">Your notice, made clear</div><div class="result-heading"><h2>Notice Decoded</h2><span class="review-tag">Ready for your review</span></div>', unsafe_allow_html=True)
    st.caption(escape_markdown(st.session_state.get("uploaded_filename", "")))
    extraction = st.session_state.get("extraction")
    if extraction:
        st.caption(f"{extraction.page_count} pages read")
        for warning in extraction.warnings:
            st.warning(warning)
    metadata = [("Type", analysis.notice_type), ("Department", analysis.department), ("Assessment Year", analysis.assessment_year), ("Financial Year", analysis.financial_year), ("Notice Date", analysis.notice_date)]
    with st.container(border=True, key="notice_details"):
        render_metadata(metadata)
        deadline = analysis.response_deadline
        render_deadline(deadline)
        if deadline.source_quote:
            with st.expander("Deadline wording in the notice"):
                st.text(deadline.source_quote)

    st.subheader("What the Department is Asking")
    st.caption("AI-assisted summary of the notice; verify against the original.")
    render_summary(analysis.executive_summary)
    if len(analysis.executive_summary) > 6:
        st.caption("Additional extracted points are retained below and included when drafting.")

    st.subheader("Issues Identified")
    if not analysis.issues:
        st.info("No specific issues could be identified. Review the source notice before drafting.")
    for index, issue in enumerate(analysis.issues, 1):
        with st.container(border=True, key=f"issue_card_{index}"):
            render_issue_heading(index, issue.title)
            st.caption("Department's observation")
            st.text(issue.department_observation)
            if issue.amount:
                render_amount(issue.amount)
            if issue.action_requested:
                st.text(f"Action requested: {issue.action_requested}")
            with st.expander("View source excerpt"):
                st.text(issue.source_quote)

    left, right = st.columns(2)
    with left:
        st.subheader("Sections Mentioned")
        for section in analysis.sections_mentioned:
            render_section(section.text)
            with st.expander("Source wording"):
                st.text(section.source_quote)
        if not analysis.sections_mentioned:
            st.caption("No explicit section could be verified.")
    with right:
        st.subheader("Documents requested in notice")
        for index, document in enumerate(analysis.documents_requested):
            st.checkbox(escape_markdown(document.text), key=f"document_{index}", help=escape_markdown(document.source_quote))
        if not analysis.documents_requested:
            st.caption("No requested documents could be verified.")
        st.caption("This checklist tracks preparation only; it does not attach documents to your reply.")

    if analysis.uncertainties:
        with st.expander("Items to verify", expanded=True):
            for uncertainty in analysis.uncertainties:
                st.text(f"• {uncertainty}")
    ready = render_case_workflow()
    st.divider()
    st.markdown('<div class="section-eyebrow">From clarity to action</div>', unsafe_allow_html=True)
    st.subheader("7 · Review your reply")
    st.markdown('<div class="draft-intro">Professional first draft — review facts and attachments before filing.</div>', unsafe_allow_html=True)
    if not ready:
        st.info("Complete the available-document, research and strategy stages above. Existing draft edits remain below, if any.")
    if st.session_state.get("draft_reply") and (not ready or st.session_state.get("case_draft_signature") != record_signature()):
        st.warning("This draft predates changes to the case record. Rebuild the strategy and regenerate, or reconcile the changes manually before using it.")
    st.radio("Draft style", ["Concise", "Detailed", "Firm"], index=1, key="draft_style", horizontal=True)
    st.caption("Style applies when generating a draft. Regeneration replaces the editor; your prior version can be restored.")
    st.button("Regenerate Draft" if st.session_state.get("draft_reply") else "Generate Comprehensive Reply", on_click=regenerate, disabled=not ready, type="primary")
    for note in st.session_state.get("case_review_notes", []):
        st.warning(note)
    if st.session_state.get("previous_draft"):
        st.button("Restore previous draft", on_click=restore_draft)
    st.session_state.setdefault("draft_reply", "")
    reply = st.text_area("Edit your reply", key="draft_reply", height=520, placeholder="Your reviewed draft will appear after you prepare the strategy and generate the reply.")
    st.caption("Click outside the editor to save changes before copying or downloading. Changes are kept in this session.")
    if reply.strip():
        try:
            word = generate_docx(reply)
            st.download_button("Download Word Reply", data=word, file_name=safe_filename(analysis.assessment_year), mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")
        except AppError as exc:
            st.error(str(exc))
        if hasattr(st, "iframe"):
            st.iframe(clipboard_html(reply), height=55)
        else:
            components.html(clipboard_html(reply), height=55)
    st.caption(DISCLAIMER)
    with st.expander("Review extracted notice text"):
        st.text(st.session_state.get("notice_text", ""))
    st.button("Clear notice & start again", on_click=start_over)


def main() -> None:
    apply_styles()
    render_header(bool(st.session_state.get("analysis")))
    with st.container(border=True, key="upload_panel"):
        st.markdown('<div class="section-eyebrow">Start here</div><div class="upload-heading"><h2>Bring your notice. Find your next step.</h2><span>PDF · 20 MB max · 60 pages</span></div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload Tax Notice", type=["pdf"], key=f"upload_{st.session_state.get('uploader_generation', 0)}", on_change=clear_result, help="PDF only · up to 20 MB · up to 60 pages")
        col1, col2 = st.columns([1, 1])
        with col1:
            clicked = st.button("Retry decoding" if st.session_state.get("error") else "Decode Notice", type="primary", disabled=uploaded is None, use_container_width=True)
        with col2:
            st.button("Try Sample Notice", on_click=use_sample, use_container_width=True)
        st.caption(PRIVACY)
    if clicked and uploaded:
        process_upload(uploaded)
    if st.session_state.get("error"):
        st.error(st.session_state["error"])
        if st.session_state.get("notice_text"):
            st.caption("The extracted text is retained in this session so retrying does not repeat PDF reading.")
    if st.session_state.get("analysis"):
        render_results()
    else:
        st.markdown('<div class="outcome-hint">A clearer notice. A considered reply. <strong>You stay in control.</strong></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
