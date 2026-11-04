"""AuditSense Streamlit application.

Day 3 provides the user interface only. The LLM review layer is added next.
All included examples are fictional.
"""

from pathlib import Path
import json
from io import BytesIO

import pandas as pd
import streamlit as st

from src.reviewer import ELEMENTS, generate_ideal_issue, review_finding
from src.guardrails import find_sensitive_looking_content, validate_review_input


PROJECT_DIR = Path(__file__).parent
DATA_PATH = PROJECT_DIR / "data" / "synthetic_findings.csv"
REQUIRED_COLUMNS = {
    "id",
    "process",
    "title",
    "draft_observation",
    "evidence",
    "manual_status",
    "missing_elements",
    "unsupported_claims",
}


st.set_page_config(
    page_title="AuditSense",
    page_icon="🔎",
    layout="wide",
)


def load_findings() -> pd.DataFrame:
    """Load the fictional demonstration findings."""
    findings = pd.read_csv(DATA_PATH, keep_default_na=False)
    missing_columns = REQUIRED_COLUMNS.difference(findings.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required columns: {missing}")
    if findings.empty:
        raise ValueError("The synthetic dataset contains no findings.")
    if findings["id"].duplicated().any():
        raise ValueError("Synthetic finding IDs must be unique.")
    return findings


def finding_text(row: pd.Series) -> str:
    """Return the selected finding as editable text."""
    return clean_text(row["draft_observation"])


def clean_text(value: object, fallback: str = "") -> str:
    """Convert dataset values to safe display text without showing NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    return str(value)


MISSING_TEXT = "[Information missing in raw notes - Auditor to specify]"


def ideal_issue_as_text(issue: dict[str, str]) -> str:
    """Render the ideal issue in the requested 5-C report format."""
    return "\n\n".join(
        [
            f"Observation Title: {issue['observation_title']}",
            f"Risk Rating: {issue['risk_rating']}",
            f"Process Owner: {issue['process_owner']}",
            "Observation Summary\n" + issue["observation_summary"],
            "Criteria (What should be)\n" + issue["criteria"],
            "Condition (What is)\n" + issue["condition"],
            "Cause (Why it happened)\n" + issue["cause"],
            "Consequence / Impact (Why it matters)\n" + issue["consequence"],
            "Corrective Action / Recommendation\n" + issue["corrective_action"],
            "Risk rating basis (AI suggestion)\n" + issue["risk_rating_basis"],
            "Auditor verification note\n" + issue["auditor_verification_note"],
        ]
    )


def build_word_document(issue: dict[str, str]) -> bytes:
    """Create a DOCX export in memory."""
    from docx import Document

    document = Document()
    document.add_heading("AuditSense — Ideal Audit Issue", level=0)
    document.add_paragraph(
        "AI-generated advisory draft based only on fictional raw notes. "
        "Auditor verification and approval are required."
    )
    document.add_heading(issue["observation_title"], level=1)
    document.add_paragraph(f"Risk Rating: {issue['risk_rating']}")
    document.add_paragraph(f"Process Owner: {issue['process_owner']}")
    sections = [
        ("Observation Summary", "observation_summary"),
        ("Criteria (What should be)", "criteria"),
        ("Condition (What is)", "condition"),
        ("Cause (Why it happened)", "cause"),
        ("Consequence / Impact (Why it matters)", "consequence"),
        ("Corrective Action / Recommendation", "corrective_action"),
        ("Risk rating basis (AI suggestion)", "risk_rating_basis"),
        ("Auditor verification note", "auditor_verification_note"),
    ]
    for heading, key in sections:
        document.add_heading(heading, level=2)
        document.add_paragraph(issue[key])
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def build_pdf_document(issue: dict[str, str]) -> bytes:
    """Create a simple selectable-text PDF export in memory."""
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="AuditSense Ideal Audit Issue",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "AuditBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=10,
        leading=14, alignment=TA_LEFT, spaceAfter=8,
    )
    heading = ParagraphStyle(
        "AuditHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, spaceBefore=8, spaceAfter=4,
    )
    story = [
        Paragraph("AuditSense — Ideal Audit Issue", styles["Title"]),
        Paragraph(
            "AI-generated advisory draft based only on fictional raw notes. "
            "Auditor verification and approval are required.", body
        ),
        Paragraph(f"<b>Observation Title:</b> {issue['observation_title']}", body),
        Paragraph(f"<b>Risk Rating:</b> {issue['risk_rating']}", body),
        Paragraph(f"<b>Process Owner:</b> {issue['process_owner']}", body),
    ]
    sections = [
        ("Observation Summary", "observation_summary"),
        ("Criteria (What should be)", "criteria"),
        ("Condition (What is)", "condition"),
        ("Cause (Why it happened)", "cause"),
        ("Consequence / Impact (Why it matters)", "consequence"),
        ("Corrective Action / Recommendation", "corrective_action"),
        ("Risk rating basis (AI suggestion)", "risk_rating_basis"),
        ("Auditor verification note", "auditor_verification_note"),
    ]
    for heading_text, key in sections:
        story.extend([Paragraph(heading_text, heading), Paragraph(issue[key], body)])
    document.build(story)
    return output.getvalue()


st.title("🔎 AuditSense")
st.subheader("AI-assisted audit finding quality review")
st.info(
    "Demonstration only: all examples are fictional. AI suggestions will not "
    "replace audit evidence assessment or auditor judgment."
)

try:
    findings = load_findings()
except FileNotFoundError:
    st.error(f"Synthetic dataset not found at {DATA_PATH}")
    st.stop()
except (OSError, pd.errors.ParserError, ValueError) as error:
    st.error(f"Could not load the synthetic dataset: {error}")
    st.stop()


with st.sidebar:
    st.header("Demo controls")
    sample_ids = findings["id"].tolist()
    selected_id = st.selectbox("Load a fictional sample", sample_ids)
    selected_row = findings.loc[findings["id"] == selected_id].iloc[0]
    st.caption(
        "The sample data is for testing the application and must not be "
        "replaced with real bank or customer data."
    )


st.markdown("### 1. Finding details")
left, right = st.columns(2)

with left:
    title = st.text_input("Finding title", value=clean_text(selected_row["title"]))
    process = st.text_input("Business process", value=clean_text(selected_row["process"]))
    draft_observation = st.text_area(
        "Draft observation",
        value=finding_text(selected_row),
        height=180,
        max_chars=8000,
        help="Enter the draft finding that the reviewer should assess.",
    )

with right:
    evidence = st.text_area(
        "Available evidence",
        value=clean_text(selected_row["evidence"]),
        height=180,
        max_chars=8000,
        help="Enter only evidence available to the auditor.",
    )
    criteria = st.text_area(
        "Applicable criteria or control expectation (optional)",
        value="",
        height=100,
        max_chars=8000,
        help="Add the fictional policy or control expectation if known.",
    )


st.markdown("### 2. Review")
fictional_data_confirmed = st.checkbox(
    "I confirm that this input is fictional demonstration data and contains no customer, employee, or bank-confidential information.",
    value=False,
)
review_col, ideal_col = st.columns(2)
with review_col:
    review_clicked = st.button("Review finding", type="primary", use_container_width=True)
with ideal_col:
    ideal_issue_clicked = st.button("Generate ideal audit issue", use_container_width=True)

request_payload = {
    "title": title,
    "process": process,
    "draft_observation": draft_observation,
    "evidence": evidence,
    "criteria": criteria,
}

if review_clicked:
    st.session_state.pop("last_review", None)
    input_errors = validate_review_input(request_payload)
    suspicious_patterns = find_sensitive_looking_content(request_payload)
    if not fictional_data_confirmed:
        st.warning("Confirm that the input is fictional before requesting an AI review.")
    elif input_errors:
        for message in input_errors:
            st.error(message)
    elif suspicious_patterns:
        st.error("The review was blocked because the input looks potentially sensitive:")
        for message in suspicious_patterns:
            st.write(f"- {message}")
        st.info("Remove the sensitive-looking content and use fictional examples only.")
    else:
        st.session_state["last_input"] = request_payload
        with st.spinner("Reviewing the fictional finding..."):
            try:
                review = review_finding(st.session_state["last_input"])
            except Exception as error:  # Display a safe, user-readable message.
                st.error(str(error))
                review = None

        if review:
            st.session_state["last_review"] = review

if ideal_issue_clicked:
    st.session_state.pop("last_ideal_issue", None)
    input_errors = validate_review_input(request_payload)
    suspicious_patterns = find_sensitive_looking_content(request_payload)
    if not fictional_data_confirmed:
        st.warning("Confirm that the input is fictional before generating an ideal audit issue.")
    elif input_errors:
        for message in input_errors:
            st.error(message)
    elif suspicious_patterns:
        st.error("The ideal issue was blocked because the input looks potentially sensitive:")
        for message in suspicious_patterns:
            st.write(f"- {message}")
        st.info("Remove the sensitive-looking content and use fictional examples only.")
    else:
        with st.spinner("Drafting the fictional ideal audit issue..."):
            try:
                st.session_state["last_ideal_issue"] = generate_ideal_issue(request_payload)
            except Exception as error:
                st.error(str(error))


review = st.session_state.get("last_review")
if review:
    st.markdown("### 3. AI review result")
    st.caption(
        "AI suggestions are advisory. Verify every statement against evidence "
        "before using it in an audit document."
    )
    st.metric("Overall status", review["overall_status"].replace("_", " ").title())

    rows = []
    for element in ELEMENTS:
        item = review["element_analysis"][element]
        rows.append(
            {
                "Element": element.title(),
                "Status": item["status"].replace("_", " ").title(),
                "Explanation": item["explanation"],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Unsupported or verification-required claims**")
        if review["unsupported_claims"]:
            for claim in review["unsupported_claims"]:
                st.warning(claim)
        else:
            st.write("None flagged by the model.")

        st.markdown("**Questions for the auditor**")
        if review["questions_for_auditor"]:
            for question in review["questions_for_auditor"]:
                st.write(f"- {question}")
        else:
            st.write("No additional questions returned.")

    with col_b:
        st.markdown("**Suggested rewrite — verify before use**")
        st.write(review["suggested_rewrite"])
        st.info(review["human_review_note"])

    st.download_button(
        "Download review JSON",
        data=json.dumps(review, indent=2),
        file_name="auditsense_review.json",
        mime="application/json",
    )


ideal_issue = st.session_state.get("last_ideal_issue")
if ideal_issue:
    st.markdown("### 4. Ideal audit issue — 5 C's format")
    st.warning(
        "This is an AI-generated advisory draft. Verify every fact, cause, impact, "
        "risk rating, and recommendation against evidence before use."
    )
    st.markdown(f"**Observation Title:** {ideal_issue['observation_title']}")
    st.markdown(f"**Risk Rating:** {ideal_issue['risk_rating']} *(AI suggestion — verify)*")
    st.markdown(f"**Process Owner:** {ideal_issue['process_owner']}")
    st.markdown("**Observation Summary**")
    st.write(ideal_issue["observation_summary"])
    for heading_text, key in [
        ("Criteria (What should be)", "criteria"),
        ("Condition (What is)", "condition"),
        ("Cause (Why it happened)", "cause"),
        ("Consequence / Impact (Why it matters)", "consequence"),
        ("Corrective Action / Recommendation", "corrective_action"),
    ]:
        st.markdown(f"**{heading_text}**")
        st.write(ideal_issue[key])
    st.markdown("**Risk rating basis (AI suggestion)**")
    st.write(ideal_issue["risk_rating_basis"])
    st.markdown("**Auditor verification note**")
    st.write(ideal_issue["auditor_verification_note"])

    issue_text = ideal_issue_as_text(ideal_issue)
    export_col_a, export_col_b, export_col_c = st.columns(3)
    with export_col_a:
        st.download_button(
            "Download ideal issue TXT", data=issue_text,
            file_name="auditsense_ideal_audit_issue.txt", mime="text/plain",
        )
    with export_col_b:
        st.download_button(
            "Download ideal issue Word", data=build_word_document(ideal_issue),
            file_name="auditsense_ideal_audit_issue.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with export_col_c:
        st.download_button(
            "Download ideal issue PDF", data=build_pdf_document(ideal_issue),
            file_name="auditsense_ideal_audit_issue.pdf", mime="application/pdf",
        )


st.markdown("### 5. Human review boundary")
st.warning(
    "The auditor remains responsible for verifying evidence, assessing materiality "
    "and risk, deciding whether the finding is valid, and approving final wording."
)
st.caption(
    "AuditSense does not store or transmit input until you confirm the data is fictional "
    "and press Review finding."
)


with st.expander("View selected sample's evaluation label"):
    st.write("Reference status:", clean_text(selected_row["manual_status"]))
    st.write(
        "Deliberate weaknesses:",
        clean_text(selected_row["missing_elements"], fallback="None"),
    )
    st.write(
        "Reference unsupported claims:",
        clean_text(selected_row["unsupported_claims"], fallback="None"),
    )
