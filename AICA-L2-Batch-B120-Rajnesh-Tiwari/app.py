"""AuditSense Streamlit application.

Day 3 provides the user interface only. The LLM review layer is added next.
All included examples are fictional.
"""

from pathlib import Path
import json

import pandas as pd
import streamlit as st

from src.reviewer import ELEMENTS, review_finding
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
review_clicked = st.button("Review finding", type="primary", use_container_width=True)

if review_clicked:
    st.session_state.pop("last_review", None)
    request_payload = {
        "title": title,
        "process": process,
        "draft_observation": draft_observation,
        "evidence": evidence,
        "criteria": criteria,
    }
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


st.markdown("### 4. Human review boundary")
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
