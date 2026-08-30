"""
AUD-LS-001 — Ledger Scrutiny: Missing Narration.

Audit area: Ledger Scrutiny. Relevant SA: SA 500.

SA Reference (authoritative — ICAI Standard on Auditing): SA 500 (Audit
Evidence) requires audit evidence sufficient to support the recorded
transaction — a ledger entry with no narration at all offers none. SA
500 does not itself define "narration" or mandate this specific check;
the screen below is FinSight's own.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA; adapted from a user-provided ledger-scrutiny prototype — see
`ledger_scrutiny_shared.py`'s module docstring): flags a GL/JE/BANK row
whose `description` field is blank or whitespace-only.

What data is required: GL/JE/BANK rows with a `description` field.
What can actually be established: whether a row's narration/description
is blank. What cannot be established: why it is blank, or whether the
entry is otherwise properly supported by a voucher/invoice on file —
only inspection of the underlying document can establish that.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome

RULE_ID = "AUD-LS-001"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 500"
ASSERTIONS = ("COMPLETENESS", "ACCURACY")
TOPIC = "Ledger Scrutiny — Missing Narration"


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
        description = (v.get("description") or "").strip()
        if description:
            continue

        account_name = v.get("account_name") or f"row {row.row_index + 1}"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=f'Entry on "{account_name}" has no narration/description recorded.',
            explanation=(
                f'An entry on "{account_name}" has no narration or description recorded at all. SA 500 '
                f"requires audit evidence sufficient to support a recorded transaction — a completely blank "
                f"narration offers the reviewer nothing to assess without going back to the underlying "
                f"voucher. This does not itself mean the entry is improper, only that its purpose cannot be "
                f"determined from the ledger data alone."
            ),
            suggested_query="Please obtain the narration/description and supporting documents for this entry.",
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "identification_method": "FinSight blank-narration check",
                "threshold_is_statutory": False,
            },
            amount_paise=row_amount(v) or None,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
