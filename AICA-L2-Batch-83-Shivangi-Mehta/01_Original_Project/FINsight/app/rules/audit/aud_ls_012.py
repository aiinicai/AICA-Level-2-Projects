"""
AUD-LS-012 — Ledger Scrutiny: Unusual Ledger Activity.

Audit area: Ledger Scrutiny. Relevant SA: SA 520.

SA Reference: SA 520 (Analytical Procedures) — comparing one month's
activity on a ledger account against that same account's activity in
other months is a textbook trend analytical procedure. SA 520 does not
prescribe the exact multiples used below.

FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): within each account_name
with activity spread across at least 2 calendar months, this check
flags a month in EITHER direction:

  - Unusually HIGH: that month's total exceeds twice the average
    monthly total of that same account's other months.
  - Unusually LOW: that month's total is less than half the MEDIAN
    monthly total of that same account's other months — but only when
    there are at least 3 other months to compare against.

Stage 21 addition (explicitly approved): the original version of this
check only looked for unusually HIGH months. The user pointed out it
should also catch a month that's unusually LOW compared to the same
ledger's other months — for example, a recurring monthly expense head
that suddenly shows far less activity than normal, which can indicate
an entry that was missed or booked to the wrong account, not just one
that looks suspiciously large.

Why the "too low" side needs 3 other months, not 2, and uses the
median instead of the mean: with only 2 other months, a single
genuinely large month (a big one-off purchase, a bulk order — exactly
the kind of thing this same check's own "too high" side already
expects and explains away) drags the *average* of "other months" up so
far that every other, perfectly normal month then looks artificially
"too low" by comparison — every month in a 3-month dataset would end
up flagged, which is a false-positive flood, not a real finding. Once
there are at least 3 other months, comparing against their MEDIAN
instead fixes this: a single extreme month becomes just the largest
value in that group rather than something that drags the whole
baseline up, so a genuinely low month is no longer confused with "the
other months happened to include one big one." This is the same kind
of small-sample statistical limitation already disclosed for
AUD-LS-006 (Unusual Amount vs Ledger Pattern) — flagged here rather
than silently shipped.

Limitation: a genuine seasonal or one-off business event (a large
year-end purchase, a bulk order, a slow month with genuinely less
business) can also produce either pattern — this flags the month for
review, not an irregularity.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement, or no account has activity in 2 or more distinct months.
The "too low" side specifically needs 3 or more OTHER months of
history for a given account before it will ever fire; with fewer, only
the "too high" side is evaluated for that account.
"""
from __future__ import annotations

import statistics
from datetime import date

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import (
    UNUSUAL_LEDGER_DIP_DIVISOR,
    UNUSUAL_LEDGER_DIP_MIN_OTHER_MONTHS,
    UNUSUAL_LEDGER_MIN_MONTHS,
    collect_ledger_rows,
    row_amount,
)
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-012"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 520"
ASSERTIONS = ("ACCURACY", "VALUATION", "COMPLETENESS")
TOPIC = "Ledger Scrutiny — Unusual Ledger Activity"

_SPIKE_MULTIPLE = 2


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

    # account_name -> month_key -> [rows]
    accounts: dict[str, dict[str, list]] = {}
    considered = 0
    for row in ledger_rows:
        v = row.values
        account_name = (v.get("account_name") or "").strip()
        month_key = _parse_month(v.get("transaction_date"))
        if not account_name or not month_key:
            continue
        considered += 1
        accounts.setdefault(account_name, {}).setdefault(month_key, []).append(row)

    outcome.evaluated_count = considered
    eligible = {name: months for name, months in accounts.items() if len(months) >= UNUSUAL_LEDGER_MIN_MONTHS}
    if not eligible:
        outcome.insufficient_data_reason = (
            f"No ledger account has activity spread across {UNUSUAL_LEDGER_MIN_MONTHS} or more distinct "
            f"calendar months, which FinSight requires before a month-over-month comparison is meaningful."
        )
        return outcome

    for account_name, months in eligible.items():
        monthly_totals = {m: sum(row_amount(r.values) for r in rows) for m, rows in months.items()}
        for month_key, rows in months.items():
            other_totals = [t for m, t in monthly_totals.items() if m != month_key]
            if not other_totals:
                continue
            this_total = monthly_totals[month_key]

            other_avg = sum(other_totals) / len(other_totals)
            is_spike = other_avg > 0 and this_total > _SPIKE_MULTIPLE * other_avg

            is_dip = False
            dip_baseline = None
            if len(other_totals) >= UNUSUAL_LEDGER_DIP_MIN_OTHER_MONTHS:
                dip_baseline = statistics.median(other_totals)
                is_dip = (
                    dip_baseline > 0 and this_total > 0
                    and this_total < dip_baseline / UNUSUAL_LEDGER_DIP_DIVISOR
                )

            # A month is judged on whichever side actually fired — the
            # two conditions cannot both hold in practice (a total can't
            # simultaneously exceed 2x one baseline and fall under 1/2 of
            # another), but "spike wins" if it somehow ever did, since a
            # high-value spike is the higher-risk finding of the two.
            if is_spike:
                direction = "high"
                baseline = other_avg
                baseline_desc = "average"
            elif is_dip:
                direction = "low"
                baseline = dip_baseline
                baseline_desc = "median"
            else:
                continue

            for row in rows:
                amount = row_amount(row.values)
                if direction == "high":
                    trigger_condition = (
                        f'"{account_name}" posted {paise_to_display(this_total)} in {month_key}, more than '
                        f"{_SPIKE_MULTIPLE}x this account's {baseline_desc} of {paise_to_display(round(baseline))} "
                        f"in its other months."
                    )
                    explanation = (
                        f'"{account_name}" posted a total of {paise_to_display(this_total)} in {month_key}, '
                        f"more than {_SPIKE_MULTIPLE} times this same account's {baseline_desc} monthly total of "
                        f"{paise_to_display(round(baseline))} across its other months. A genuine seasonal or "
                        f"one-off business event can also produce this pattern — this flags the month for "
                        f"review, not an irregularity."
                    )
                    suggested_query = (
                        f'Please explain the reason for the unusually high activity on "{account_name}" in {month_key}.'
                    )
                else:
                    trigger_condition = (
                        f'"{account_name}" posted only {paise_to_display(this_total)} in {month_key}, less than '
                        f"half this account's {baseline_desc} of {paise_to_display(round(baseline))} in its "
                        f"other months."
                    )
                    explanation = (
                        f'"{account_name}" posted a total of only {paise_to_display(this_total)} in {month_key}, '
                        f"less than half this same account's {baseline_desc} monthly total of "
                        f"{paise_to_display(round(baseline))} across its other months. A genuinely slow month can "
                        f"also produce this pattern — this flags the month for review, not confirmation that an "
                        f"entry is missing."
                    )
                    suggested_query = (
                        f'Please confirm whether all expected entries on "{account_name}" for {month_key} have '
                        f"been recorded, or explain the reason for the unusually low activity."
                    )

                outcome.exceptions.append(ExceptionDraft(
                    label=wording.REVIEW_REQUIRED,
                    area=AUDIT_AREA,
                    trigger_condition=trigger_condition,
                    explanation=explanation,
                    suggested_query=suggested_query,
                    risk_level="MEDIUM",
                    data_sources=[str(row.file_id)],
                    threshold_used={
                        "identification_method": f"FinSight month-over-month ledger-activity {direction} check",
                        "direction": direction,
                        "spike_multiple": _SPIKE_MULTIPLE if direction == "high" else None,
                        "dip_divisor": UNUSUAL_LEDGER_DIP_DIVISOR if direction == "low" else None,
                        "threshold_is_statutory": False,
                        "month_total_paise": this_total,
                        "other_months_baseline_paise": round(baseline),
                        "other_months_baseline_method": baseline_desc,
                    },
                    amount_paise=amount or None,
                    related_transaction_id=row.transaction_id,
                ))

    return outcome
