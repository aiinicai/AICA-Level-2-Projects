"""
AUD-JE-003 — Round-Sum Manual Entry Above Threshold.

Audit area: Journal Entry Testing. Relevant SA: SA 240, SA 500 (Audit
Evidence). Assertions: Accuracy, Occurrence.

SA Reference (authoritative — ICAI Standard on Auditing): SA 240,
SA 500. This citation identifies the fraud-risk/evidence context the
check sits within; it does NOT mean either standard prescribes a
"round-sum" definition or a rupee threshold — both are FinSight's own.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a manual JE whose amount is an exact multiple of a
FinSight-configurable "round" denomination (currently ₹10,000 —
`ROUND_DENOMINATION_PAISE`), at or above the applicable materiality
threshold (the engagement's own Overall Materiality if set, else a
FinSight default fallback of ₹1,00,000).

What data is required: `JE` rows with `is_manual_entry`, `debit_amount`/
`credit_amount`.
What can actually be established: whether a manual entry's amount is an
exact multiple of a configurable "round" denomination, at or above a
materiality-derived threshold.
What cannot be established: whether the amount reflects an estimate
rather than a precisely-calculated transaction — that is exactly what
the suggested procedure below asks a reviewer to determine; a round
figure is not inherently wrong.
Insufficient data: no validated JE data at all.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import resolve_materiality_threshold_paise, is_flag_true
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-JE-003"
AUDIT_AREA = "Journal Entry Testing"
RELATED_SA = "SA 240, SA 500"
ASSERTIONS = ("ACCURACY", "OCCURRENCE")
TOPIC = "Round-Sum Manual Entry Above Threshold"

# A FinSight-configurable "roundness" definition, not an SA concept.
ROUND_DENOMINATION_PAISE = 1_000_000  # ₹10,000


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    je_rows = dataset.get("JE", [])
    if not je_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Journal Entry data is available for this engagement."
        )
        return outcome

    threshold_paise, threshold_source = resolve_materiality_threshold_paise(engagement)

    for row in je_rows:
        v = row.values
        if not is_flag_true(v.get("is_manual_entry")):
            continue

        outcome.evaluated_count += 1
        amount = max(v.get("debit_amount") or 0, v.get("credit_amount") or 0)
        if amount <= 0 or amount % ROUND_DENOMINATION_PAISE != 0:
            continue
        if amount < threshold_paise:
            continue

        description = v.get("description") or v.get("account_name") or f"entry (row {row.row_index + 1})"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_AUDIT_RISK,
            area=AUDIT_AREA,
            trigger_condition=(
                f"Manual journal entry of exactly {paise_to_display(amount)} — a round multiple of "
                f"{paise_to_display(ROUND_DENOMINATION_PAISE)}, at or above the applicable threshold "
                f"({paise_to_display(threshold_paise)}, from {threshold_source})."
            ),
            explanation=(
                f'Manual entry "{description}" for {paise_to_display(amount)} is an exact multiple of the '
                f"FinSight-configurable round-sum denomination ({paise_to_display(ROUND_DENOMINATION_PAISE)}) and "
                f"is at or above the applicable threshold. A round-sum amount is not inherently incorrect — it may "
                f"reflect a genuine estimate, a round contractual figure, or simply be a coincidence — this "
                f"heuristic only flags it for professional review of the underlying calculation."
            ),
            suggested_query=(
                "Please provide the calculation or supporting basis for this round-sum entry, and confirm whether "
                "it reflects a precise transaction or an estimate."
            ),
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "round_denomination_paise": ROUND_DENOMINATION_PAISE,
                "amount_threshold_paise": threshold_paise,
                "amount_threshold_source": threshold_source,
                "threshold_is_sa_requirement": False,
            },
            amount_paise=amount,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
