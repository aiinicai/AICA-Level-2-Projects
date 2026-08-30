"""
AUD-LS-002 — Ledger Scrutiny: Generic / Insufficient Narration.

Audit area: Ledger Scrutiny. Relevant SA: SA 500.

SA Reference: SA 500 (Audit Evidence) — same basis as AUD-LS-001, one
step short of it: a narration that exists but is generic/boilerplate
("payment", "general", "misc", "transfer" and similar) or too short to
convey any real business detail is only marginally more useful than no
narration at all.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA; adapted from a user-provided ledger-scrutiny prototype — see
`ledger_scrutiny_shared.py`): flags a GL/JE/BANK row (excluding one
already flagged blank by AUD-LS-001) whose narration is an exact/near
match to a FinSight generic-term word list, or is very short (<= 6
characters) with no digit in it.

Limitation: keyword/length matching is FinSight's own approximation —
a short but genuinely informative narration ("GST paid") can still be
flagged, and a long but equally uninformative one can be missed.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import GENERIC_NARRATION_TERMS, collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome

RULE_ID = "AUD-LS-002"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 500"
ASSERTIONS = ("COMPLETENESS", "ACCURACY")
TOPIC = "Ledger Scrutiny — Generic Narration"


def _is_generic(narration: str) -> bool:
    lower = narration.lower().strip(".")
    if lower in GENERIC_NARRATION_TERMS:
        return True
    is_too_short = len(narration) <= 6 and not any(ch.isdigit() for ch in narration)
    return is_too_short


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
        description = (v.get("description") or "").strip()
        if not description or not _is_generic(description):
            continue  # blank is AUD-LS-001's; a genuinely descriptive narration isn't flagged here

        account_name = v.get("account_name") or f"row {row.row_index + 1}"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=f'Entry on "{account_name}" has narration "{description}", which may not provide sufficient detail.',
            explanation=(
                f'An entry on "{account_name}" carries the narration "{description}" — matched against '
                f"FinSight's own generic-term/short-narration heuristic as potentially insufficient to convey "
                f"the entry's actual business purpose. This is a candidate for review, not a finding that the "
                f"entry itself is improper — a short narration can still be entirely adequate in context."
            ),
            suggested_query="Please confirm the business purpose and supporting documents for this entry.",
            risk_level="LOW",
            data_sources=[str(row.file_id)],
            threshold_used={
                "identification_method": "FinSight generic/short-narration heuristic",
                "threshold_is_statutory": False,
            },
            amount_paise=row_amount(v) or None,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
