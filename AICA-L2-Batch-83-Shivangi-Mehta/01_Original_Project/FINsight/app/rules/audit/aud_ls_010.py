"""
AUD-LS-010 — Ledger Scrutiny: Risk Indicator Keywords.

Audit area: Ledger Scrutiny. Relevant SA: SA 240, SA 500.

SA Reference: SA 240 (fraud risk), SA 500 (Audit Evidence). Neither
standard prescribes the exact keyword list used below — it is
FinSight's own, disclosed word list (see `ledger_scrutiny_shared.py`).
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype): flags a GL/JE/BANK row whose account name or description
contains one of FinSight's own risk-indicator keywords (e.g. "personal",
"penalty", "donation", "cash", "loan", "advance", "director",
"relative", "gift", "fine", "adjustment", "reversal").

Limitation: this is a plain keyword match — it will miss any equivalent
term not on the list, and will flag entirely routine, properly-recorded
entries that happen to use one of these ordinary words (e.g. a
scheduled loan-instalment repayment). A match is a prompt to look
closer, never itself a finding of an improper transaction.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import RISK_KEYWORDS, collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-010"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 240, SA 500"
ASSERTIONS = ("OCCURRENCE", "CLASSIFICATION")
TOPIC = "Ledger Scrutiny — Risk Indicator Keywords"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = collect_ledger_rows(dataset)
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entry, or Bank Statement data is "
            "available for this engagement."
        )
        return outcome

    outcome.evaluated_count = len(ledger_rows)
    for row in ledger_rows:
        v = row.values
        account_name = (v.get("account_name") or "").strip()
        description = (v.get("description") or "").strip()
        haystack = f"{account_name} {description}".strip().lower()
        if not haystack:
            continue
        matched = [kw for kw in RISK_KEYWORDS if kw in haystack]
        if not matched:
            continue

        label_text = account_name or description or f"row {row.row_index + 1}"
        amount = row_amount(v)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=f'Entry on "{label_text}" matches FinSight risk-indicator keyword(s): {", ".join(matched)}.',
            explanation=(
                f'An entry on "{label_text}" contains the word(s) {", ".join(matched)} in its account name or '
                f"description, matched against FinSight's own risk-indicator word list. This is a keyword screen "
                f"only — the matched word(s) frequently appear in entirely ordinary, properly-recorded entries — "
                f"and flags the row for a closer look, not as a finding of an improper transaction."
            ),
            suggested_query="Please provide the business rationale and supporting documents for this entry.",
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "identification_method": "FinSight risk-indicator keyword check",
                "matched_keywords": matched,
                "threshold_is_statutory": False,
            },
            amount_paise=amount or None,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
