"""
Agent 2 — Document Drafting Agent.

perceive -> reason -> act loop that turns a one-line plain-English instruction
into a filled document draft, reusing the L1 app's document structure and
firm defaults from CA_PracticeOS_Compliance.html. See prompts/drafting_agent.md
for the prompt and design rationale (including why the Engagement Letter
template deliberately does not "fix" the L1 app's missing Limitations clause).
"""
import json
import os
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

MODEL = "claude-sonnet-5"

# Firm defaults, copied from CA_PracticeOS_Compliance.html state.settings
FIRM_NAME = "NSSJ & Co."
CA_NAME = "CA Shubham Mishra"
FOOTER = (
    "This document is prepared based on information and representations provided "
    "to us and should be read with the applicable engagement terms and "
    "professional requirements."
)

SYSTEM_PROMPT = """You are an intake assistant for an Indian chartered accountancy \
firm's document drafting workflow. You will be given one plain-English instruction \
line from a CA describing a document to draft. Extract structured parameters and \
return ONLY a JSON object with these exact keys — no prose, no markdown fences:

{
  "doc_type": string,
  "client_name": string,
  "fields": {
    "assignment_type": string,
    "period": string,
    "fees": string,
    "deliverable": string,
    "purpose": string,
    "service_description": string
  }
}

doc_type must be exactly one of: Engagement Letter, Net Worth Certificate, General \
Certificate, Representation Letter, Working Paper, Professional Fee Note. If the \
instruction does not clearly match one of them, pick the closest fit.

Only include a "fields" key if it is mentioned or reasonably inferable from the \
instruction (e.g. infer a sensible "deliverable" from "assignment_type" — a tax \
audit implies Form 3CA/3CB and 3CD). Do not fabricate a client name; if genuinely \
absent, use "[Client name not specified]". Do not fabricate specific figures (fees, \
dates) that were not stated or clearly implied."""


def format_inr(amount) -> str:
    if amount in (None, ""):
        return ""
    digits_only = re.sub(r"[^0-9.]", "", str(amount))
    if not digits_only:
        return ""
    try:
        n = int(round(float(digits_only)))
    except ValueError:
        return ""
    s = str(abs(n))
    if len(s) <= 3:
        formatted = s
    else:
        last3, rest = s[-3:], s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        formatted = ",".join(parts) + "," + last3
    sign = "-" if n < 0 else ""
    return f"{sign}₹{formatted}"


def _f(fields: dict, key: str, default: str = "") -> str:
    return (fields.get(key) or default).strip() if isinstance(fields.get(key), str) else default


def render_engagement_letter(client_name: str, fields: dict) -> str:
    assignment_type = _f(fields, "assignment_type", "the agreed assignment")
    period = _f(fields, "period", "the agreed period")
    deliverable = _f(fields, "deliverable", "[To be specified]")
    fees_raw = _f(fields, "fees")
    fees_display = format_inr(fees_raw) if fees_raw else "[To be agreed]"
    return f"""ENGAGEMENT LETTER

Client: {client_name}

Dear Sir / Madam,

We thank you for appointing {FIRM_NAME} to provide professional services in relation to {assignment_type} for {period}.

1. Objective and Scope
The objective of this engagement is to perform the services described above and issue the agreed deliverable, subject to the applicable professional standards, laws, regulations and engagement-specific requirements.
Deliverable: {deliverable}

2. Management / Client Responsibilities
The client is responsible for maintaining appropriate books, records and supporting documentation; providing complete, accurate and timely information; making relevant personnel available; and providing representations and confirmations where required.

3. Our Responsibilities
We will perform the agreed procedures and professional work with due professional care and in accordance with the applicable professional requirements relevant to the assignment. The nature and extent of work will depend on the agreed scope and information made available to us.

4. Access and Cooperation
The client shall provide reasonable access to records, documents, explanations and other information required for the engagement.

5. Fees
Professional fees: {fees_display}. Applicable taxes and agreed out-of-pocket expenses remain subject to the final terms agreed between the parties.

6. Confidentiality and Communication
Information obtained during the engagement will be handled in accordance with applicable professional obligations. Material matters arising during the engagement may be communicated to the client or those charged with governance, as appropriate.

7. Acceptance
Please sign and return a copy of this letter as acknowledgement of your understanding and acceptance of the engagement terms.

For {FIRM_NAME}
{CA_NAME}
Chartered Accountant

Accepted for and on behalf of the Client
Name / Designation:
Date:

{FOOTER}
"""


def render_net_worth_certificate(client_name: str, fields: dict) -> str:
    purpose = _f(fields, "purpose", "[purpose not specified]")
    return f"""NET WORTH CERTIFICATE

Certificate No.: NSSJ/NW/DRAFT
Date: [date]

Client: {client_name}

We have been requested by the above client to provide a statement of net worth as at [date] for the purpose of {purpose}.

Statement of Net Worth

Assets                     Basis / Evidence          Amount (Rs.)
[To be filled]             [To be filled]            [To be filled]

Liabilities                Basis / Evidence          Amount (Rs.)
[To be filled]             [To be filled]            [To be filled]

Net Worth: [To be computed once asset/liability figures are entered]

Management / Client Representation
The client has represented that the information and supporting documents provided for the above statement are complete and accurate to the best of their knowledge.

For {FIRM_NAME}
{CA_NAME}
Chartered Accountant

UDIN: ______________________
Membership No.: __________________
Place: ___________________________
Date: [date]

{FOOTER}
"""


def render_general_certificate(client_name: str, fields: dict) -> str:
    purpose = _f(fields, "purpose", "For submission to the concerned authority / institution.")
    return f"""GENERAL CERTIFICATE

Certificate No.: NSSJ/CERT/DRAFT
Date: [date]
Period / As at: [period]

Client: {client_name}

TO WHOMSOEVER IT MAY CONCERN

Based on the information, books, records and documents produced before us and the explanations provided by the client, we have considered the following particulars for the limited purpose stated below.

Particulars / Basis
[Enter factual basis, amount and supporting details]

Purpose
{purpose}

For {FIRM_NAME}
{CA_NAME}
Chartered Accountant

UDIN: ______________________
Membership No.: ________________
Place: _________________________
Date: [date]

{FOOTER}
"""


def render_representation_letter(client_name: str, fields: dict) -> str:
    assignment_type = _f(fields, "assignment_type", "the agreed assignment")
    period = _f(fields, "period", "the agreed period")
    return f"""MANAGEMENT / CLIENT REPRESENTATION LETTER

Date: [date]
Assignment: {assignment_type}
Period: {period}

Client: {client_name}

Dear Sir / Madam,

This representation is provided in connection with the above engagement. We acknowledge our responsibility for the completeness and accuracy of information supplied to you.

Representations
[Enter specific matters being represented/confirmed]

We confirm that, to the best of our knowledge and belief, the above representations are complete and accurate, except for matters specifically communicated to you.

For and on behalf of the Client
Name:
Designation:

Date: [date]
Place: __________________
Signature:
"""


def render_working_paper(client_name: str, fields: dict) -> str:
    assignment_type = _f(fields, "assignment_type", "the agreed assignment")
    return f"""WORKING PAPER

Reference: WP-DRAFT
Assignment: {assignment_type}
Date: [date]

Client: {client_name}

Objective
Document the work performed, evidence considered, exceptions and conclusion in relation to the assignment.

Procedures Performed
[Enter procedures performed]

Evidence / Exceptions
Supporting documents should be listed and cross-referenced here. Any unresolved exception must be clearly documented and evaluated before issue of the final deliverable.

Conclusion
[Enter conclusion]

Prepared By: [Name]        Reviewed By: [Name]
Date: [date]                Date: __________________

{FOOTER}
"""


def render_professional_fee_note(client_name: str, fields: dict) -> str:
    service = _f(fields, "service_description", "Professional Services")
    fees_raw = _f(fields, "fees")
    fees_val = format_inr(fees_raw) if fees_raw else "[To be agreed]"
    return f"""PROFESSIONAL FEE NOTE / INVOICE DRAFT

Reference: FEE-DRAFT
Date: [date]

Client: {client_name}

Description                              Amount (Rs.)
{service:<40}  {fees_val}
Professional Fees / Taxable Value        {fees_val}
GST (as applicable)                      [To be computed]
Total Invoice Value                      [To be computed]

Invoice tax treatment, GST registration details, place of supply, SAC, tax rate, reverse-charge applicability and other statutory particulars must be completed and verified by the firm before issue. This is a drafting utility, not a tax determination engine.

For {FIRM_NAME}
{CA_NAME}
Chartered Accountant

Client / Recipient
"""


TEMPLATES = {
    "Engagement Letter": render_engagement_letter,
    "Net Worth Certificate": render_net_worth_certificate,
    "General Certificate": render_general_certificate,
    "Representation Letter": render_representation_letter,
    "Working Paper": render_working_paper,
    "Professional Fee Note": render_professional_fee_note,
}


class DraftingAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key or key == "your-anthropic-api-key-here":
            raise RuntimeError("ANTHROPIC_API_KEY is not configured in .env")
        self.client = anthropic.Anthropic(api_key=key)

    # ---- perceive -----------------------------------------------------------
    def perceive(self, instruction: str) -> str:
        return instruction.strip()

    # ---- reason ---------------------------------------------------------------
    def reason(self, instruction: str) -> dict:
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": instruction}],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        if not text_blocks:
            raise RuntimeError(f"No text block in Claude response: {response.content}")
        raw = text_blocks[0].strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        if parsed.get("doc_type") not in TEMPLATES:
            parsed["doc_type"] = "General Certificate"
        parsed.setdefault("fields", {})
        parsed.setdefault("client_name", "[Client name not specified]")
        return parsed

    # ---- act ----------------------------------------------------------------
    def render(self, doc_type: str, client_name: str, fields: dict) -> str:
        return TEMPLATES[doc_type](client_name, fields)

    # ---- full loop --------------------------------------------------------
    def run(self, instruction: str) -> dict:
        perceived = self.perceive(instruction)
        extracted = self.reason(perceived)
        draft_text = self.render(extracted["doc_type"], extracted["client_name"], extracted["fields"])
        return {
            "instruction": instruction,
            "doc_type": extracted["doc_type"],
            "client_name": extracted["client_name"],
            "fields": extracted["fields"],
            "draft_text": draft_text,
        }


if __name__ == "__main__":
    agent = DraftingAgent()
    result = agent.run(sys.argv[1])
    print(json.dumps(result, indent=2))
