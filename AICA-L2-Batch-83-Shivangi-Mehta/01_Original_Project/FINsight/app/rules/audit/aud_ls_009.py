"""
AUD-LS-009 — Ledger Scrutiny: Year-End Transaction.

Audit area: Ledger Scrutiny. Relevant SA: SA 240, SA 520.

SA Reference: SA 240 (fraud risk — entries clustered right at financial
year-end are a recognized area for possible earnings-management or
cut-off manipulation), SA 520 (Analytical Procedures). Neither standard
prescribes the exact 3-day window used below.
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): using the engagement's own
financial year (Indian convention, 1 April - 31 March), flags a GL/JE/
BANK row dated within the last 3 days of that financial year (29-31
March for a standard year).

Limitation: genuine, routine year-end entries (accruals, provisions,
closing adjustments) also fall in this window — a flag here is a
candidate for review, not evidence of manipulation.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement, the engagement's financial year could not be parsed, or no
row carries a parseable transaction date.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.period_utils import financial_year_bounds
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-009"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 240, SA 520"
ASSERTIONS = ("CUT_OFF",)
TOPIC = "Ledger Scrutiny — Year-End Transaction"

_WINDOW_DAYS = 3


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = collect_ledger_rows(dataset)
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entry, or Bank Statement data is "
            "available for this engagement."
        )
        return outcome

    bounds = financial_year_bounds(engagement.financial_year)
    if bounds is None:
        outcome.insufficient_data_reason = (
            f"The engagement's financial year (\"{engagement.financial_year}\") could not be parsed into "
            f"calendar bounds."
        )
        return outcome
    _fy_start, fy_end = bounds
    window_start = fy_end - timedelta(days=_WINDOW_DAYS - 1)

    considered = 0
    for row in ledger_rows:
        v = row.values
        txn_date = _parse_date(v.get("transaction_date"))
        if txn_date is None:
            continue
        considered += 1
        if not (window_start <= txn_date <= fy_end):
            continue

        account_name = v.get("account_name") or v.get("party_name") or f"row {row.row_index + 1}"
        amount = row_amount(v)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=f'Entry on "{account_name}" dated {txn_date.isoformat()} falls within the last {_WINDOW_DAYS} days of the financial year.',
            explanation=(
                f'An entry on "{account_name}" dated {txn_date.isoformat()} falls within the last {_WINDOW_DAYS} '
                f"days of the engagement's financial year (ending {fy_end.isoformat()}). Year-end entries are "
                f"common and routine, but this window also carries a higher concentration of manual adjustments, "
                f"provisions, and cut-off risk, which is why FinSight surfaces it for review."
            ),
            suggested_query="Please confirm the business rationale and cut-off treatment of this year-end entry.",
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "identification_method": "FinSight financial-year-end window check",
                "window_days": _WINDOW_DAYS,
                "financial_year_end": fy_end.isoformat(),
                "threshold_is_statutory": False,
            },
            amount_paise=amount or None,
            related_transaction_id=row.transaction_id,
        ))

    outcome.evaluated_count = considered
    if considered == 0:
        outcome.insufficient_data_reason = (
            "No General Ledger, Journal Entry, or Bank Statement row carries a parseable transaction date."
        )
    return outcome
