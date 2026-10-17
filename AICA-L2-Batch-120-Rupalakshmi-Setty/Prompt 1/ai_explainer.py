"""
Ledger Sentinel - AI Explanation Layer (Step 8 & 9)
Takes the risk-scored vouchers (output of rules_engine.py) and, for the
highest-risk entries, generates:
  1. A plain-language explanation an auditor could read in 10 seconds
  2. 2-3 follow-up questions to ask management
  3. A draft working-paper note ready to paste into the audit file

Design choice (Step 9 - privacy/governance):
  The rules engine does the DETECTING. This script only EXPLAINS entries
  that are already flagged - it never decides what counts as suspicious.
  That keeps the system auditable: every explanation can be traced back
  to the specific rule(s) that fired, not to an opaque model judgement.

Two modes:
  - LIVE AI mode: if ANTHROPIC_API_KEY is set in the environment, calls
    the Claude API to write natural-language explanations.
  - LOCAL/OFFLINE mode (default, no key needed): if LM_STUDIO_URL is set
    (e.g. http://localhost:1234/v1), calls a local model served by LM
    Studio instead - no data leaves the machine. This is the configuration
    described in the project plan for privacy/governance.
  - TEMPLATE fallback: if neither is configured, builds the explanation
    deterministically from the rule reasons already captured by the rules
    engine. This means the script always produces a complete working
    paper even with no AI wired up yet - useful for a first demo run.
"""

import os
import json
import pandas as pd

SCORED_PATH = "risk_scored_vouchers.xlsx"
OUT_PATH = "Auditor_Working_Paper.xlsx"
TOP_N = 50  # number of highest-risk entries to write up in full

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL")  # e.g. "http://localhost:1234/v1"


def call_claude_api(prompt: str) -> str:
    import anthropic  # pip install anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def call_local_lm_studio(prompt: str) -> str:
    import requests  # pip install requests
    resp = requests.post(
        f"{LM_STUDIO_URL}/chat/completions",
        json={
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _vendor_flag_line(row) -> str:
    """Rule 11 fires separately from risk_score (see ledger_sentinel_rules.py),
    so a voucher can be in this working paper ONLY because of a vendor-level
    structuring flag, with risk_score/reasons showing nothing unusual on their
    own. Build an extra line for that case so the explanation isn't misleading."""
    vflag = row.get("vendor_flag_score", 0)
    if pd.notna(vflag) and vflag > 0:
        return (f"\n- Rule 11 vendor structured-disbursement flag: {vflag}/100 - "
                 f"{row.get('vendor_flag_reason', '')}")
    return ""


def build_prompt(row) -> str:
    vendor_line = _vendor_flag_line(row)
    return f"""You are assisting an external auditor performing SA 240 journal-entry testing.
A rules engine has flagged the following journal entry as high risk. Based ONLY on the
information given, write:
1. A 2-3 sentence plain-language explanation of why this entry is risky.
2. Two specific follow-up questions to ask management or the preparer.
3. A one-paragraph working-paper note suitable for the audit file.

Entry details:
- Voucher ID: {row['voucher_id']}
- Date: {row['date']}
- Prepared by: {row['created_by_name']}
- Debit account: {row['debit_account']}
- Credit account: {row['credit_account']}
- Amount: {row['amount']:,.2f}
- Narration: {row['narration']}
- Risk score: {row['risk_score']}/100
- Red flags triggered: {row['reasons']}{vendor_line}

{"NOTE: this entry's risk score and red flags above may look unremarkable on their own - it is in this review because of the separate Rule 11 vendor flag above, which looks at this vendor's CUMULATIVE payments over time, not this single entry. Base your explanation on that pattern." if vendor_line else ""}

Respond in plain text with three clearly labelled sections: EXPLANATION, FOLLOW-UP QUESTIONS, WORKING PAPER NOTE.
Do not invent facts not given above."""


def template_fallback(row) -> dict:
    """Deterministic, rule-based explanation - used when no AI backend is configured."""
    reasons = row["reasons"]
    amt = row["amount"]
    vflag = row.get("vendor_flag_score", 0)
    is_vendor_only = pd.notna(vflag) and vflag > 0 and row["num_flags"] == 0

    if is_vendor_only:
        # This voucher is in the working paper ONLY because of Rule 11 - the
        # single-entry rules found nothing wrong with it in isolation, by
        # design (see ledger_sentinel_rules.py). Explain it on that basis
        # instead of the misleading "0 red flags" framing.
        vreason = row.get("vendor_flag_reason", "")
        explanation = (
            f"Voucher {row['voucher_id']} itself triggered none of the 10 single-entry red flags "
            f"(score {row['risk_score']}/100) - it is in this working paper because of Rule 11, the "
            f"vendor structured-disbursement screen (flag {vflag}/100): {vreason} The entry debits "
            f"{row['debit_account']} and credits {row['credit_account']} for AED {amt:,.2f}, prepared by "
            f"{row['created_by_name']}. The concern is the cumulative pattern of payments to this vendor "
            f"over time, not this entry in isolation - consistent with 'structuring' or 'smurfing', where "
            f"amounts are deliberately kept small and unremarkable to avoid single-entry detection."
        )
        questions = [
            f"Can management explain why payments to this vendor ledger have risen sharply relative to "
            f"its own earlier activity, and provide the underlying contracts/POs/invoices for every "
            f"payment in that window?",
            f"Is {row['created_by_name']} (or any other preparer on these vouchers) related to, or does "
            f"it have an undisclosed interest in, this vendor?",
        ]
        note = (
            f"Working Paper Note - Voucher {row['voucher_id']}: Selected for testing via the Ledger "
            f"Sentinel Rule 11 vendor structured-disbursement screen (flag {vflag}/100), NOT the "
            f"single-entry rules (score {row['risk_score']}/100, no flags on this entry alone). "
            f"Rule 11 basis: {vreason} Entry reviewed: debit {row['debit_account']} / credit "
            f"{row['credit_account']}, AED {amt:,.2f}, narration '{row['narration']}'. [Auditor to pull "
            f"and review the FULL set of payments to this vendor in the flagged window, not just this "
            f"entry, then document evidence obtained, conclusion reached, and sign-off here.]"
        )
        return {"explanation": explanation, "questions": questions, "note": note}

    vendor_note = f" Also separately flagged by Rule 11 (vendor structured-disbursement screen, {vflag}/100): {row.get('vendor_flag_reason', '')}" if pd.notna(vflag) and vflag > 0 else ""
    explanation = (
        f"Voucher {row['voucher_id']} was flagged with a risk score of {row['risk_score']}/100 "
        f"based on {row['num_flags']} red flag(s): {reasons}. The entry debits "
        f"{row['debit_account']} and credits {row['credit_account']} for AED {amt:,.2f}, "
        f"prepared by {row['created_by_name']}. Combined, these characteristics are "
        f"consistent with patterns auditors are directed to test under SA 240 journal-entry "
        f"procedures (unusual timing, round or threshold-driven amounts, weak segregation of "
        f"duties, or post-review alterations).{vendor_note}"
    )
    questions = [
        f"Can {row['created_by_name']} explain the business reason for posting this entry "
        f"on {row['date']}, and provide supporting documentation (PO, invoice, approval)?",
        "Was this entry reviewed and approved by someone other than the preparer, and if so, "
        "can that approval evidence be provided?",
    ]
    note = (
        f"Working Paper Note - Voucher {row['voucher_id']}: Selected for testing via the "
        f"Ledger Sentinel risk-scoring tool (score {row['risk_score']}/100; flags: {reasons})."
        f"{vendor_note} "
        f"Entry reviewed: debit {row['debit_account']} / credit {row['credit_account']}, "
        f"AED {amt:,.2f}, narration '{row['narration']}'. [Auditor to document evidence obtained, "
        f"conclusion reached, and sign-off here.]"
    )
    return {"explanation": explanation, "questions": questions, "note": note}


def parse_ai_response(text: str) -> dict:
    """Best-effort split of a free-text LLM reply into the three sections."""
    sections = {"EXPLANATION": "", "FOLLOW-UP QUESTIONS": "", "WORKING PAPER NOTE": ""}
    current = None
    for line in text.splitlines():
        stripped = line.strip().upper().rstrip(":")
        matched = next((k for k in sections if stripped == k), None)
        if matched:
            current = matched
            continue
        if current:
            sections[current] += line + "\n"
    return {
        "explanation": sections["EXPLANATION"].strip() or text.strip(),
        "questions": [q.strip("- ").strip() for q in sections["FOLLOW-UP QUESTIONS"].strip().splitlines() if q.strip()],
        "note": sections["WORKING PAPER NOTE"].strip(),
    }


def explain_entry(row) -> dict:
    prompt = build_prompt(row)
    try:
        if ANTHROPIC_API_KEY:
            return parse_ai_response(call_claude_api(prompt))
        if LM_STUDIO_URL:
            return parse_ai_response(call_local_lm_studio(prompt))
    except Exception as exc:  # network/model errors fall back gracefully
        print(f"  [warning] AI call failed for {row['voucher_id']} ({exc}); using template fallback")
    return template_fallback(row)


def main():
    scored = pd.read_excel(SCORED_PATH)

    # Working paper scope = top-N by risk_score (the 10 single-entry rules)
    # UNION any voucher Rule 11 flagged as part of the vendor structured-
    # disbursement screen. Rule 11 is deliberately NOT blended into
    # risk_score (see ledger_sentinel_rules.py / rules_engine.py), so a
    # structuring payment can sit far down the risk_score ranking even
    # while it is the single clearest fraud signal in the file. Without
    # this union, every Rule-11-only catch would silently disappear from
    # the auditor's working paper - the one document meant to list every
    # entry that needs a human look.
    top_n_ids = set(scored.head(TOP_N)["voucher_id"])
    vendor_flagged_ids = set(scored[scored["vendor_flag_score"] > 0]["voucher_id"])
    working_paper_ids = top_n_ids | vendor_flagged_ids
    top = scored[scored["voucher_id"].isin(working_paper_ids)].sort_values("rank").reset_index(drop=True).copy()

    mode = "LIVE Claude API" if ANTHROPIC_API_KEY else ("Local LM Studio" if LM_STUDIO_URL else "Template fallback (no AI configured)")
    print(f"Mode: {mode}")
    print(f"Explaining top {TOP_N} highest-risk vouchers "
          f"+ {len(vendor_flagged_ids - top_n_ids)} additional Rule 11 vendor-flagged voucher(s) "
          f"= {len(top)} total...")

    explanations, questions_col, notes = [], [], []
    for pos, (i, row) in enumerate(top.iterrows()):
        result = explain_entry(row)
        explanations.append(result["explanation"])
        questions_col.append(" | ".join(result["questions"]) if isinstance(result["questions"], list) else result["questions"])
        notes.append(result["note"])
        if (pos + 1) % 10 == 0:
            print(f"  ...{pos + 1}/{len(top)} done")

    top["ai_explanation"] = explanations
    top["follow_up_questions"] = questions_col
    top["working_paper_note"] = notes
    top["reviewed_by"] = ""
    top["review_date"] = ""
    top["auditor_conclusion"] = ""

    top.to_excel(OUT_PATH, index=False, engine="openpyxl")
    print(f"\nSaved: {OUT_PATH} ({len(top)} entries)")


if __name__ == "__main__":
    main()
