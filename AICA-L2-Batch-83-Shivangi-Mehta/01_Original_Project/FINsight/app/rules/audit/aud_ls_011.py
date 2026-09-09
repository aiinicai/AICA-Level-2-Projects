"""
AUD-LS-011 — Ledger Scrutiny: Repeated Party Transactions.

Audit area: Ledger Scrutiny. Relevant SA: SA 520.

SA Reference: SA 520 (Analytical Procedures) — an unusually high count
of postings with the same party within a single month is a recognized
prompt for a closer look at that relationship. SA 520 does not
prescribe the exact monthly-count threshold used below.
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): groups GL/JE/BANK rows by
party and calendar month, and flags every row in any party/month group
whose count exceeds FinSight's own threshold (more than 2 entries with
the same party in the same month).

Limitation: a genuinely active, high-volume trading relationship will
routinely exceed this count — this flags a pattern for review, not an
irregularity.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement, or no row carries both a party name and a parseable
transaction date.
"""
from __future__ import annotations

from datetime import date

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import (
    REPEATED_PARTY_MONTHLY_THRESHOLD,
    collect_ledger_rows,
    row_amount,
)
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-011"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 520"
ASSERTIONS = ("OCCURRENCE",)
TOPIC = "Ledger Scrutiny — Repeated Party Transactions"


def _parse_month(value) -> str | None:
    if not value:
        return None
    try:
        d = date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
    return f"{d.year:04d}-{d.month:02d}"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = collect_ledger_rows(dataset)
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entry, or Bank Statement data is "
            "available for this engagement."
        )
        return outcome

    groups: dict[tuple, list] = {}
    considered = 0
    for row in ledger_rows:
        v = row.values
        party = v.get("party_name") or v.get("account_name")
        month_key = _parse_month(v.get("transaction_date"))
        if not party or not month_key:
            continue
        considered += 1
        groups.setdefault((party, month_key), []).append(row)

    outcome.evaluated_count = considered
    if considered == 0:
        outcome.insufficient_data_reason = (
            "No General Ledger, Journal Entry, or Bank Statement row carries both a party name and a "
            "parseable transaction date."
        )
        return outcome

    for (party, month_key), rows in groups.items():
        if len(rows) <= REPEATED_PARTY_MONTHLY_THRESHOLD:
            continue
        for row in rows:
            amount = row_amount(row.values)
            outcome.exceptions.append(ExceptionDraft(
                label=wording.REVIEW_REQUIRED,
                area=AUDIT_AREA,
                trigger_condition=f'"{party}" has {len(rows)} entries in {month_key}, above FinSight\'s threshold of {REPEATED_PARTY_MONTHLY_THRESHOLD}.',
                explanation=(
                    f'"{party}" has {len(rows)} entries recorded in {month_key}, above FinSight\'s own screening '
                    f"threshold of more than {REPEATED_PARTY_MONTHLY_THRESHOLD} entries with the same party in a "
                    f"single month. A genuinely active trading relationship will often exceed this count — this "
                    f"flags the pattern for review, not an irregularity."
                ),
                suggested_query=f'Please confirm the nature of the relationship with "{party}" and the business reason for this transaction frequency.',
                risk_level="LOW",
                data_sources=[str(row.file_id)],
                threshold_used={
                    "identification_method": "FinSight repeated-party-per-month check",
                    "monthly_count_threshold": REPEATED_PARTY_MONTHLY_THRESHOLD,
                    "threshold_is_statutory": False,
                    "party_month_count": len(rows),
                },
                amount_paise=amount or None,
                related_transaction_id=row.transaction_id,
            ))

    return outcome
