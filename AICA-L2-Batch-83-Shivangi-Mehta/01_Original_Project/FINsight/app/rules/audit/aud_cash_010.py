"""
AUD-CASH-010 — Material Cash Transaction Review.

Audit area: Material Cash Transaction Review (renamed from the original
catalogue proposal's "Unusual Cash Movements" per Stage 9 review
correction #11 — a material cash transaction is not inherently unusual
or inappropriate, and the rule's own wording must not imply that it is).
Relevant SA: SA 240, SA 500. Assertions: Existence, Occurrence.

SA Reference (authoritative — ICAI Standard on Auditing): SA 240,
SA 500. This citation identifies cash transactions as a recognized
fraud-risk/evidence area under these standards; it does NOT mean either
standard prescribes a materiality figure for cash transactions — the
threshold applied below is entirely FinSight's own (or the engagement's
own configured Overall Materiality).
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a BANK row recorded with a cash payment mode (`payment_mode`
contains "cash") at or above the applicable materiality threshold (the
engagement's own Overall Materiality if set, else a FinSight default
fallback of ₹1,00,000).

What data is required: `BANK` rows with `payment_mode`, `transaction_date`,
and an amount (`debit_amount`/`credit_amount`).
What can actually be established: whether a Bank Statement row is
recorded with a cash payment mode (via the shared `is_cash_payment_mode()`
normalizer, since `payment_mode` is a free-text field, never a real
boolean) and an amount at or above the applicable materiality threshold.
What cannot be established: that the transaction is inappropriate,
irregular, or improperly documented — only that its cash nature and
size make it a candidate for review; the finding text is deliberately
neutral on this point per the Stage 9 wording requirement.
Insufficient data: no validated BANK data, or no row anywhere in the
BANK data has a `payment_mode` value populated (the field exists in the
mapping but was never actually mapped/populated for this engagement).
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import is_cash_payment_mode, resolve_materiality_threshold_paise
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-CASH-010"
AUDIT_AREA = "Material Cash Transaction Review"
RELATED_SA = "SA 240, SA 500"
ASSERTIONS = ("EXISTENCE", "OCCURRENCE")
TOPIC = "Material Cash Transaction Review"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    bank_rows = dataset.get("BANK", [])
    if not bank_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Bank Statement data is available for this engagement."
        )
        return outcome

    if not any((row.values.get("payment_mode") or "").strip() for row in bank_rows):
        outcome.insufficient_data_reason = (
            "No row in this engagement's validated Bank Statement data has a Payment Mode value populated — cash "
            "transactions cannot be identified without it."
        )
        return outcome

    threshold_paise, threshold_source = resolve_materiality_threshold_paise(engagement)

    for row in bank_rows:
        v = row.values
        payment_mode = v.get("payment_mode")
        if not is_cash_payment_mode(payment_mode):
            continue
        amount = max(v.get("debit_amount") or 0, v.get("credit_amount") or 0)
        if amount <= 0:
            outcome.partial_insufficient_data_notes.append(
                f"Bank Statement row (file {row.file_id}, row {row.row_index + 1}): cash payment mode but no "
                f"amount recorded."
            )
            continue

        outcome.evaluated_count += 1
        if amount < threshold_paise:
            continue

        description = v.get("description") or f"row {row.row_index + 1}"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_AUDIT_RISK,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Cash transaction ("{payment_mode}") for {paise_to_display(amount)} — "{description}" — is at or '
                f"above the applicable materiality threshold."
            ),
            explanation=(
                f'A cash-mode transaction for {paise_to_display(amount)} ("{description}") meets or exceeds '
                f"{threshold_source}, used here as a FinSight analytical threshold. This flags the transaction as "
                f"a material cash transaction warranting review — it does not imply that the transaction is "
                f"inherently unusual or inappropriate."
            ),
            suggested_query=(
                "Please provide the explanation and supporting documentation for this cash transaction."
            ),
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "materiality_threshold_paise": threshold_paise,
                "materiality_threshold_source": threshold_source,
                "threshold_is_sa_requirement": False,
            },
            amount_paise=amount,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
