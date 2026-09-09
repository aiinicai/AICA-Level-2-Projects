"""
Act-transition helpers (Stage 10, Decision 1 — approved).

India's Income-tax Act, 1961 is repealed effective 1 April 2026 by the
Income-tax Act, 2025 (Act No. 30 of 2025) — confirmed via CBDT's own
"FAQs on Interplay and Transition to the Income-tax Act, 2025"
(incometaxindia.gov.in) during the Stage 10 research pass (see
documentation/stage10_tax_rule_catalogue_proposal.md, Section 0).

Approved V1 scope: every executable Tax rule is verified and gated
against the OLD Act (1961) only. FY 2025-26 (Assessment Year 2026-27)
and all prior years are governed by the 1961 Act; FY 2026-27 (Tax Year
2026-27) onward is governed by the 2025 Act, whose section numbering
was NOT reliably verifiable during Stage 10's research (conflicting or
single-source-only claims for nearly every provision). Per your
explicit instruction, an unverified 2025 Act reference must never make
a rule executable — so this module provides a single, shared
engagement-level gate: `is_old_act_fy()`. `app/services/tax_review_
service.py` calls this ONCE per review (not per rule) before running
any Tax rule at all, since every currently-executable rule shares the
same old-Act-only verification scope; there is no per-rule case yet
where one rule is new-Act-verified and another isn't.

This module intentionally has no knowledge of the New Act 2025's
section numbers — those are carried, unverified, as labeled prose on
each `TaxRule.description` (Stage 10 plan Section 3/7), never here,
and never used to decide executability.
"""
from __future__ import annotations

from datetime import date

from app.rules.period_utils import financial_year_bounds

# The last day the Income-tax Act, 1961 governs — confirmed via CBDT's
# transition FAQ (primary source, see the catalogue proposal doc).
_OLD_ACT_LAST_DAY = date(2026, 3, 31)


def is_old_act_fy(financial_year: str) -> bool:
    """True if `financial_year` ("2025-26" etc.) ends on or before
    31 March 2026 — i.e. is governed by the Income-tax Act, 1961, the
    only regime FinSight's Tax rules are currently verified against.
    False for an unparseable financial_year (same "insufficient data,
    not a crash" defensiveness as period_utils.py's own helpers) and
    for FY 2026-27 onward, which falls under the (unverified) Income-tax
    Act, 2025."""
    bounds = financial_year_bounds(financial_year)
    if bounds is None:
        return False
    _fy_start, fy_end = bounds
    return fy_end <= _OLD_ACT_LAST_DAY


def describe_act_era(financial_year: str) -> str:
    """A short, reusable citation string for finding/explanation text,
    e.g. "FY 2025-26 (Assessment Year 2026-27) — Income-tax Act, 1961".
    Only ever called after is_old_act_fy() has already confirmed True
    (tax_review_service refuses to run any rule otherwise), so this
    does not itself branch on era — it exists so every rule's finding
    text states the FY/AY/Act consistently, in one place, rather than
    each rule module formatting this string on its own."""
    bounds = financial_year_bounds(financial_year)
    if bounds is None:
        return f'FY {financial_year} (financial year could not be parsed)'
    _fy_start, fy_end = bounds
    ay_start = fy_end.year
    ay_end_2digit = (ay_start + 1) % 100
    return f"FY {financial_year} (Assessment Year {ay_start}-{ay_end_2digit:02d}) — Income-tax Act, 1961"
