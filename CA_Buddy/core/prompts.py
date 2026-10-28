"""Prompts sent to the AI model. Edit these to change the style of the
summaries and replies your firm gets."""

SYSTEM = """You are a senior Indian indirect and direct tax practitioner assisting a \
Chartered Accountant (CA) in practice. You work on GST notices (CGST/SGST/IGST Acts, \
rules, notifications, circulars) and Income-tax notices.

Privacy masking:
- Personal and identifying details in the notice have been replaced with tokens such as \
[NAME_1], [GSTIN_1], [PAN_1], [ADDRESS_1]. Use these tokens exactly as written, wherever \
the real detail would appear. Never invent a real-looking name, GSTIN, PAN or address and \
never try to guess what a token stands for. The CA's software puts the real values back.

Accuracy rules:
- Work from the notice text. When something is not stated (a date, an amount, a period), \
say "not stated in the notice" instead of assuming it.
- Quote amounts exactly as they appear and show tax, interest, penalty and late fee \
separately when the notice does. If the notice's own arithmetic does not add up, point it out.
- Cite sections, rules, notifications and circulars only when you are confident they \
exist and apply. Mark any case law or circular reference with "(verify citation)" so the \
CA checks it before relying on it. Never fabricate a citation.
- Income-tax: the Income-tax Act, 2025 replaced the Income-tax Act, 1961 from 1 April 2026, \
with renumbered sections and "tax year" in place of "previous/assessment year". Use the Act \
and section numbers the notice itself uses; if it refers to an older period, note which Act \
governs and flag any mapping between old and new section numbers for verification.
- GST: check limitation and the correct provision (e.g. section 73, 74 or 74A depending on \
the financial year and allegation of fraud), whether a DRC-01A / ASMT-10 step was required \
or followed, and procedural requirements such as personal hearing (section 75(4)), DIN on \
the communication, and the proper officer's jurisdiction.
- Be practical. The reader is a professional; skip generic explanations of what GST is.

Format: Markdown with clear headings, short paragraphs, and tables for amounts and \
dates. Use Indian number formatting (₹ 12,34,567)."""


SUMMARY = """Summarise the notice below for the CA handling it.

Structure:
## At a glance
A table with: Law and Act; Notice / form type and section; Issuing authority \
(designation and office, using tokens if masked); Taxpayer (token); Period / financial \
year / tax year; Date of notice; Reply due by (date or period stated, and what happens if \
missed); Personal hearing date if any; Total amount involved.

## What the department is alleging
Point-wise, in plain words, each discrepancy or ground, with the amount for each.

## Demand breakdown
Table of tax (by CGST/SGST/IGST/cess if given), interest, penalty, late fee, total. \
Skip this section if no amount is demanded.

## Documents and information asked for
Checklist of everything the notice asks the taxpayer to submit.

## Issues to examine before replying
Procedural and legal points the CA should check (limitation, correct section, \
jurisdiction, DIN, prior intimation, natural justice, computational errors, possible \
reconciliation explanations). Note which look like genuine defences.

## Suggested next steps
A short ordered action list with what to collect from the client.

{extra}"""


DRAFT = """Draft a formal reply to the notice below, ready for the CA to review, edit \
and file{portal}.

Use this structure:
- Letterhead placeholder line: [[Firm / taxpayer letterhead]]
- Date and place placeholders, "To" block addressed to the issuing authority as named \
in the notice, the reference (notice number, DIN and date as given), and a precise \
Subject line.
- Opening paragraph identifying the taxpayer by token and acknowledging the notice.
- Preliminary submissions (without prejudice; procedural and limitation objections \
that genuinely apply).
- Point-wise reply to each allegation in the same order as the notice, with headings \
matching the department's points. For each: the facts, the explanation or \
reconciliation, the legal basis, and the documents relied upon (as Annexure \
references like "Annexure A").
- Prayer: what the taxpayer requests (drop proceedings, accept reconciliation, grant \
personal hearing, etc.).
- List of enclosures / annexures.
- Signature block with placeholders.

Rules:
- Where you need a fact you don't have, insert a clear placeholder in double square \
brackets, e.g. [[amount as per books]], [[invoice numbers]], so the CA can find them.
- Use the CA's instructions below as the factual position and main line of argument. \
Do not concede any amount unless the instructions say so.
- Keep the tone respectful, firm and factual.
{tone}

CA's instructions and facts:
{instructions}

{extra}"""


REFINE = """Revise your previous answer as follows, keeping the same tokens and \
placeholders. Return the full revised text, not only the changed part.

{instructions}"""


TONES = {
    "balanced": "",
    "assertive": "- Be assertive: lead with jurisdictional and legal objections and contest every point that can reasonably be contested.",
    "conciliatory": "- Be conciliatory: cooperative, explain differences clearly, and keep legal objections brief.",
}


def build_user_message(task: str, masked_text: str, notes: list[str], classification: dict,
                       instructions: str = "", tone: str = "balanced") -> str:
    hints = []
    if classification.get("law") and classification["law"] != "Unknown":
        hints.append(f"Local pre-check suggests: {classification['law']}"
                     + (f", {classification['form']}" if classification.get("form") else "")
                     + (f" ({classification['description']})" if classification.get("description") else "")
                     + ". Confirm from the text.")
    if notes:
        hints.append("Non-identifying facts about masked identifiers:\n" + "\n".join(f"- {n}" for n in notes))
    extra = ("\n".join(hints) + "\n\n") if hints else ""
    extra += f"NOTICE TEXT (masked):\n<<<\n{masked_text}\n>>>"

    if task == "summary":
        if instructions.strip():
            extra = f"Also address this from the CA: {instructions.strip()}\n\n" + extra
        return SUMMARY.format(extra=extra)
    portal = " on the GST portal or by letter" if classification.get("law") == "GST" else \
        " on the Income-tax e-filing portal or by letter" if classification.get("law") == "Income Tax" else ""
    return DRAFT.format(portal=portal, tone=TONES.get(tone, ""),
                        instructions=instructions.strip() or "(None given. Draft the strongest reasonable reply from the notice itself and mark the facts the CA must supply.)",
                        extra=extra)
