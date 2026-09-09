"""
TAX-DEP-005 — Tax Depreciation Consistency Review.

Round 2 rename (post-approval review): renamed from "Tax Depreciation
Recompute & Book-vs-Tax Variance" to "Tax Depreciation Consistency
Review" — this rule uses the uploaded tax depreciation rate as given
and does NOT independently establish the correct Appendix I block/rate
for an asset, so "Recompute" overstated what it actually does. It is a
consistency check between the recorded rate/WDV figures and what those
same figures imply, not a from-first-principles tax depreciation
engine. The underlying logic, thresholds, and Limitation are unchanged
by this rename — see below.

Legal provision: Section 32, Income-tax Act, 1961, read with Rule 5 and
Appendix I (block-of-asset depreciation). An asset put to use for less
than 180 days in the financial year is restricted to half the
applicable rate for that year's additions. Rate table (current, common
blocks): residential buildings 5%, non-residential/factory buildings
10%, furniture & fittings 10%, plant & machinery (general) 15%,
computers/software 40%, motor vehicles (general use) 15%, motor
vehicles (hire business) 30%.

Verification: VERIFIED (old Act, 1961) — primary source: "Depreciation
Rates" and Section 32, incometaxindia.gov.in, both fetched directly
(see documentation/stage10_tax_rule_catalogue_proposal.md, TAX-DEP-005).
New Act 2025 forward reference (UNVERIFIED, non-gating): Section 33 —
cross-checked across two independent sources for the section number and
retention of the 180-day rule, but not itself primary-confirmed; never
used to decide executability.

FinSight Analytical Test — a FinSight-designed recompute, not itself a
figure the Act specifies (the RATE TABLE and 180-day rule are the Act's
own; the specific recompute-and-compare mechanism is FinSight's):
recomputes each Fixed Asset row's expected tax depreciation from its
own recorded `tax_depreciation_rate` (FinSight does NOT independently
verify the recorded rate against the block-name rate table above — see
Limitation), applying the 180-day half-rate rule to the year's
additions via `date_put_to_use`, and flags a variance against the
recorded `closing_wdv_paise` beyond a small FinSight tolerance.

Limitation: (1) FinSight trusts the uploaded `tax_block_of_asset` and
`tax_depreciation_rate` values — it does not cross-check that the rate
recorded actually matches the standard rate for the stated block, so a
mapping error at upload time will produce a wrong "expected" figure
without FinSight detecting the root cause. (2) Deletions are netted
out of the block before computing depreciation on the remaining
balance; FinSight does not separately compute depreciation on an asset
disposed of mid-year. (3) The half-rate 180-day rule is applied only to
the year's additions, not retroactively re-checked for prior-year
assets. This rule never states a depreciation claim is incorrect —
only that the recomputed and recorded figures diverge beyond a small
tolerance, warranting review.

Insufficient data: no validated Fixed Assets Register data at all for
this engagement, or the engagement's financial year cannot be parsed.
"""
from __future__ import annotations

from datetime import date

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.period_utils import days_held_in_period, financial_year_bounds
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-DEP-005"
TOPIC = "Tax Depreciation Consistency Review"
PROVISION_REFERENCE = "Section 32, Income-tax Act, 1961, read with Rule 5 and Appendix I"

FULL_YEAR_HALF_RATE_DAYS = 180  # the Act's own figure
VARIANCE_TOLERANCE_PAISE = 10_000  # ~₹100 — a FinSight rounding tolerance, not statutory


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    asset_rows = dataset.get("FIXED_ASSETS", [])
    if not asset_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Fixed Assets Register data is available for this engagement."
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
    era = describe_act_era(engagement.financial_year)

    for row in asset_rows:
        v = row.values
        block = (v.get("tax_block_of_asset") or "").strip()
        rate = v.get("tax_depreciation_rate")
        opening_wdv = v.get("opening_wdv_paise")
        closing_wdv = v.get("closing_wdv_paise")
        additions = v.get("additions_paise") or 0
        deletions = v.get("deletions_paise") or 0

        if not block or rate is None or opening_wdv is None or closing_wdv is None:
            outcome.partial_insufficient_data_notes.append(
                f"Fixed Assets row (file {row.file_id}, row {row.row_index + 1}): missing Tax Block of Asset, "
                f"Tax Depreciation Rate, Opening WDV, or Closing WDV — could not be included in the recompute."
            )
            continue

        outcome.evaluated_count += 1
        base_for_dep = max(opening_wdv - deletions, 0)
        opening_dep = base_for_dep * rate / 100.0

        additions_half_year = False
        raw_date = v.get("date_put_to_use")
        if raw_date:
            try:
                put_to_use = date.fromisoformat(raw_date)
                days_held = days_held_in_period(put_to_use, fy_start, fy_end)
                additions_half_year = fy_start <= put_to_use <= fy_end and days_held < FULL_YEAR_HALF_RATE_DAYS
            except ValueError:
                pass
        additions_dep = additions * rate / 100.0 * (0.5 if additions_half_year else 1.0)

        expected_dep = round(opening_dep + additions_dep)
        expected_closing = opening_wdv + additions - deletions - expected_dep
        variance = closing_wdv - expected_closing

        if abs(variance) <= VARIANCE_TOLERANCE_PAISE:
            continue

        asset_label = v.get("asset_description") or block or f"row {row.row_index + 1}"
        half_rate_note = (
            "applying the half-rate rule to this year's additions" if additions_half_year else "at the full rate"
        )
        outcome.exceptions.append(ExceptionDraft(
            label=wording.TAX_REVIEW_REQUIRED,
            area=TOPIC,
            trigger_condition=(
                f'Asset "{asset_label}" (block: {block}, rate: {rate}%): recomputed expected closing WDV of '
                f"{paise_to_display(expected_closing)} differs from the recorded closing WDV of "
                f"{paise_to_display(closing_wdv)} by {paise_to_display(abs(variance))}."
            ),
            explanation=(
                f'{era}. Section 32 allows depreciation per the block-of-asset rate table, with a half-rate '
                f'restriction for additions put to use for less than 180 days in the year. FinSight recomputed '
                f'expected depreciation for "{asset_label}" using its own recorded rate ({rate}%) — '
                f"{half_rate_note} "
                f"— giving an expected closing WDV of {paise_to_display(expected_closing)} against a recorded "
                f"closing WDV of {paise_to_display(closing_wdv)}. FinSight does not independently verify that "
                f"{rate}% is the correct rate for the {block} block, nor separately compute depreciation on "
                f"disposed assets — this variance may reflect a data entry difference rather than an actual "
                f"claim error. This is a potential issue for professional review, not a confirmed error."
            ),
            suggested_query=(
                f'Please confirm the tax block classification, depreciation rate, and closing WDV computation for '
                f'"{asset_label}", and explain the variance shown.'
            ),
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "variance_tolerance_paise": VARIANCE_TOLERANCE_PAISE,
                "threshold_is_statutory": False,
                "statutory_source": PROVISION_REFERENCE,
                "recorded_rate_independently_verified": False,
                "additions_half_year_rule_applied": additions_half_year,
                "expected_closing_wdv_paise": expected_closing,
                "recorded_closing_wdv_paise": closing_wdv,
                "variance_paise": variance,
            },
            amount_paise=abs(variance),
        ))

    return outcome
