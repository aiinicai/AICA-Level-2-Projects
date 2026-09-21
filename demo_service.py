"""An explicitly fictional, offline demonstration using the production models."""
from datetime import date
from services.models import Analysis, Deadline, Evidence, Issue

SAMPLE_TEXT = """DEMO NOTICE — FICTIONAL TRAINING EXAMPLE — NOT AN OFFICIAL NOTICE
Income Tax Department
Taxpayer: Example Demonstration Taxpayer (fictional)
Reference: DEMO-NOTICE-001
Notice dated 12 September 2026
Notice under Section 142(1) of the Income-tax Act, 1961
Assessment Year: 2025-26
Financial Year: 2024-25

1. Interest income reconciliation
Interest reported in the information statement is Rs. 2,48,600. The return shows
Rs. 2,10,000. Please explain and reconcile the difference of Rs. 38,600.
Provide bank statements, interest certificates and a reconciliation statement.

2. Deduction verification
Please provide documentary support for the deduction of Rs. 50,000 claimed
in the return, together with the computation of income.

Submit your response online by 27 September 2026.
This example contains no PAN, Aadhaar, GSTIN or real taxpayer information.
"""


def sample_analysis() -> Analysis:
    return Analysis(
        is_tax_notice=True, notice_type="Notice under Section 142(1)", department="Income Tax Department",
        notice_date="12 September 2026", assessment_year="2025-26", financial_year="2024-25",
        sections_mentioned=[Evidence(text="Section 142(1)", source_quote="Notice under Section 142(1) of the Income-tax Act, 1961")],
        response_deadline=Deadline(exact_date=date(2026, 9, 27), deadline_text="Submit your response online by 27 September 2026.", confidence="high", source_quote="Submit your response online by 27 September 2026."),
        issues=[
            Issue(title="Interest income reconciliation", department_observation="The information statement reports Rs. 2,48,600 in interest; the return shows Rs. 2,10,000.", amount="Rs. 38,600", action_requested="Explain and reconcile the difference.", source_quote="Interest reported in the information statement is Rs. 2,48,600. The return shows\nRs. 2,10,000. Please explain and reconcile the difference of Rs. 38,600."),
            Issue(title="Deduction verification", department_observation="Documentary support is requested for the deduction claimed in the return.", amount="Rs. 50,000", action_requested="Provide supporting documents and the computation of income.", source_quote="Please provide documentary support for the deduction of Rs. 50,000 claimed\nin the return, together with the computation of income."),
        ],
        documents_requested=[
            Evidence(text=name, source_quote="Provide bank statements, interest certificates and a reconciliation statement.")
            for name in ["Bank statements", "Interest certificates", "Reconciliation statement"]
        ] + [Evidence(text="Deduction supporting documents and computation of income", source_quote="Please provide documentary support for the deduction of Rs. 50,000 claimed\nin the return, together with the computation of income.")],
        executive_summary=[
            "Reconcile the Rs. 38,600 difference in reported interest income.",
            "Prepare bank statements, interest certificates and a reconciliation statement.",
            "Support the Rs. 50,000 deduction and provide the computation of income.",
            "Submit a response online by 27 September 2026.",
        ],
        uncertainties=["The taxpayer's factual explanations and supporting evidence have not been supplied."],
    )


def sample_draft(style: str = "Detailed") -> str:
    """Offline templates are labelled in the UI; they never masquerade as API output."""
    explanation = {
        "Concise": "[Insert factual explanation and verify supporting records before filing.]",
        "Detailed": "[Reconcile each item to the books and certificates, explain the difference, and confirm the amount to be reported. Attach the verified reconciliation before filing.]",
        "Firm": "We respectfully request that the issue be considered on the basis of the factual reconciliation to be provided. [Insert verified explanation and supporting records before filing.]",
    }[style]
    return f"""To
The Assessing Officer
Income Tax Department

Subject: Response to Notice under Section 142(1) for AY 2025-26 — DEMO

Respected Sir/Madam,

With reference to the notice dated 12 September 2026, reference DEMO-NOTICE-001, the following issue-wise response is submitted for your consideration.

1. Interest income reconciliation
The notice refers to interest of Rs. 2,48,600 in the information statement and Rs. 2,10,000 in the return, with a difference of Rs. 38,600.
{explanation}
[Confirm amount as per books. Attach verified bank statements and interest certificates before filing.]

2. Deduction verification
The notice requests support for the deduction of Rs. 50,000 claimed in the return.
[Insert the nature of the deduction and the verified factual explanation. Confirm eligibility and attach supporting records and computation of income before filing.]

We request that the verified explanations and documents supplied with the final response be considered on their merits.

Yours faithfully,
For [Assessee / Firm Name]
[Name of authorised representative]
Authorized Representative
[Date]
"""
