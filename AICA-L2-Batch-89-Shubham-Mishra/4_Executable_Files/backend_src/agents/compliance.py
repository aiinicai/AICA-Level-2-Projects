"""
Agent 3 — Compliance Checklist Agent (PROTECTED PRIORITY — the product's headline
feature). See prompts/compliance_agent.md for the prompt and design rationale.

perceive -> reason -> self_check -> act loop that checks a drafted document's text
against a mandatory-clause checklist for its document type, and reports exactly
what's missing.
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

# Mandatory clauses per document type, derived from the L1 app's own document
# generator templates (CA_PracticeOS_Compliance.html) plus the explicit example
# CLAUDE.md gives for engagement letters (scope, fees, responsibilities, limitations).
# Each clause also carries trigger keywords used by the self-check heuristic.
CHECKLISTS = {
    "Engagement Letter": [
        {
            "id": "scope",
            "name": "Objective and Scope",
            "description": "States the objective/scope of the engagement and the specific deliverable to be issued.",
            "keywords": ["scope", "objective", "deliverable"],
        },
        {
            "id": "responsibilities",
            "name": "Client and Firm Responsibilities",
            "description": "States both the client's responsibilities (records, information, personnel) and the firm's responsibilities (professional care, standards).",
            "keywords": ["responsib", "records", "professional care", "personnel"],
        },
        {
            "id": "fees",
            "name": "Fees",
            "description": "States the professional fee amount or the basis on which fees will be charged.",
            "keywords": ["fee", "fees", "remuneration", "₹", "rs.", "rs "],
        },
        {
            "id": "limitations",
            "name": "Limitations",
            "description": "States the inherent limitations of the engagement (e.g. does not guarantee detection of all misstatements, fraud, or errors).",
            "keywords": ["limitation", "inherent", "not guarantee", "does not detect"],
        },
        {
            "id": "acceptance",
            "name": "Acceptance / Signature",
            "description": "Provides for the client to sign and return the letter as acceptance of the engagement terms.",
            "keywords": ["accept", "sign", "signature", "acknowledg"],
        },
    ],
    "Net Worth Certificate": [
        {
            "id": "purpose",
            "name": "Purpose Stated",
            "description": "States the purpose for which the net worth certificate is being issued (e.g. bank loan, visa).",
            "keywords": ["purpose", "for the purpose of"],
        },
        {
            "id": "assets_liabilities",
            "name": "Assets, Liabilities and Net Worth Statement",
            "description": "Contains an itemized statement of assets and liabilities with a computed net worth figure.",
            "keywords": ["assets", "liabilit", "net worth"],
        },
        {
            "id": "representation",
            "name": "Client Representation",
            "description": "States that the client has represented the information/documents provided are complete and accurate.",
            "keywords": ["represent", "complete and accurate", "best of their knowledge"],
        },
        {
            "id": "udin",
            "name": "UDIN",
            "description": "Contains a UDIN (Unique Document Identification Number) field, even if left blank/pending.",
            "keywords": ["udin"],
        },
        {
            "id": "membership_no",
            "name": "Membership Number",
            "description": "Contains the signing CA's ICAI membership number field.",
            "keywords": ["membership no", "membership number"],
        },
    ],
    "General Certificate": [
        {
            "id": "addressee",
            "name": "Addressee",
            "description": "States who the certificate is addressed to (e.g. 'TO WHOMSOEVER IT MAY CONCERN' or a named addressee).",
            "keywords": ["whomsoever", "to,", "addressed"],
        },
        {
            "id": "basis",
            "name": "Particulars / Basis",
            "description": "States the factual basis, particulars, and source documents considered for the certificate.",
            "keywords": ["basis", "particular", "books", "records", "documents produced"],
        },
        {
            "id": "purpose",
            "name": "Purpose",
            "description": "States the purpose for which the certificate is issued.",
            "keywords": ["purpose", "submission"],
        },
        {
            "id": "udin",
            "name": "UDIN",
            "description": "Contains a UDIN field, even if left blank/pending.",
            "keywords": ["udin"],
        },
        {
            "id": "signature",
            "name": "Signature Block",
            "description": "Contains a firm/CA signature block with membership number.",
            "keywords": ["chartered accountant", "membership no", "signature"],
        },
    ],
    "Representation Letter": [
        {
            "id": "assignment_context",
            "name": "Assignment Context",
            "description": "States the engagement/assignment and period this representation letter relates to.",
            "keywords": ["engagement", "assignment", "period", "connection with"],
        },
        {
            "id": "responsibility_acknowledgement",
            "name": "Responsibility Acknowledgement",
            "description": "The client acknowledges responsibility for the completeness and accuracy of information supplied.",
            "keywords": ["responsib", "completeness and accuracy", "acknowledge"],
        },
        {
            "id": "representations",
            "name": "Representations",
            "description": "Contains the actual substantive representations/matters being confirmed.",
            "keywords": ["represent", "confirm"],
        },
        {
            "id": "signature",
            "name": "Signature and Date",
            "description": "Contains a signature block with name, designation, date and place.",
            "keywords": ["signature", "designation", "date", "place"],
        },
    ],
    "Working Paper": [
        {
            "id": "objective",
            "name": "Objective",
            "description": "States the objective of the working paper.",
            "keywords": ["objective"],
        },
        {
            "id": "procedures",
            "name": "Procedures Performed",
            "description": "Describes the procedures performed as part of the assignment.",
            "keywords": ["procedure"],
        },
        {
            "id": "evidence_exceptions",
            "name": "Evidence / Exceptions",
            "description": "Lists supporting evidence considered and any exceptions noted.",
            "keywords": ["evidence", "exception"],
        },
        {
            "id": "conclusion",
            "name": "Conclusion",
            "description": "States a conclusion reached from the work performed.",
            "keywords": ["conclusion"],
        },
        {
            "id": "prepared_reviewed",
            "name": "Prepared By / Reviewed By",
            "description": "Records who prepared and who reviewed the working paper, with dates.",
            "keywords": ["prepared by", "reviewed by"],
        },
    ],
    "Professional Fee Note": [
        {
            "id": "description",
            "name": "Service Description",
            "description": "Describes the professional service(s) being billed.",
            "keywords": ["description", "service"],
        },
        {
            "id": "amount",
            "name": "Fee Amount and Tax",
            "description": "States the professional fee amount and applicable GST/tax breakup.",
            "keywords": ["fee", "gst", "tax", "₹", "rs."],
        },
        {
            "id": "total",
            "name": "Total Invoice Value",
            "description": "States the total invoice value payable.",
            "keywords": ["total", "balance payable"],
        },
        {
            "id": "signature",
            "name": "Signature Block",
            "description": "Contains a firm signature block.",
            "keywords": ["chartered accountant", "signature", "for "],
        },
    ],
}

SYSTEM_PROMPT_TEMPLATE = """You are a compliance reviewer for an Indian chartered \
accountancy firm. You will be given the full text of a drafted {doc_type} and a list \
of mandatory clauses that this document type must contain. For EACH clause, decide \
whether the document's text satisfies it.

Mandatory clauses to check:
{clause_list}

Return ONLY a JSON array, one object per clause, in the same order given, with keys:
{{
  "id": string,
  "present": boolean,
  "evidence": string,
  "reason": string
}}

Be strict: a clause is only "present" if its substance is actually in the text, not \
merely implied. Do not be fooled by section headings alone — check the content \
under the heading actually satisfies the clause's description."""


def strip_html(text: str) -> str:
    if "<" not in text or ">" not in text:
        return text
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class ComplianceAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key or key == "your-anthropic-api-key-here":
            raise RuntimeError("ANTHROPIC_API_KEY is not configured in .env")
        self.client = anthropic.Anthropic(api_key=key)

    # ---- perceive -----------------------------------------------------------
    def perceive(self, text: str) -> str:
        return strip_html(text)

    def classify_document_type(self, text: str) -> str:
        upper = text.upper()
        title_map = {
            "ENGAGEMENT LETTER": "Engagement Letter",
            "NET WORTH CERTIFICATE": "Net Worth Certificate",
            "REPRESENTATION LETTER": "Representation Letter",
            "WORKING PAPER": "Working Paper",
            "PROFESSIONAL FEE NOTE": "Professional Fee Note",
            "FEE NOTE": "Professional Fee Note",
        }
        for marker, doc_type in title_map.items():
            if marker in upper:
                return doc_type
        # any other certificate-shaped document falls back to the general checklist
        if "CERTIFICATE" in upper:
            return "General Certificate"

        # last resort: ask the model to classify from the known list
        known_types = list(CHECKLISTS.keys())
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=30,
            messages=[{
                "role": "user",
                "content": (
                    f"Classify this document as exactly one of {known_types}. "
                    f"Reply with only the exact label.\n\n{text[:1500]}"
                ),
            }],
        )
        blocks = [b.text for b in response.content if b.type == "text"]
        guess = (blocks[0].strip() if blocks else "").strip('"')
        return guess if guess in CHECKLISTS else "General Certificate"

    # ---- reason ---------------------------------------------------------------
    def reason(self, text: str, doc_type: str) -> list[dict]:
        checklist = CHECKLISTS[doc_type]
        clause_list = "\n".join(
            f"{i+1}. id={c['id']} | {c['name']}: {c['description']}"
            for i, c in enumerate(checklist)
        )
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(doc_type=doc_type, clause_list=clause_list)
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Document text:\n\n{text}"}],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        if not text_blocks:
            raise RuntimeError(f"No text block in Claude response: {response.content}")
        raw = text_blocks[0].strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    # ---- self-check / validate -------------------------------------------
    def self_check(self, text: str, doc_type: str, verdicts: list[dict]) -> list[dict]:
        """Cross-checks each LLM verdict with a keyword heuristic. Deliberately
        asymmetric: only used to catch the LLM claiming a clause is present with
        zero textual basis (a strong, reliable signal of hallucination). It is
        NOT used to second-guess an "absent" verdict, because judging whether a
        clause's *substance* is missing (as opposed to a placeholder like
        "[To be filled]" under an on-topic heading) requires the same semantic
        judgment the keyword check can't make — heading words alone would
        otherwise make every blank template look "needs review" instead of
        cleanly absent."""
        checklist = {c["id"]: c for c in CHECKLISTS[doc_type]}
        text_lower = text.lower()
        checked = []
        for v in verdicts:
            clause = checklist.get(v["id"])
            keyword_hit = bool(clause) and any(kw in text_lower for kw in clause["keywords"])
            if v["present"]:
                status = "present" if keyword_hit else "needs_review"
            else:
                status = "absent"
            checked.append({**v, "name": clause["name"] if clause else v["id"], "status": status})
        return checked

    # ---- act / full loop --------------------------------------------------
    def run(self, text: str, doc_type: str | None = None) -> dict:
        clean_text = self.perceive(text)
        resolved_type = doc_type if doc_type in CHECKLISTS else self.classify_document_type(clean_text)
        verdicts = self.reason(clean_text, resolved_type)
        checked = self.self_check(clean_text, resolved_type, verdicts)

        missing = [c for c in checked if c["status"] == "absent"]
        needs_review = [c for c in checked if c["status"] == "needs_review"]
        overall = "PASS" if not missing and not needs_review else "FAIL"

        return {
            "document_type": resolved_type,
            "overall": overall,
            "items": checked,
            "missing": [c["name"] for c in missing],
            "needs_review": [c["name"] for c in needs_review],
        }


if __name__ == "__main__":
    import sys as _sys

    path = _sys.argv[1]
    doc_type_arg = _sys.argv[2] if len(_sys.argv) > 2 else None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    agent = ComplianceAgent()
    result = agent.run(content, doc_type_arg)
    print(json.dumps(result, indent=2))
