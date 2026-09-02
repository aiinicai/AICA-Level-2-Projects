"""
AUD-LS-007 — Ledger Scrutiny: Possible Split Transactions.

Audit area: Ledger Scrutiny. Relevant SA: SA 240, SA 500.

SA Reference: SA 240 (fraud risk — breaking one transaction into
several smaller ones is a recognized technique for evading an approval
or materiality threshold), SA 500 (Audit Evidence). Neither standard
prescribes the exact grouping key or materiality figure used below.
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): groups GL/JE/BANK rows by
the same party and the same transaction date; where 2 or more such rows
exist, each individually below the applicable materiality threshold,
but their combined total on that date meets or exceeds it, every row in
the group is flagged.

Limitation: a party can legitimately have more than one genuine,
unrelated transaction on the same day — this is a pattern screen, not
proof that any splitting occurred; only inspection of the underlying
invoices/vouchers can establish that.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement, or no row carries both a party name and a transaction date.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import resolve_materiality_threshold_paise
from app.rules.audit.ledger_scrutiny_shared import collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-007"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 240, SA 500"
ASSERTIONS = ("OCCURRENCE", "ACCURACY")
TOPIC = "Ledger Scrutiny — Possible Split Transactions"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = collect_ledger_rows(dataset)
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entry, or Bank Statement data is "
            "available for this engagement."
        )
        return outcome

    threshold_paise, threshold_source = resolve_materiality_threshold_paise(engagement)

    groups: dict[tuple, list] = {}
    considered = 0
    for row in ledger_rows:
        v = row.values
        party = v.get("party_name") or v.get("account_name")
        txn_date = v.get("transaction_date")
        if not party or not txn_date:
            continue
        considered += 1
        groups.setdefault((party, txn_date), []).append(row)

    outcome.evaluated_count = considered
    if considered == 0:
        outcome.insufficient_data_reason = (
            "No General Ledger, Journal Entry, or Bank Statement row carries both a party name and a "
            "transaction date, which this check needs to group same-day entries."
        )
        return outcome

    for (party, txn_date), rows in groups.items():
        if len(rows) < 2:
            continue
        amounts = [row_amount(row.values) for row in rows]
        total = sum(amounts)
        if total < threshold_paise:
            continue
        if any(a >= threshold_paise for a in amounts):
            continue  # at least one leg already meets the threshold on its own — not a "split"

        for row, amount in zip(rows, amounts):
            outcome.exceptions.append(ExceptionDraft(
                label=wording.POTENTIAL_AUDIT_RISK,
                area=AUDIT_AREA,
                trigger_condition=(
                    f'{len(rows)} entries with "{party}" on {txn_date}, each below the applicable materiality '
                    f"threshold individually, total {paise_to_display(total)} — at or above that threshold."
                ),
                explanation=(
                    f'An entry with "{party}" on {txn_date} for {paise_to_display(amount)} is one of {len(rows)} '
                    f"same-day entries with this party, none individually meeting {threshold_source}, but "
                    f"totalling {paise_to_display(total)} together — at or above it. This may indicate a single "
                    f"transaction was split across multiple postings, or may simply be several genuinely "
                    f"separate transactions with the same party on the same day."
                ),
                suggested_query=(
                    "Please confirm whether these same-day entries represent separate transactions or a single "
                    "transaction recorded in parts, and provide the supporting invoices/vouchers."
                ),
                risk_level="HIGH",
                data_sources=[str(row.file_id)],
                threshold_used={
                    "identification_method": "FinSight same-party/same-date split-transaction check",
                    "materiality_threshold_paise": threshold_paise,
                    "materiality_threshold_source": threshold_source,
                    "threshold_is_statutory": False,
                    "group_total_paise": total,
                    "group_row_count": len(rows),
                },
                amount_paise=amount or None,
                related_transaction_id=row.transaction_id,
            ))

    return outcome
