"""
AUD-LS-005 — Ledger Scrutiny: Round-Number Transaction.

Audit area: Ledger Scrutiny. Relevant SA: SA 240, SA 500.

SA Reference: SA 240 (fraud risk — round, unusually "clean" amounts are
a recognized indicator that a figure may have been estimated, adjusted,
or fabricated rather than arising from an actual invoiced/metered
transaction), SA 500 (Audit Evidence). Neither standard prescribes the
exact rounding threshold used below.
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): flags a GL/JE/BANK row
whose amount is a non-zero exact multiple of FinSight's own round-number
divisor (₹5,000).

Limitation: many entirely genuine transactions are round by nature
(round-figure advances, standing charges, estimated provisions agreed
with a party) — a match here is a candidate for review, not evidence of
manipulation.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import ROUND_DIVISOR_PAISE, collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-005"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 240, SA 500"
ASSERTIONS = ("ACCURACY", "VALUATION")
TOPIC = "Ledger Scrutiny — Round-Number Transaction"


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
        amount = row_amount(v)
        if not amount or amount % ROUND_DIVISOR_PAISE != 0:
            continue

        account_name = v.get("account_name") or v.get("party_name") or f"row {row.row_index + 1}"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=f'Entry on "{account_name}" for {paise_to_display(amount)} is an exact round figure.',
            explanation=(
                f'An entry on "{account_name}" for {paise_to_display(amount)} is an exact multiple of '
                f"{paise_to_display(ROUND_DIVISOR_PAISE)}, matched against FinSight's own round-number screen. "
                f"Round amounts are common in genuine transactions and this is not itself an indicator of "
                f"manipulation — only a candidate for a closer look at the supporting document."
            ),
            suggested_query="Please confirm the basis on which this round-figure amount was arrived at.",
            risk_level="LOW",
            data_sources=[str(row.file_id)],
            threshold_used={
                "identification_method": "FinSight round-number check",
                "round_divisor_paise": ROUND_DIVISOR_PAISE,
                "threshold_is_statutory": False,
            },
            amount_paise=amount,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
