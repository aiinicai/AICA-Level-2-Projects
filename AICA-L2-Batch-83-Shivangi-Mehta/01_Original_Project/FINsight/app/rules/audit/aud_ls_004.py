"""
AUD-LS-004 — Ledger Scrutiny: Zero, Negative, or Dual-Sided Amount.

Audit area: Ledger Scrutiny. Relevant SA: SA 500.

SA Reference: SA 500 (Audit Evidence) — a ledger row is expected to
carry exactly one, positive, non-zero amount on either its Debit or
Credit side; a row that fails that basic shape is a data-integrity
concern worth a look before any other analysis is placed on top of it.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA; adapted from a user-provided ledger-scrutiny prototype — see
`ledger_scrutiny_shared.py`): flags a GL/JE/BANK row where both Debit
and Credit are zero/blank, where either side is negative, or where both
Debit and Credit are populated (non-zero) on the same row at once.

Limitation: this is a structural/data-entry screen only — it cannot
distinguish a genuine data-entry error from an unusual but valid
posting convention used by a particular accounting system's export.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import collect_ledger_rows
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-004"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 500"
ASSERTIONS = ("ACCURACY", "EXISTENCE")
TOPIC = "Ledger Scrutiny — Zero, Negative, or Dual-Sided Amount"

_ISSUE_TEXT = {
    "negative": "carries a negative amount on the Debit and/or Credit side",
    "zero": "has no amount recorded on either the Debit or Credit side",
    "both": "has both a Debit and a Credit amount populated on the same row",
}
_ISSUE_RISK = {"negative": "MEDIUM", "zero": "LOW", "both": "MEDIUM"}


def _classify(debit: int, credit: int) -> str | None:
    if debit < 0 or credit < 0:
        return "negative"
    if debit == 0 and credit == 0:
        return "zero"
    if debit != 0 and credit != 0:
        return "both"
    return None


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
        debit = v.get("debit_amount") or 0
        credit = v.get("credit_amount") or 0
        issue = _classify(debit, credit)
        if issue is None:
            continue

        account_name = v.get("account_name") or v.get("party_name") or f"row {row.row_index + 1}"
        amount = debit + credit
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=f'Entry on "{account_name}" {_ISSUE_TEXT[issue]}.',
            explanation=(
                f'An entry on "{account_name}" {_ISSUE_TEXT[issue]}. This is a structural data-entry screen, '
                f"flagging the row's shape for review — it does not itself establish that the entry is wrong, "
                f"only that it departs from the normal single-sided, positive-amount posting pattern."
            ),
            suggested_query="Please confirm this entry was posted correctly and provide the supporting voucher.",
            risk_level=_ISSUE_RISK[issue],
            data_sources=[str(row.file_id)],
            threshold_used={
                "identification_method": "FinSight zero/negative/dual-amount structural check",
                "threshold_is_statutory": False,
                "issue_type": issue,
            },
            amount_paise=(amount if amount else None),
            related_transaction_id=row.transaction_id,
        ))

    return outcome
