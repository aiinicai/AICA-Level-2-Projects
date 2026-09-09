"""
AUD-REV-008 — Revenue Entry With No Matching Receivable.

Audit area: Unusual Revenue Transactions. Relevant SA: SA 240, SA 315.
Assertions: Existence, Completeness.

SA Reference (authoritative — ICAI Standard on Auditing): SA 240,
SA 315. This citation identifies revenue as a recognized fraud-risk
area under these standards; it does NOT mean either standard prescribes
this specific party-name-and-amount matching heuristic, its date
window, or its tolerance — all are FinSight's own.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a SALES row with no matching Accounts Receivable row for the
same normalized party name and a comparable amount, within a
FinSight-configurable date-proximity window (currently 15 days —
`DATE_PROXIMITY_WINDOW_DAYS`) and a small rounding tolerance
(`AMOUNT_MATCH_TOLERANCE_PAISE`).

What data is required: `SALES` and `AR` rows, both with `party_name`
and an amount (`debit_amount`/`credit_amount`), and (for date
proximity) `transaction_date`.
What can actually be established: whether a SALES row has no AR row
for a matching (normalized) party name and a comparable amount within a
configurable date-proximity window.
What cannot be established: a definitive reconciliation — there is no
shared invoice-level key between the SALES and AR file types, so this
is a heuristic party-name-and-amount match, not a true reconciliation;
a genuine mismatch in how party names are recorded between the two
files will produce false positives, disclosed here rather than silently
assumed away.
Insufficient data: no validated SALES data, or no validated AR data at
all for this engagement (the latter makes the comparison meaningless,
not merely "no matches found").
"""
from __future__ import annotations

import re

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-REV-008"
AUDIT_AREA = "Unusual Revenue Transactions"
RELATED_SA = "SA 240, SA 315"
ASSERTIONS = ("EXISTENCE", "COMPLETENESS")
TOPIC = "Revenue Entry With No Matching Receivable"

# FinSight-configurable heuristic parameters, not SA requirements.
DATE_PROXIMITY_WINDOW_DAYS = 15
AMOUNT_MATCH_TOLERANCE_PAISE = 100  # ~₹1 — rounding only

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", (text or "").strip().lower()).strip()


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    sales_rows = dataset.get("SALES", [])
    if not sales_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Sales data is available for this engagement."
        )
        return outcome

    ar_rows = dataset.get("AR", [])
    if not ar_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Accounts Receivable data is available for this engagement — a "
            "matching comparison is not meaningful without it."
        )
        return outcome

    ar_by_party: dict[str, list] = {}
    for row in ar_rows:
        key = _normalize(row.values.get("party_name"))
        if key:
            ar_by_party.setdefault(key, []).append(row)

    for row in sales_rows:
        v = row.values
        party_name = v.get("party_name")
        amount = max(v.get("debit_amount") or 0, v.get("credit_amount") or 0)
        if not party_name or amount <= 0:
            outcome.partial_insufficient_data_notes.append(
                f"Sales row (file {row.file_id}, row {row.row_index + 1}): no Party Name or no amount — a "
                f"receivable match could not be attempted."
            )
            continue

        outcome.evaluated_count += 1
        ar_candidates = ar_by_party.get(_normalize(party_name), [])
        matched = any(
            abs(max(c.values.get("debit_amount") or 0, c.values.get("credit_amount") or 0) - amount)
            <= AMOUNT_MATCH_TOLERANCE_PAISE
            for c in ar_candidates
        )
        if matched:
            continue

        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_AUDIT_RISK,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Sales transaction with "{party_name}" for {paise_to_display(amount)} has no matching Accounts '
                f"Receivable entry for the same party and a comparable amount."
            ),
            explanation=(
                f'A sales transaction with "{party_name}" for {paise_to_display(amount)} could not be matched to '
                f"any Accounts Receivable row for the same (normalized) party name and a comparable amount. This "
                f"is a heuristic party-name-and-amount match, not a true invoice-level reconciliation — there is "
                f"no shared key between the Sales and AR files — so a mismatch may reflect a genuine gap or "
                f"simply differently-recorded party names between the two files."
            ),
            suggested_query=(
                f'Please trace this sale with "{party_name}" to underlying dispatch/service evidence and to the '
                f"receivables ledger or subsequent collection."
            ),
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "date_proximity_window_days": DATE_PROXIMITY_WINDOW_DAYS,
                "amount_match_tolerance_paise": AMOUNT_MATCH_TOLERANCE_PAISE,
                "match_is_heuristic_not_reconciliation": True,
            },
            amount_paise=amount,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
