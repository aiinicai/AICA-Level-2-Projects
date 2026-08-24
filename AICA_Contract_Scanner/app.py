import os
import json

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("GEMINI_API_KEY was not found in your .env file.")
    st.stop()

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.6-flash"

st.set_page_config(
    page_title="AI Contract Risk Scanner",
    page_icon="🛡️",
    layout="wide"
)


# ============================================================
# DOCUMENT EXTRACTION
# ============================================================

def extract_pdf(file):
    reader = PdfReader(file)

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append(
            f"\n--- PAGE {page_number} ---\n{text}"
        )

    return "\n".join(pages)


def extract_docx(file):
    document = Document(file)

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)


def extract_text(file):
    filename = file.name.lower()

    if filename.endswith(".pdf"):
        return extract_pdf(file)

    elif filename.endswith(".docx"):
        return extract_docx(file)

    else:
        raise ValueError(
            "Unsupported file format. Please upload PDF or DOCX."
        )


# ============================================================
# GEMINI STRUCTURED OUTPUT SCHEMA
# ============================================================

RISK_SCHEMA = {
    "type": "object",
    "properties": {

        "executive_summary": {
            "type": "string"
        },

        "contract_facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string"
                    },
                    "value": {
                        "type": "string"
                    },
                    "evidence": {
                        "type": "string"
                    },
                    "page": {
                        "type": "string"
                    }
                },
                "required": [
                    "item",
                    "value",
                    "evidence",
                    "page"
                ]
            }
        },

        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {

                    "category": {
                        "type": "string"
                    },

                    "finding_type": {
                        "type": "string",
                        "enum": [
                            "Identified Provision",
                            "Potential Missing Protection",
                            "Not Determinable"
                        ]
                    },

                    "severity": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low",
                            "Informational"
                        ]
                    },

                    "clause": {
                        "type": "string"
                    },

                    "page": {
                        "type": "string"
                    },

                    "evidence": {
                        "type": "string"
                    },

                    "contract_fact": {
                        "type": "string"
                    },

                    "commercial_interpretation": {
                        "type": "string"
                    },

                    "financial_impact": {
                        "type": "string"
                    },

                    "recommendation": {
                        "type": "string"
                    },

                    "confidence": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low"
                        ]
                    }
                },

                "required": [
                    "category",
                    "finding_type",
                    "severity",
                    "clause",
                    "page",
                    "evidence",
                    "contract_fact",
                    "commercial_interpretation",
                    "financial_impact",
                    "recommendation",
                    "confidence"
                ]
            }
        }
    },

    "required": [
        "executive_summary",
        "contract_facts",
        "risks"
    ]
}


# ============================================================
# CONTRACT ANALYSIS
# ============================================================

def analyse_contract(contract_text):

    prompt = f"""
You are a senior Chartered Accountant and commercial
financial-risk analyst.

Analyse this commercial contract from a BUSINESS,
FINANCIAL and OPERATIONAL risk perspective.

You are NOT providing legal advice.

Do not determine whether a provision is legal, illegal,
valid, invalid, enforceable or unenforceable.

============================================================
CORE PRINCIPLE
============================================================

Follow:

EVIDENCE
→ CONTRACT FACT
→ COMMERCIAL INTERPRETATION
→ FINANCIAL / BUSINESS IMPACT
→ SEVERITY
→ RECOMMENDATION

Never jump directly from an interpretation to a High risk.

============================================================
NO HALLUCINATION
============================================================

Use ONLY the contract text provided.

Do not invent:

- clauses
- amounts
- dates
- parties
- obligations
- payment terms
- liabilities
- risks

If something cannot be determined, use:

"Not determinable from the available contract text."

============================================================
FINDING TYPES
============================================================

Use exactly one:

1. Identified Provision

The contract actually contains the provision.

2. Potential Missing Protection

A commercially important protection does not appear in
the available contract text.

IMPORTANT:
A missing protection is NOT automatically a High risk.

3. Not Determinable

There is insufficient evidence to reach a reliable conclusion.

============================================================
RISK AREAS
============================================================

Review:

- Payment terms
- Payment delays
- Credit exposure
- Cash-flow exposure
- Termination
- Termination payments
- Auto-renewal
- Liability caps
- Liability exposure
- Indemnities
- Penalties
- Liquidated damages
- Service credits
- Exclusivity
- Price escalation
- Fixed-price commitments
- Currency / FX exposure
- Performance obligations
- Service levels
- Operational dependencies
- Asymmetric obligations
- Unusual obligations
- Additional cost exposure
- Material commercial dependencies
- Other financially significant provisions

============================================================
SEVERITY
============================================================

HIGH:
Strong evidence of material financial, cash-flow,
liability, penalty, termination or operational exposure.

MEDIUM:
Meaningful commercial exposure but more limited or conditional.

LOW:
Minor commercial concern.

INFORMATIONAL:
Useful observation without material risk.

Do not inflate severity.

============================================================
EVIDENCE
============================================================

For every risk provide:

- Clause / Section
- Page
- Evidence
- Contract Fact

Evidence must come from the contract.

Do not fabricate quotations.

============================================================
FINANCIAL IMPACT
============================================================

Explain potential consequences such as:

- delayed cash collection
- working-capital pressure
- additional cost
- penalty exposure
- liability exposure
- FX exposure
- revenue uncertainty
- margin pressure
- termination cost
- resource commitment

Do not invent monetary amounts.

============================================================
RECOMMENDATION
============================================================

Provide practical management recommendations such as:

- negotiate shorter payment terms
- introduce payment milestones
- clarify responsibility for delayed inputs
- introduce liability protection
- review renewal notice periods
- introduce price escalation
- clarify FX treatment

Do not provide legal advice.

============================================================
CONTRACT
============================================================

{contract_text}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RISK_SCHEMA
        )
    )

    return json.loads(response.text)


# ============================================================
# VALIDATION
# ============================================================

def validate_risks(data):

    risks = data.get("risks", [])

    allowed_severities = {
        "High",
        "Medium",
        "Low",
        "Informational"
    }

    allowed_finding_types = {
        "Identified Provision",
        "Potential Missing Protection",
        "Not Determinable"
    }

    for risk in risks:

        severity = risk.get(
            "severity",
            "Informational"
        )

        finding_type = risk.get(
            "finding_type",
            "Not Determinable"
        )

        evidence = risk.get(
            "evidence",
            ""
        ).strip()

        if severity not in allowed_severities:
            risk["severity"] = "Informational"

        if finding_type not in allowed_finding_types:
            risk["finding_type"] = "Not Determinable"

        evidence_lower = evidence.lower()

        if (
            not evidence
            or "not determinable" in evidence_lower
            or "not identified" in evidence_lower
            or "no evidence" in evidence_lower
        ):

            if risk["finding_type"] == "Not Determinable":
                risk["severity"] = "Informational"

            elif (
                risk["finding_type"]
                == "Potential Missing Protection"
            ):
                if risk["severity"] == "High":
                    risk["severity"] = "Medium"

    return data


# ============================================================
# DISPLAY HELPERS
# ============================================================

def severity_icon(severity):

    icons = {
        "High": "🔴",
        "Medium": "🟠",
        "Low": "🟢",
        "Informational": "🔵"
    }

    return icons.get(
        severity,
        "🔵"
    )


def display_risk(risk, number):

    severity = risk.get(
        "severity",
        "Informational"
    )

    icon = severity_icon(severity)

    st.markdown(
        f"## {icon} Risk {number}: "
        f"{risk.get('category', 'Commercial Risk')}"
    )

    # Use two columns only.
    # Finding Type is displayed separately so that
    # "Potential Missing Protection" is not truncated.

    col1, col2 = st.columns(2)

    col1.metric(
        "Severity",
        severity
    )

    col2.metric(
        "Confidence",
        risk.get(
            "confidence",
            "Low"
        )
    )

    st.markdown(
        f"**Finding Type:** "
        f"{risk.get('finding_type', 'Not Determinable')}"
    )

    st.markdown(
        f"**Clause / Section:** "
        f"{risk.get('clause', 'Not identified')}"
    )

    st.markdown(
        f"**Page:** "
        f"{risk.get('page', 'Not determinable')}"
    )

    with st.expander(
        "📌 Evidence",
        expanded=True
    ):

        st.write(
            risk.get(
                "evidence",
                "Not determinable from the available contract text."
            )
        )

    st.markdown(
        "**Contract Fact**"
    )

    st.write(
        risk.get(
            "contract_fact",
            "Not determinable from the available contract text."
        )
    )

    st.markdown(
        "**Commercial Interpretation**"
    )

    st.write(
        risk.get(
            "commercial_interpretation",
            "Not determinable from the available contract text."
        )
    )

    st.markdown(
        "**Potential Financial / Business Impact**"
    )

    st.write(
        risk.get(
            "financial_impact",
            "Not determinable from the available contract text."
        )
    )

    st.markdown(
        "**Management Recommendation**"
    )

    st.write(
        risk.get(
            "recommendation",
            "No specific recommendation available."
        )
    )

    st.divider()


# ============================================================
# MANAGEMENT Q&A
# ============================================================

def answer_question(question, contract_text, result):

    risk_summary = json.dumps(
        result,
        indent=2,
        ensure_ascii=False
    )

    prompt = f"""
You are the commercial and financial risk assistant
for a Chartered Accountant.

Answer the user's question about the uploaded contract.

IMPORTANT:

Use ONLY:

1. The contract text
2. The structured risk analysis generated from that contract

Do not invent information.

Do not provide legal advice.

If the answer cannot be established from the available
contract text, say:

"Not determinable from the available contract text."

Every answer should distinguish between:

FACT
What the contract actually says.

INTERPRETATION
What it means commercially.

IMPACT
Potential financial or business consequence.

ACTION
What management may consider doing.

Keep the answer concise and management-focused.

USER QUESTION:

{question}

==================================================
STRUCTURED RISK ANALYSIS
==================================================

{risk_summary}

==================================================
CONTRACT TEXT
==================================================

{contract_text}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# ============================================================
# MAIN APPLICATION
# ============================================================

st.title(
    "🛡️ AI Contract Risk Scanner"
)

st.write(
    "Business & Financial Risk Analysis for Commercial Contracts"
)

st.info(
    "This application analyses contracts from a business "
    "and financial risk perspective. It does not provide "
    "legal advice."
)

st.divider()


# ============================================================
# UPLOAD
# ============================================================

st.subheader(
    "📄 Upload Contract"
)

uploaded_file = st.file_uploader(
    "Upload a commercial contract",
    type=["pdf", "docx"]
)


# ============================================================
# PROCESS CONTRACT
# ============================================================

if uploaded_file:

    st.success(
        f"Uploaded: {uploaded_file.name}"
    )

    try:

        with st.spinner(
            "Extracting contract text..."
        ):

            contract_text = extract_text(
                uploaded_file
            )

    except Exception as e:

        st.error(
            f"Document extraction failed: {str(e)}"
        )

        st.stop()

    if not contract_text.strip():

        st.error(
            "No readable text was extracted."
        )

        st.warning(
            "This may be a scanned/image-based PDF. "
            "OCR can be added later if required."
        )

        st.stop()

    word_count = len(
        contract_text.split()
    )

    st.success(
        f"Contract extracted successfully — "
        f"{word_count:,} words"
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Words Extracted",
        f"{word_count:,}"
    )

    col2.metric(
        "Characters Extracted",
        f"{len(contract_text):,}"
    )

    st.divider()


    # ========================================================
    # SCAN BUTTON
    # ========================================================

    if st.button(
        "🔍 Scan Contract for Commercial Risks",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "Analysing contractual risks..."
        ):

            try:

                result = analyse_contract(
                    contract_text
                )

                result = validate_risks(
                    result
                )

                st.session_state["result"] = result
                st.session_state["contract_text"] = contract_text

            except Exception as e:

                st.error(
                    f"Contract analysis failed: {str(e)}"
                )

                st.stop()


# ============================================================
# RISK DASHBOARD
# ============================================================

if "result" in st.session_state:

    result = st.session_state["result"]

    st.divider()

    st.header(
        "📊 Contract Risk Dashboard"
    )

    # --------------------------------------------------------
    # Executive Summary
    # --------------------------------------------------------

    st.subheader(
        "Executive Summary"
    )

    st.write(
        result.get(
            "executive_summary",
            "No executive summary available."
        )
    )

    # --------------------------------------------------------
    # Risk Counts
    # --------------------------------------------------------

    risks = result.get(
        "risks",
        []
    )

    high_count = sum(
        1 for r in risks
        if r.get("severity") == "High"
    )

    medium_count = sum(
        1 for r in risks
        if r.get("severity") == "Medium"
    )

    low_count = sum(
        1 for r in risks
        if r.get("severity") == "Low"
    )

    info_count = sum(
        1 for r in risks
        if r.get("severity") == "Informational"
    )

    st.subheader(
        "Risk Overview"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🔴 High",
        high_count
    )

    c2.metric(
        "🟠 Medium",
        medium_count
    )

    c3.metric(
        "🟢 Low",
        low_count
    )

    c4.metric(
        "🔵 Informational",
        info_count
    )

    st.divider()

    # --------------------------------------------------------
    # Priority Issues
    # --------------------------------------------------------

    st.subheader(
        "🚨 Priority Management Issues"
    )

    high_risks = [
        r for r in risks
        if r.get("severity") == "High"
    ]

    if high_risks:

        for risk in high_risks:

            st.error(
                f"{risk.get('category', 'Risk')} — "
                f"{risk.get('clause', 'Clause not identified')}"
            )

    else:

        st.success(
            "No High severity risks were identified "
            "from the available contract text."
        )

    st.divider()

    # --------------------------------------------------------
    # Detailed Risks
    # --------------------------------------------------------

    st.header(
        "Detailed Risk Findings"
    )

    if not risks:

        st.info(
            "No material commercial risk findings were returned."
        )

    else:

        for index, risk in enumerate(
            risks,
            start=1
        ):

            display_risk(
                risk,
                index
            )

    # --------------------------------------------------------
    # Contract Facts
    # --------------------------------------------------------

    st.header(
        "📋 Contract Facts"
    )

    facts = result.get(
        "contract_facts",
        []
    )

    if facts:

        for fact in facts:

            with st.expander(
                fact.get(
                    "item",
                    "Contract Fact"
                )
            ):

                st.write(
                    f"**Value:** "
                    f"{fact.get('value', '')}"
                )

                st.write(
                    f"**Evidence:** "
                    f"{fact.get('evidence', '')}"
                )

                st.write(
                    f"**Page:** "
                    f"{fact.get('page', '')}"
                )

    else:

        st.info(
            "No structured contract facts were returned."
        )

    # ========================================================
    # MANAGEMENT Q&A
    # ========================================================

    st.divider()

    st.header(
        "💬 Ask About This Contract"
    )

    st.write(
        "Ask a business or financial question about "
        "the uploaded contract."
    )

    question = st.text_input(
        "Your question",
        placeholder=(
            "Example: What could cost us money?"
        )
    )

    if st.button(
    "Get Answer",
    type="secondary"
    ):

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "Analysing your question..."
            ):

                try:

                    answer = answer_question(
                        question,
                        st.session_state["contract_text"],
                        st.session_state["result"]
                    )

                    st.session_state[
                        "qa_answer"
                    ] = answer

                except Exception as e:

                    st.error(
                        f"Unable to answer the question: {str(e)}"
                    )

    if "qa_answer" in st.session_state:

        st.subheader(
            "Answer"
        )

        st.markdown(
            st.session_state["qa_answer"]
        )


# ============================================================
# EXTRACTED CONTRACT
# ============================================================

if uploaded_file:

    st.divider()

    with st.expander(
        "🔎 View Extracted Contract Text"
    ):

        st.text_area(
            "Extracted Contract",
            contract_text,
            height=500
        )


# ============================================================
# DISCLAIMER
# ============================================================

st.divider()

st.caption(
    "AI Contract Risk Scanner is a business and financial "
    "risk analysis assistant. It does not provide legal advice "
    "and should not replace professional legal review."
)