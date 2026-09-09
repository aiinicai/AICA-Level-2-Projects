"""
AUD-LS-003 — Ledger Scrutiny: Potential Duplicate Transactions.

Audit area: Ledger Scrutiny. Relevant SA: SA 240, SA 500.

SA Reference: SA 240 (fraud risk — duplicate postings are a recognized
double-payment/manipulation indicator), SA 500 (Audit Evidence). Neither
standard prescribes the exact match key used below.
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): flags every GL/JE/BANK
row that shares an identical (transaction_date, account_name/party_name,
amount, description) combination with at least one other row.

Limitation: an exact-match key will miss a duplicate recorded with even
a slightly different narration or a one-day date difference, and can
also flag two genuinely separate, coincidentally identical transactions
(e.g. two identical recurring standing charges). This never itself
concludes a duplicate posting occurred — only that two rows warrant a
side-by-side check against source documents.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-003"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 240, SA 500"
ASSERTIONS = ("OCCURRENCE", "ACCURACY")
TOPIC = "Ledger Scrutiny — Potential Duplicate Transactions"


def _dup_key(v: dict) -> tuple:
    return (
        v.get("transaction_date"),
        v.get("account_name") or v.get("party_name"),
        v.get("debit_amount") or 0,
        v.get("credit_amount") or 0,
        (v.get("description") or "").strip().lower(),
    )


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
    groups: dict[tuple, list] = {}
    for row in ledger_rows:
        key = _dup_key(row.values)
        if key[0] is None or key[1] is None:
            continue  # can't meaningfully compare rows with no date/account at all
        groups.setdefault(key, []).append(row)

    for key, rows in groups.items():
        if len(rows) < 2:
            continue
        for row in rows:
            v = row.values
            account_name = v.get("account_name") or v.get("party_name") or f"row {row.row_index + 1}"
            amount = row_amount(v)
            outcome.exceptions.append(ExceptionDraft(
                label=wording.POTENTIAL_AUDIT_RISK,
                area=AUDIT_AREA,
                trigger_condition=(
                    f'{len(rows)} entries on "{account_name}" share the same date, amount, and narration.'
                ),
                explanation=(
                    f'An entry on "{account_name}" for {paise_to_display(amount)} shares the same date, '
                    f"amount, and narration as {len(rows) - 1} other entr{'y' if len(rows) == 2 else 'ies'} "
                    f"in the same data. This may indicate a duplicate posting, or may simply be two "
                    f"genuinely separate, coincidentally identical transactions — only inspection of the "
                    f"supporting invoice/voucher can establish which."
                ),
                suggested_query=(
                    "Please verify against supporting invoice/voucher to confirm this is not a duplicate entry."
                ),
                risk_level="HIGH",
                data_sources=[str(row.file_id)],
                threshold_used={
                    "identification_method": "FinSight exact-match duplicate key (date, account/party, amount, narration)",
                    "threshold_is_statutory": False,
                    "matched_row_count": len(rows),
                },
                amount_paise=amount or None,
                related_transaction_id=row.transaction_id,
            ))

    return outcome
