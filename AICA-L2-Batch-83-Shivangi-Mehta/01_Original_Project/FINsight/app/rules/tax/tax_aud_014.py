"""
TAX-AUD-014 — Tax Audit Applicability / Turnover-Threshold Test.

Legal provision: Section 44AB, Income-tax Act, 1961. Business: audit
required if turnover/gross receipts EXCEED ₹1 crore, enhanced to ₹10
crore where CASH RECEIPTS do not exceed 5% of TOTAL RECEIPTS **AND**
CASH PAYMENTS do not exceed 5% of TOTAL PAYMENTS — two independent
conditions, tested separately (non-account-payee instruments count as
cash). Professionals: audit required if gross receipts EXCEED ₹50 lakh.
"Exceed" is strict — a figure exactly equal to a threshold does NOT
cross it (Round 3 correction, see below).

Round 3 correction (post-approval review) — two fixes:

  (a) CRITICAL — boundary operator. Every comparison in this rule
  previously used ">=" ("at or above"). Section 44AB's own text says a
  tax audit is required where turnover/gross receipts "exceed" a
  figure — a strict inequality. ₹1,00,00,000 exactly does NOT cross the
  ₹1 crore threshold; ₹1,00,00,001 does. Same for the ₹10 crore
  enhanced threshold and the ₹50 lakh professional threshold. Every
  `crosses_*` comparison below now uses ">" accordingly. (The 5%
  cash-percentage conditions are UNCHANGED — the Act's own text there
  is "does not exceed five per cent", so "<=5%" remains correct and
  was never part of this correction.)

  (b) Professional/Section 44ADA wording. `crosses_professional` being
  True must never read as if tax-audit applicability under Section
  44AB(b) were conclusively settled — FinSight cannot determine from
  existing data whether the assessee is a specified profession,
  whether Section 44ADA is being used, whether they have opted out, or
  whether the presumptive-income conditions are satisfied. The
  professional comparison is now its OWN finding (split out from the
  business comparison — previously both were folded into a single
  finding), labeled `wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED`
  ("Tax Audit Applicability — Review Required"), with its explanation
  explicitly stating FinSight cannot conclusively determine Section
  44ADA-related applicability from the current data. The ₹50 lakh and
  ₹75 lakh statutory figures are both retained in `threshold_used`,
  unchanged from Round 2 — the ₹75 lakh figure is still Section
  44ADA's own presumptive-scheme ceiling (Finance Act 2023, effective
  AY 2024-25), shown informationally only, never applied to
  `crosses_professional`. No new schema field was added for this.

Round 2 correction (post-approval review) — professional ₹75 lakh
figure, primary-verified: incometaxindia.gov.in's own Section 44AB
page (fetched directly) confirms clause (b) reads verbatim "carrying
on profession shall, if his gross receipts in profession exceed fifty
lakh rupees in any previous year" — **no ₹75 lakh variant exists
inside Section 44AB(b) itself.** The ₹75 lakh figure is real, but it
belongs to a DIFFERENT provision: a proviso to **Section 44ADA** (the
professional presumptive-taxation scheme), added by the Finance Act
2023 (effective 1 April 2024, i.e. AY 2024-25 onward), which
substitutes "seventy-five lakh rupees" for "fifty lakh rupees" in
44ADA's own eligibility ceiling where cash receipts do not exceed 5%
of total gross receipts (non-account-payee instruments count as cash).

Verification: VERIFIED (old Act, 1961) — primary source: Section 44AB,
incometaxindia.gov.in, full threshold text fetched directly (see
documentation/stage10_tax_rule_catalogue_proposal.md, TAX-AUD-014), for
the ₹1cr/₹10cr business and ₹50L professional figures used below.
Section 44ADA's ₹75L proviso is ALSO primary-verified (same fetch) —
see the Round 2 note above for why it is disclosed but never applied
to `crosses_professional`. New Act 2025 forward reference (UNVERIFIED,
non-gating): Section 63 — reported consistently across several
secondary sources but no primary text was reached; never used to
decide executability.

FinSight Analytical Test — a FinSight-designed heuristic screen for
Section 44AB, not itself a figure the Act specifies (the RUPEE
THRESHOLDS are the Act's own; the METHOD of computing turnover and cash
percentages from FinSight's data is FinSight's): computes turnover from
the Sales Register if present, else from GL/Trial Balance accounts
whose name suggests sales/revenue/turnover/income, else falls back to
the Entity Profile's manually-entered turnover figure (clearly
disclosed which source was used); computes cash-receipt and
cash-payment percentages SEPARATELY (a row's `credit_amount` is
treated as its receipt/inflow side, `debit_amount` as its
payment/outflow side, the same polarity convention TAX-CASH-001/002
use) across GL/Bank/Sales flows; the ₹10 crore enhanced business
threshold is applied only when BOTH the receipt-side and payment-side
conditions are independently satisfied and determinable — if either
side has no data to compute a percentage from, FinSight does NOT assume
that side's condition is satisfied, and falls back to the base ₹1 crore
threshold, disclosing which side was indeterminate; and evaluates the
business (₹1cr/₹10cr) and professional (₹50L) comparisons
INDEPENDENTLY — each becomes its own finding when crossed, since
FinSight's Entity Profile records entity_type (Company/LLP/Partnership/
Proprietorship/Other) but not a business-vs-profession classification,
so both are always computed even though only one will actually apply
to a given engagement.

Limitation: (1) FinSight cannot determine whether this engagement is a
"business" or a "specified profession" under Section 44ADA from
existing data — both comparisons are always computed, and the reviewer
must determine which applies (Decision 5 — no new field added for
this). (2) The ₹75 lakh figure is Section 44ADA's own presumptive-
scheme eligibility ceiling (primary-verified), not a Section 44AB(b)
audit-threshold enhancement — it is shown informationally only and
never changes `crosses_professional`. (3) The presumptive-scheme
opt-out/under-declaration trigger for audit applicability — which is
exactly where the 44ADA ₹75L figure could indirectly matter, and
exactly why the professional finding is labeled "Review Required"
rather than treated as a settled conclusion — is not evaluated. (4) If
no Sales/GL/TB revenue data is available, this rule falls back to the
Entity Profile's manually-entered `turnover` field, which may be stale
or for a different year than this engagement's transactional data —
the finding states clearly which source was used. (5) Same-transaction
double-counting across GL and Bank Statement data (if both are
uploaded for the same underlying cash movement) is not deduplicated —
FinSight has no reliable cross-source transaction-identity field to
detect this, so the receipt/payment totals may overstate true cash
flow when both sources cover the same period; this is disclosed, not
silently corrected. This rule never states that a tax audit is or is
not required — only that FinSight's computed figures suggest the
applicability warrants review.

Insufficient data: no validated Sales Register, General Ledger, Trial
Balance, or Bank Statement data at all, AND no Entity Profile turnover
figure set, for this engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import is_cash_payment_mode
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.tax.act_transition import describe_act_era
from app.services import engagement_service
from app.utils.currency import paise_to_display

RULE_ID = "TAX-AUD-014"
TOPIC = "Tax Audit Applicability / Turnover-Threshold Test"
PROVISION_REFERENCE = "Section 44AB, Income-tax Act, 1961"

BUSINESS_BASE_THRESHOLD_PAISE = 1_000_000_000        # ₹1 crore
BUSINESS_ENHANCED_THRESHOLD_PAISE = 10_000_000_000    # ₹10 crore
PROFESSIONAL_THRESHOLD_PAISE = 500_000_000            # ₹50 lakh — Section 44AB(b)'s own, unconditional figure
CASH_PERCENT_ENHANCED_LIMIT = 5.0                     # percent, the Act's own figure ("does not exceed" -> <=)

# Section 44ADA proviso (Finance Act 2023, effective 1 April 2024 / AY 2024-25 onward),
# primary-verified from incometaxindia.gov.in — the presumptive-scheme eligibility
# ceiling, NOT a Section 44AB(b) audit-threshold enhancement. Shown informationally in
# every professional finding; never used to compute `crosses_professional`.
PROFESSIONAL_44ADA_PRESUMPTIVE_ENHANCED_THRESHOLD_PAISE = 750_000_000  # ₹75 lakh
PROFESSIONAL_44ADA_PROVISION_REFERENCE = "Section 44ADA proviso (as inserted by the Finance Act, 2023), Income-tax Act, 1961"
PROFESSIONAL_44ADA_EFFECTIVE_FROM = "1 April 2024 (AY 2024-25 onward)"

_TURNOVER_KEYWORDS = ("sales", "revenue", "turnover", "income from operations")
_LEDGER_TYPES = ("GL", "TB")
_CASH_METRIC_DATASET_TYPES = ("GL", "BANK", "SALES")


def _compute_turnover_paise(dataset: dict[str, list], engagement) -> tuple[int, str]:
    sales_rows = dataset.get("SALES", [])
    if sales_rows:
        total = sum(
            (row.values.get("credit_amount") or row.values.get("debit_amount") or 0) for row in sales_rows
        )
        if total > 0:
            return total, "computed from the validated Sales Register"

    ledger_total = 0
    for dt in _LEDGER_TYPES:
        for row in dataset.get(dt, []):
            account_name = (row.values.get("account_name") or "").lower()
            if any(k in account_name for k in _TURNOVER_KEYWORDS):
                credit = row.values.get("credit_amount") or 0
                debit = row.values.get("debit_amount") or 0
                ledger_total += credit - debit
    if ledger_total > 0:
        return ledger_total, "computed from General Ledger/Trial Balance accounts matching a sales/revenue/turnover keyword"

    profile = engagement_service.get_entity_profile(engagement.engagement_id)
    if profile is not None and profile.turnover:
        return profile.turnover, "the Entity Profile's manually-entered turnover figure (not recomputed from this engagement's transactional data)"

    return 0, "not computable"


def _compute_receipt_payment_metrics(dataset: dict[str, list]) -> dict:
    """Separately aggregates the receipt side (`credit_amount`) and the
    payment side (`debit_amount`) of GL/Bank/Sales flows, and the
    cash-mode portion of each. Section 44AB's enhanced ₹10 crore
    business threshold requires TWO independent conditions — cash
    receipts ≤5% of total receipts AND cash payments ≤5% of total
    payments — never one blended percentage across both directions.
    Polarity: `credit_amount` = receipt/inflow, `debit_amount` =
    payment/outflow, the same convention TAX-CASH-001 (expenditure =
    debit) and TAX-CASH-002 (receipt = credit) already establish."""
    total_receipts = 0
    cash_receipts = 0
    total_payments = 0
    cash_payments = 0
    for dt in _CASH_METRIC_DATASET_TYPES:
        for row in dataset.get(dt, []):
            v = row.values
            cash = is_cash_payment_mode(v.get("payment_mode"))
            credit = v.get("credit_amount") or 0
            if credit > 0:
                total_receipts += credit
                if cash:
                    cash_receipts += credit
            debit = v.get("debit_amount") or 0
            if debit > 0:
                total_payments += debit
                if cash:
                    cash_payments += debit
    return {
        "total_receipts": total_receipts,
        "cash_receipts": cash_receipts,
        "total_payments": total_payments,
        "cash_payments": cash_payments,
    }


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    turnover_paise, turnover_source = _compute_turnover_paise(dataset, engagement)
    if turnover_source == "not computable":
        outcome.insufficient_data_reason = (
            "No validated Sales Register, General Ledger, or Trial Balance data with an identifiable turnover "
            "figure is available for this engagement, and no Entity Profile turnover figure has been set."
        )
        return outcome

    outcome.evaluated_count = 1

    metrics = _compute_receipt_payment_metrics(dataset)
    total_receipts = metrics["total_receipts"]
    cash_receipts = metrics["cash_receipts"]
    total_payments = metrics["total_payments"]
    cash_payments = metrics["cash_payments"]

    receipts_determinable = total_receipts > 0
    payments_determinable = total_payments > 0

    cash_receipt_percentage = (cash_receipts / total_receipts * 100.0) if receipts_determinable else None
    cash_payment_percentage = (cash_payments / total_payments * 100.0) if payments_determinable else None

    # Never assume a condition is satisfied when it cannot be determined —
    # both sides must be affirmatively computed AND at or under 5% ("does not
    # exceed" -> <=, unchanged by the Round 3 boundary correction below, which
    # is about the turnover thresholds, not this percentage condition).
    receipt_condition_satisfied = receipts_determinable and cash_receipt_percentage <= CASH_PERCENT_ENHANCED_LIMIT
    payment_condition_satisfied = payments_determinable and cash_payment_percentage <= CASH_PERCENT_ENHANCED_LIMIT
    enhanced_threshold_applied = receipt_condition_satisfied and payment_condition_satisfied

    indeterminate_sides = []
    if not receipts_determinable:
        indeterminate_sides.append("receipts")
    if not payments_determinable:
        indeterminate_sides.append("payments")

    if indeterminate_sides:
        cash_pct_note = (
            f"insufficient data to compute a cash-{'/'.join(indeterminate_sides)} percentage — the enhanced "
            f"₹10 crore business threshold is NOT assumed and the base ₹1 crore threshold is used"
        )
    else:
        cash_pct_note = (
            f"cash receipts at {cash_receipt_percentage:.1f}% of total receipts "
            f"({'at or under' if receipt_condition_satisfied else 'over'} the 5% limit) and cash payments at "
            f"{cash_payment_percentage:.1f}% of total payments "
            f"({'at or under' if payment_condition_satisfied else 'over'} the 5% limit)"
        )

    business_threshold = BUSINESS_ENHANCED_THRESHOLD_PAISE if enhanced_threshold_applied else BUSINESS_BASE_THRESHOLD_PAISE
    # Round 3 CRITICAL correction: strict "exceeds" (>), never "at or above" (>=).
    crosses_business = turnover_paise > business_threshold
    crosses_professional = turnover_paise > PROFESSIONAL_THRESHOLD_PAISE

    if not (crosses_business or crosses_professional):
        return outcome

    era = describe_act_era(engagement.financial_year)
    common_threshold_fields = {
        "cash_percent_enhanced_limit": CASH_PERCENT_ENHANCED_LIMIT,
        "computed_turnover_paise": turnover_paise,
        "turnover_source": turnover_source,
        "total_receipts": total_receipts,
        "cash_receipts": cash_receipts,
        "cash_receipt_percentage": round(cash_receipt_percentage, 2) if cash_receipt_percentage is not None else None,
        "total_payments": total_payments,
        "cash_payments": cash_payments,
        "cash_payment_percentage": round(cash_payment_percentage, 2) if cash_payment_percentage is not None else None,
        "receipt_condition_satisfied": receipt_condition_satisfied,
        "payment_condition_satisfied": payment_condition_satisfied,
        "enhanced_threshold_applied": enhanced_threshold_applied,
    }

    # --- Business (Section 44AB(a)) finding — independent of the professional one ---
    if crosses_business:
        outcome.exceptions.append(ExceptionDraft(
            label=wording.TAX_REVIEW_REQUIRED,
            area=TOPIC,
            trigger_condition=(
                f"Computed turnover of {paise_to_display(turnover_paise)} ({turnover_source}) EXCEEDS the "
                f"{'enhanced ₹10 crore' if business_threshold == BUSINESS_ENHANCED_THRESHOLD_PAISE else 'base ₹1 crore'} "
                f"Section 44AB business threshold."
            ),
            explanation=(
                f'{era}. Section 44AB requires a tax audit where BUSINESS turnover exceeds ₹1 crore (₹10 crore '
                f'only if cash receipts do not exceed 5% of total receipts AND cash payments do not exceed 5% of '
                f'total payments — two separate conditions, both required; a figure exactly equal to a threshold '
                f'does not exceed it). FinSight computed a turnover of {paise_to_display(turnover_paise)} '
                f"({turnover_source}), with {cash_pct_note}, which exceeds the "
                f"{'enhanced ₹10 crore' if business_threshold == BUSINESS_ENHANCED_THRESHOLD_PAISE else 'base ₹1 crore'} "
                f"limit. This does NOT establish that a tax audit is or is not required — entity-type-specific "
                f"carve-outs and prior-year audit history can affect the actual answer, and FinSight cannot "
                f"determine whether this engagement is actually a business (as opposed to a specified profession, "
                f"see the separate professional-threshold finding if one is also present) from existing data."
            ),
            suggested_query=(
                "Please confirm this engagement's actual turnover figure, whether it is properly classified as a "
                "business for Section 44AB purposes, and whether any carve-out or prior-year audit history "
                "affects audit applicability."
            ),
            risk_level="HIGH",
            data_sources=[],
            threshold_used={
                **common_threshold_fields,
                "business_base_threshold_paise": BUSINESS_BASE_THRESHOLD_PAISE,
                "business_enhanced_threshold_paise": BUSINESS_ENHANCED_THRESHOLD_PAISE,
                "threshold_is_statutory": True,
                "statutory_source": PROVISION_REFERENCE,
                "threshold_comparison_operator": "strictly greater than (exceeds)",
                "crosses_business_threshold": crosses_business,
            },
            amount_paise=turnover_paise,
        ))

    # --- Professional (Section 44AB(b)) finding — independent, distinct label ---
    if crosses_professional:
        outcome.exceptions.append(ExceptionDraft(
            label=wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED,
            area=TOPIC,
            trigger_condition=(
                f"Computed turnover/gross receipts of {paise_to_display(turnover_paise)} ({turnover_source}) "
                f"EXCEEDS the ₹50 lakh Section 44AB(b) professional gross-receipts threshold."
            ),
            explanation=(
                f'{era}. Section 44AB(b) requires a tax audit where a PROFESSION\'s gross receipts exceed ₹50 '
                f'lakh (a figure exactly equal to ₹50 lakh does not exceed it). FinSight computed a turnover/'
                f"gross receipts figure of {paise_to_display(turnover_paise)} ({turnover_source}), which exceeds "
                f"that ₹50 lakh figure. A ₹75 lakh figure is sometimes cited alongside this threshold, but it is "
                f"Section 44ADA's own presumptive-scheme eligibility ceiling (Finance Act 2023, effective AY "
                f"2024-25, conditional on cash receipts not exceeding 5% of total receipts) — a different "
                f"provision, shown informationally only, never applied to this ₹50 lakh comparison. FinSight does "
                f"NOT have enough data to determine Section 44ADA-related applicability — it has no record of "
                f"whether this engagement is a specified profession, whether Section 44ADA is being used, whether "
                f"the assessee has opted out, or whether the presumptive-income conditions are satisfied. This is "
                f"a candidate for professional review, not a settled determination that tax audit applicability "
                f"under Section 44AB(b) has been established."
            ),
            suggested_query=(
                "Please confirm whether this engagement is a specified profession for Section 44AB(b)/44ADA "
                "purposes, whether Section 44ADA presumptive taxation is being used or has been opted out of, "
                "whether the presumptive-income conditions are satisfied, and the actual gross receipts figure."
            ),
            risk_level="HIGH",
            data_sources=[],
            threshold_used={
                **common_threshold_fields,
                "professional_threshold_paise": PROFESSIONAL_THRESHOLD_PAISE,
                "professional_44ada_presumptive_enhanced_threshold_paise": PROFESSIONAL_44ADA_PRESUMPTIVE_ENHANCED_THRESHOLD_PAISE,
                "professional_44ada_cash_percent_limit": CASH_PERCENT_ENHANCED_LIMIT,
                "professional_44ada_provision": PROFESSIONAL_44ADA_PROVISION_REFERENCE,
                "professional_44ada_effective_from": PROFESSIONAL_44ADA_EFFECTIVE_FROM,
                "professional_44ada_threshold_is_statutory": True,
                "professional_44ada_applied_to_crosses_professional": False,  # informational only, see docstring
                "threshold_is_statutory": True,
                "statutory_source": PROVISION_REFERENCE,
                "threshold_comparison_operator": "strictly greater than (exceeds)",
                "crosses_professional_threshold": crosses_professional,
                "section_44ada_applicability_conclusively_determined": False,
            },
            amount_paise=turnover_paise,
        ))

    return outcome
