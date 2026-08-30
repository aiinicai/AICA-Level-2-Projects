"""
AUD-SUB-007 — Pre-Year-End Entry Reversed Shortly After.

Audit area: Subsequent Period Reversals. Relevant SA: SA 560
(Subsequent Events). Assertions: Occurrence, Cut-off.

SA Reference (authoritative — ICAI Standard on Auditing): SA 560. This
citation identifies the subsequent-events audit context this check
sits within; it does NOT mean SA 560 prescribes a pattern-match test
for pre-year-end entries reversed shortly after, or the specific day
windows/tolerance used below — none of these are SA 560 requirements.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a pre-year-end JE (within a FinSight-configurable window of
year end, currently 10 days — `PRE_YEAR_END_WINDOW_DAYS`) matched by an
equal-and-opposite entry on the same account, either later within the
same financial year, or within a FinSight-configurable window after the
start of the following financial year (currently 10 days —
`POST_PERIOD_WINDOW_DAYS`), within a small rounding tolerance
(`AMOUNT_MATCH_TOLERANCE_PAISE`).

Stage 9 catalogue-review requirement: the within-period and
subsequent-year-engagement halves of this test are implemented and
reported INDEPENDENTLY. The within-period half always runs on this
engagement's own data; if no subsequent-year engagement exists yet for
this entity (the normal case — an audit is usually performed before
next year's engagement is created in FinSight), ONLY that other half is
reported as Insufficient Data via a partial note — it does not block
the within-period half or the rule as a whole.

What data is required: `JE` rows with `transaction_date`, `account_name`,
`debit_amount`/`credit_amount` — this engagement's own, and (for the
subsequent-period half only) a subsequent-year engagement for the same
entity, if one exists.
What can actually be established: whether a pre-year-end entry on a
given account is matched by an equal-and-opposite entry (same account,
swapped debit/credit, amount within a small rounding tolerance) either
(a) later within this same financial year, or (b) shortly after the
start of the following financial year, in a subsequent engagement's own
data.
What cannot be established: whether a matched pair is actually a
deliberate reversal versus two unrelated entries that happen to net to
zero — a pattern-match heuristic requiring professional confirmation,
never a definitive finding.
Insufficient data (whole rule): no validated JE data, or the
engagement's financial year cannot be parsed.
Insufficient data (subsequent-period half only): no subsequent-year
engagement exists yet, or one exists but has no validated JE data.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.rules import wording
from app.rules.accounting.shared_detectors import find_next_year_dataset
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.period_utils import financial_year_bounds
from app.utils.currency import paise_to_display

RULE_ID = "AUD-SUB-007"
AUDIT_AREA = "Subsequent Period Reversals"
RELATED_SA = "SA 560"
ASSERTIONS = ("OCCURRENCE", "CUT_OFF")
TOPIC = "Pre-Year-End Entry Reversed Shortly After"

# FinSight-configurable, not SA requirements.
PRE_YEAR_END_WINDOW_DAYS = 10
POST_PERIOD_WINDOW_DAYS = 10
AMOUNT_MATCH_TOLERANCE_PAISE = 100  # ~₹1 — rounding only


def _parse_rows(rows: list) -> list[tuple]:
    """(row, date, account_name, signed_amount) — signed_amount is
    debit-positive/credit-negative so an exact reversal is a matching
    account with signed_amount negated (within tolerance)."""
    parsed = []
    for row in rows:
        v = row.values
        raw_date = v.get("transaction_date")
        account_name = (v.get("account_name") or "").strip()
        if not raw_date or not account_name:
            continue
        try:
            d = date.fromisoformat(raw_date)
        except ValueError:
            continue
        debit = v.get("debit_amount") or 0
        credit = v.get("credit_amount") or 0
        if debit == 0 and credit == 0:
            continue
        parsed.append((row, d, account_name, debit - credit))
    return parsed


def _find_reversal(candidate, pool: list[tuple], after_date: date, not_after: date | None):
    _cand_row, _cand_date, cand_account, cand_signed = candidate
    for row, d, account_name, signed_amount in pool:
        if account_name != cand_account:
            continue
        if d <= after_date:
            continue
        if not_after is not None and d > not_after:
            continue
        if abs(signed_amount + cand_signed) <= AMOUNT_MATCH_TOLERANCE_PAISE:
            return row, d
    return None


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    je_rows = dataset.get("JE", [])
    if not je_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Journal Entry data is available for this engagement."
        )
        return outcome

    bounds = financial_year_bounds(engagement.financial_year)
    if bounds is None:
        outcome.insufficient_data_reason = (
            f"The engagement's financial year (\"{engagement.financial_year}\") could not be parsed into "
            f"calendar bounds."
        )
        return outcome
    fy_start, fy_end = bounds

    parsed_current = _parse_rows(je_rows)
    pre_year_end_window_start = fy_end - timedelta(days=PRE_YEAR_END_WINDOW_DAYS - 1)
    candidates = [p for p in parsed_current if pre_year_end_window_start <= p[1] <= fy_end]
    outcome.evaluated_count = len(candidates)

    matched_keys = set()

    # --- Half 1: within-period reversal (always attempted; never
    # blocked by subsequent-engagement availability) ---
    for cand in candidates:
        cand_row = cand[0]
        match = _find_reversal(cand, parsed_current, after_date=cand[1], not_after=fy_end)
        if match is None:
            continue
        match_row, match_date = match
        key = (cand_row.file_id, cand_row.row_index)
        if key in matched_keys:
            continue
        matched_keys.add(key)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.AUDIT_ATTENTION_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Entry on "{cand[2]}" dated {cand[1].isoformat()} (within {PRE_YEAR_END_WINDOW_DAYS} day(s) of '
                f"year end) appears reversed by a matching entry dated {match_date.isoformat()}, within the same "
                f"financial year."
            ),
            explanation=(
                f'A pre-year-end entry on account "{cand[2]}" dated {cand[1].isoformat()} appears to be reversed '
                f"by an equal-and-opposite entry on the same account dated {match_date.isoformat()}, still within "
                f"this engagement's own financial year. This is a pattern match on account + amount only — it "
                f"does not confirm the two entries are actually related, only that they warrant inspection to "
                f"assess the original entry's period-matching and business rationale."
            ),
            suggested_query=(
                f'Please explain the business rationale for the entry on "{cand[2]}" dated {cand[1].isoformat()} '
                f"and its apparent reversal on {match_date.isoformat()}."
            ),
            risk_level="HIGH",
            data_sources=[str(cand_row.file_id), str(match_row.file_id)],
            threshold_used={
                "pre_year_end_window_days": PRE_YEAR_END_WINDOW_DAYS,
                "amount_match_tolerance_paise": AMOUNT_MATCH_TOLERANCE_PAISE,
                "half": "within_period",
            },
            amount_paise=abs(cand[3]),
        ))

    # --- Half 2: subsequent-period reversal (independent; only THIS
    # half reports Insufficient Data when a next-year engagement isn't
    # available — the within-period half above already ran regardless) ---
    next_dataset = find_next_year_dataset(engagement)
    if next_dataset is None:
        outcome.partial_insufficient_data_notes.append(
            f"No subsequent-year engagement exists yet for \"{engagement.entity_name}\" — the subsequent-period "
            f"half of this test (matching a pre-year-end entry against an early-next-period reversal in the "
            f"following year's engagement) could not be run. The within-period half above ran independently on "
            f"this engagement's own data."
        )
    else:
        next_je = next_dataset.get("JE", [])
        if not next_je:
            outcome.partial_insufficient_data_notes.append(
                "A subsequent-year engagement exists for this entity, but it has no validated Journal Entry data "
                "yet — the subsequent-period half of this test could not be run."
            )
        else:
            parsed_next = _parse_rows(next_je)
            # The next financial year starts the day after this one ends.
            next_fy_start = fy_end + timedelta(days=1)
            post_window_end = next_fy_start + timedelta(days=POST_PERIOD_WINDOW_DAYS - 1)

            for cand in candidates:
                cand_row = cand[0]
                match = _find_reversal(cand, parsed_next, after_date=fy_end, not_after=post_window_end)
                if match is None:
                    continue
                match_row, match_date = match
                key = (cand_row.file_id, cand_row.row_index, "subsequent")
                if key in matched_keys:
                    continue
                matched_keys.add(key)
                outcome.exceptions.append(ExceptionDraft(
                    label=wording.AUDIT_ATTENTION_REQUIRED,
                    area=AUDIT_AREA,
                    trigger_condition=(
                        f'Entry on "{cand[2]}" dated {cand[1].isoformat()} appears reversed by a matching entry '
                        f"dated {match_date.isoformat()}, in the subsequent-year engagement."
                    ),
                    explanation=(
                        f'A pre-year-end entry on account "{cand[2]}" dated {cand[1].isoformat()} appears to be '
                        f"reversed by an equal-and-opposite entry on the same account dated {match_date.isoformat()}"
                        f", found in the following year's engagement. This is a pattern match on account + amount "
                        f"only, across two separate engagements' data — it does not confirm the two entries are "
                        f"actually related, only that the original entry's period-matching warrants inspection."
                    ),
                    suggested_query=(
                        f'Please explain the business rationale for the entry on "{cand[2]}" dated '
                        f"{cand[1].isoformat()} and its apparent reversal shortly after year-end."
                    ),
                    risk_level="HIGH",
                    data_sources=[str(cand_row.file_id), str(match_row.file_id)],
                    threshold_used={
                        "post_period_window_days": POST_PERIOD_WINDOW_DAYS,
                        "amount_match_tolerance_paise": AMOUNT_MATCH_TOLERANCE_PAISE,
                        "half": "subsequent_period",
                    },
                    amount_paise=abs(cand[3]),
                ))

    return outcome
