"""
AUD-JE-002 — Manual Journal Entry Posted on a Non-Business Day.

Audit area: Journal Entry Testing. Relevant SA: SA 240. Assertions:
Occurrence, Existence. Risk level: LOW / Advisory (Stage 9 catalogue
review: "a weekend posting is not inherently suspicious").

SA Reference (authoritative — ICAI Standard on Auditing): SA 240. This
citation identifies the fraud-risk-testing context this check sits
within; it does NOT mean SA 240 prescribes a weekend-posting test —
SA 240 says nothing about day-of-week.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a manual JE whose `transaction_date` falls on a Saturday or
Sunday (`_WEEKEND_WEEKDAYS`). No amount or materiality threshold is
applied to this rule.

REDESIGNED from the original "weekend/off-hours" brief during the
Stage 9 catalogue-review stage (documented there, restated here): no
field anywhere in the approved schema captures a posting timestamp —
`transaction_date` is a date only. "Off-hours" is therefore not
computable and is deliberately NOT inferred or guessed at; this rule
tests weekend posting only, which the date value alone can support.

What data is required: `JE` rows with `is_manual_entry`, `transaction_date`.
What can actually be established: whether a manual entry's transaction_date
falls on a Saturday or Sunday.
What cannot be established: the actual posting timestamp, or whether a
weekend date reflects genuine weekend work, a backdated/predated entry,
or simply a data-entry convention at this entity — this is a low-
confidence advisory signal only.
Insufficient data: no validated JE data at all.
"""
from __future__ import annotations

from datetime import date

from app.rules import wording
from app.rules.accounting.shared_detectors import is_flag_true
from app.rules.base_rule import ExceptionDraft, RuleOutcome

RULE_ID = "AUD-JE-002"
AUDIT_AREA = "Journal Entry Testing"
RELATED_SA = "SA 240"
ASSERTIONS = ("OCCURRENCE", "EXISTENCE")
TOPIC = "Manual Journal Entry Posted on a Non-Business Day"

_WEEKEND_WEEKDAYS = (5, 6)  # Saturday, Sunday


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    je_rows = dataset.get("JE", [])
    if not je_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Journal Entry data is available for this engagement."
        )
        return outcome

    for row in je_rows:
        v = row.values
        if not is_flag_true(v.get("is_manual_entry")):
            continue
        raw_date = v.get("transaction_date")
        if not raw_date:
            outcome.partial_insufficient_data_notes.append(
                f"Manual JE row (file {row.file_id}, row {row.row_index + 1}): no Transaction Date value — "
                f"day-of-week could not be assessed."
            )
            continue
        try:
            txn_date = date.fromisoformat(raw_date)
        except ValueError:
            outcome.partial_insufficient_data_notes.append(
                f"Manual JE row (file {row.file_id}, row {row.row_index + 1}): Transaction Date could not be parsed."
            )
            continue

        outcome.evaluated_count += 1
        if txn_date.weekday() not in _WEEKEND_WEEKDAYS:
            continue

        description = v.get("description") or v.get("account_name") or f"entry (row {row.row_index + 1})"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=(
                f"Manual journal entry dated {txn_date.isoformat()} ({txn_date.strftime('%A')}), a non-business day."
            ),
            explanation=(
                f'Manual entry "{description}" is dated {txn_date.isoformat()}, a {txn_date.strftime("%A")}. This '
                f"is a low-confidence advisory signal only — no posting timestamp field exists in the uploaded "
                f"data (only a transaction date), so this reflects the date recorded, not necessarily when the "
                f"entry was actually entered into the system. A weekend date is not inherently suspicious and may "
                f"simply reflect this entity's normal data-entry pattern."
            ),
            suggested_query=(
                "Please confirm the business reason, if any, for this manual entry's transaction date falling on "
                "a weekend."
            ),
            risk_level="LOW",
            data_sources=[str(row.file_id)],
            threshold_used={"weekday": txn_date.strftime("%A"), "advisory_only": True},
            related_transaction_id=row.transaction_id,
        ))

    return outcome
