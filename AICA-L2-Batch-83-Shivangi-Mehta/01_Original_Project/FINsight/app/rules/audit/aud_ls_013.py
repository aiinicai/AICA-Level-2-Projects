"""
AUD-LS-013 — Ledger Scrutiny: Unusual Ledger Usage.

Audit area: Ledger Scrutiny. Relevant SA: SA 520.

SA Reference: SA 520 (Analytical Procedures) — a party's overall
transaction pattern is a legitimate analytical baseline against which a
single, one-off posting can be compared. SA 520 does not prescribe the
exact frequency thresholds used below.
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): for a party with at least
5 transactions overall, spread across at least 2 distinct ledger
accounts, flags a row on any one of those accounts where that account
was used by this party only once — i.e. an isolated, one-off posting
against an otherwise-unfamiliar ledger for a party this active
elsewhere.

Limitation: a party's very first (or a genuinely one-off) transaction
on a new, legitimate account will always look like this — this flags
the pattern for review, not an irregularity.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement, or no party meets both the minimum transaction count and
minimum distinct-ledger count.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import (
    UNUSUAL_USAGE_MIN_LEDGERS,
    UNUSUAL_USAGE_MIN_PARTY_TXNS,
    collect_ledger_rows,
    row_amount,
)
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-013"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 520"
ASSERTIONS = ("OCCURRENCE", "CLASSIFICATION")
TOPIC = "Ledger Scrutiny — Unusual Ledger Usage"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = collect_ledger_rows(dataset)
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entry, or Bank Statement data is "
            "available for this engagement."
        )
        return outcome

    # party -> account_name -> [rows]
    parties: dict[str, dict[str, list]] = {}
    considered = 0
    for row in ledger_rows:
        v = row.values
        party = (v.get("party_name") or "").strip()
        account_name = (v.get("account_name") or "").strip()
        if not party or not account_name:
            continue
        considered += 1
        parties.setdefault(party, {}).setdefault(account_name, []).append(row)

    outcome.evaluated_count = considered
    eligible = {
        party: accounts for party, accounts in parties.items()
        if sum(len(rows) for rows in accounts.values()) >= UNUSUAL_USAGE_MIN_PARTY_TXNS
        and len(accounts) >= UNUSUAL_USAGE_MIN_LEDGERS
    }
    if not eligible:
        outcome.insufficient_data_reason = (
            f"No party has both {UNUSUAL_USAGE_MIN_PARTY_TXNS} or more total transactions and "
            f"{UNUSUAL_USAGE_MIN_LEDGERS} or more distinct ledger accounts, which FinSight requires before a "
            f"per-party usage baseline is meaningful."
        )
        return outcome

    for party, accounts in eligible.items():
        total_txns = sum(len(rows) for rows in accounts.values())
        for account_name, rows in accounts.items():
            if len(rows) != 1:
                continue
            row = rows[0]
            amount = row_amount(row.values)
            outcome.exceptions.append(ExceptionDraft(
                label=wording.REVIEW_REQUIRED,
                area=AUDIT_AREA,
                trigger_condition=(
                    f'"{party}" has {total_txns} total transactions across {len(accounts)} ledger accounts, but '
                    f'used "{account_name}" only once.'
                ),
                explanation=(
                    f'"{party}" has {total_txns} transactions recorded across {len(accounts)} distinct ledger '
                    f'accounts in this data, but the entry on "{account_name}" is the only one posted against '
                    f"that particular account. This is an isolated, one-off posting for a party who is "
                    f"otherwise active elsewhere — a legitimate first-time or one-off transaction will also "
                    f"look like this, so it is a candidate for review, not an irregularity."
                ),
                suggested_query=f'Please confirm the business reason "{party}" used "{account_name}" on this one occasion.',
                risk_level="LOW",
                data_sources=[str(row.file_id)],
                threshold_used={
                    "identification_method": "FinSight isolated-ledger-usage-per-party check",
                    "min_party_transactions": UNUSUAL_USAGE_MIN_PARTY_TXNS,
                    "min_distinct_ledgers": UNUSUAL_USAGE_MIN_LEDGERS,
                    "threshold_is_statutory": False,
                    "party_total_transactions": total_txns,
                    "party_distinct_ledgers": len(accounts),
                },
                amount_paise=amount or None,
                related_transaction_id=row.transaction_id,
            ))

    return outcome
