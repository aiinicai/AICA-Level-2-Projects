"""
Detection logic shared by more than one rule module — kept in one place
per Blueprint Section 1.1 ("shared detection logic is centralized
once... not duplicated"). Despite living under `app/rules/accounting/`,
several of these functions are explicitly cross-module: this is exactly
where AS18-RPT-009 (Accounting) and AUD-RPT-006 (Audit, Stage 9) both
get their related-party detection from, and where AS29-PROV-010
(Accounting) and AUD-EST-009 (Audit, Stage 9) both get their account-
movement detection from — one detector, two interpretive layers on top,
per Section 1.1. The module stays at this path (not moved to a
module-neutral location) to avoid an import-path change across every
already-tested Accounting rule for no functional benefit — Python does
not enforce module boundaries by directory name, and nothing here is
Accounting-specific in its own logic.
"""
from __future__ import annotations

import difflib
import re
from collections import defaultdict

from app.rules.period_utils import next_financial_year, prior_financial_year
from app.services import dataset_service, engagement_service

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", (text or "").strip().lower()).strip()


def find_prior_year_dataset(engagement) -> dict[str, list] | None:
    """The immediately preceding engagement for the SAME entity (exact
    name match — see engagement_service.find_engagement_by_entity_and_year's
    docstring), if one exists and has any validated data of its own.
    Returns None (not an empty dict) when no such engagement exists at
    all, so callers can distinguish "no prior engagement" from "prior
    engagement exists but has no validated data of the relevant type."""
    prior_fy = prior_financial_year(engagement.financial_year)
    if prior_fy is None:
        return None
    prior_engagement = engagement_service.find_engagement_by_entity_and_year(
        engagement.entity_name, prior_fy
    )
    if prior_engagement is None:
        return None
    return dataset_service.load_engagement_dataset(prior_engagement.engagement_id)


def find_next_year_dataset(engagement) -> dict[str, list] | None:
    """Mirror of find_prior_year_dataset() above, looking forward one
    engagement instead of back — added in Stage 9 for AUD-SUB-007
    (subsequent-period reversal detection). Same None-vs-empty-dict
    distinction: None means no next-year engagement exists at all (the
    normal case — an audit is usually performed before next year's
    engagement is ever created in FinSight), an empty dict means one
    exists but has no validated data of the relevant type yet."""
    next_fy = next_financial_year(engagement.financial_year)
    if next_fy is None:
        return None
    next_engagement = engagement_service.find_engagement_by_entity_and_year(
        engagement.entity_name, next_fy
    )
    if next_engagement is None:
        return None
    return dataset_service.load_engagement_dataset(next_engagement.engagement_id)


# A deliberately coarse, explicitly-labeled text heuristic — same class
# of check as GEN-PPI-012's prior-period-item keyword match (already
# approved in the blueprint as "a text heuristic, not a determination").
# No related-party master list/flag exists anywhere in the approved
# schema, so this is the only signal available from transactional data
# alone: does a party's name contain a common related-party keyword, or
# closely resemble the engagement's own entity name (suggestive of a
# group/promoter entity)?
_RELATED_PARTY_KEYWORDS = (
    "director", "promoter", "relative", "holding", "subsidiary",
    "associate company", "group company", "wife of", "son of", "huf",
)
_NAME_SIMILARITY_THRESHOLD = 0.6


ROLL_FORWARD_TOLERANCE_PAISE = 100  # ~₹1 — absorbs rounding only, not a materiality judgment

_ROLL_FORWARD_FIELDS = (
    "opening_wdv_paise", "additions_paise", "deletions_paise",
    "book_depreciation_amount_paise", "closing_wdv_paise",
)


def roll_forward_fields_present(values: dict) -> bool:
    """True only if every field `reconcile_asset_roll_forward()` needs is
    present (not None) on this row's mapped values — the precondition
    check AS10-FA-001/AS26-INT-011 use before attempting the arithmetic
    check at all."""
    return all(values.get(f) is not None for f in _ROLL_FORWARD_FIELDS)


def reconcile_asset_roll_forward(
    opening_wdv_paise: int, additions_paise: int, deletions_paise: int,
    depreciation_amount_paise: int, closing_wdv_paise: int,
) -> int:
    """A method-agnostic arithmetic identity check — shared by
    AS10-FA-001 (tangible fixed assets) and AS26-INT-011 (intangible
    assets): opening WDV + additions - deletions - recorded
    depreciation/amortization should equal closing WDV, REGARDLESS of
    which depreciation method (straight-line, WDV, units-of-production,
    or anything else) actually produced the recorded depreciation
    figure. Returns the signed difference in paise (implied closing
    minus reported closing) — a nonzero result means the entity's own
    reported roll-forward numbers don't tie out arithmetically; it is
    NOT a judgment on which method was used or whether that method is
    appropriate, and it never assumes straight-line (Stage 8 Round 2
    correction #3/#4 — the prior variance-against-a-straight-line-
    estimate design produced false positives for WDV/units-of-
    production entities and has been replaced by this check)."""
    implied_closing = opening_wdv_paise + additions_paise - deletions_paise - depreciation_amount_paise
    return implied_closing - closing_wdv_paise


def detect_related_party_candidates(dataset: dict[str, list], entity_name: str) -> list:
    """Scans every MappedRow with a `party_name` value across the whole
    dataset (any dataset_type) and returns the ones that match the
    coarse heuristic above. Each returned row is annotated with
    `_related_party_reason` (a short string explaining which signal
    matched) for use in the exception's trigger_condition text."""
    normalized_entity = _normalize(entity_name)
    candidates = []
    for rows in dataset.values():
        for row in rows:
            party_name = row.values.get("party_name")
            if not party_name:
                continue
            normalized_party = _normalize(party_name)
            reason = None
            for keyword in _RELATED_PARTY_KEYWORDS:
                if keyword in normalized_party:
                    reason = f'party name contains the keyword "{keyword}"'
                    break
            if reason is None and normalized_entity:
                similarity = difflib.SequenceMatcher(None, normalized_party, normalized_entity).ratio()
                if similarity >= _NAME_SIMILARITY_THRESHOLD:
                    reason = "party name closely resembles the engagement's own entity name"
            if reason is not None:
                row._related_party_reason = reason
                candidates.append(row)
    return candidates


_DEFAULT_MOVEMENT_LEDGER_TYPES = ("GL", "JE", "TB")


def net_balance_by_account(
    dataset: dict[str, list], keywords: tuple[str, ...],
    dataset_types: tuple[str, ...] = _DEFAULT_MOVEMENT_LEDGER_TYPES,
) -> dict[str, int]:
    """account_name -> net credit balance in paise (credit - debit),
    summed across every row of the given ledger dataset types whose
    account_name contains one of `keywords` (case-insensitive substring
    match). Generalized in Stage 9 from AS29-PROV-010's original
    provision-only version so AUD-EST-009 (Audit) can reuse the exact
    same mechanism with its own, broader estimate-related keyword list
    — one detector, two interpretive layers, per Section 1.1. A positive
    value is a credit balance carried on the books; this function does
    not itself judge whether that's correct or by how much it should
    have moved."""
    totals: dict[str, int] = defaultdict(int)
    for dataset_type in dataset_types:
        for row in dataset.get(dataset_type, []):
            account_name = (row.values.get("account_name") or "").strip()
            if not account_name or not any(k in account_name.lower() for k in keywords):
                continue
            debit = row.values.get("debit_amount") or 0
            credit = row.values.get("credit_amount") or 0
            totals[account_name] += credit - debit
    return totals


# Stage 9: `is_manual_entry`/`payment_mode` are both free-text canonical
# fields (app/mapping/column_mapper.py classifies neither as a date,
# amount, or rate field, so dataset_service coerces them to a plain
# stripped string, never a real boolean) — every audit rule that reads
# either field goes through one of these two small normalizers so "Yes"/
# "Y"/"TRUE"/"1"/"Manual" (or "Cash"/"CASH"/"cash payment") are all
# recognized consistently, in one place, rather than each rule module
# rolling its own truthy-string guess.
_TRUE_FLAG_VALUES = {"yes", "y", "true", "1", "manual", "manual entry", "manually posted"}


def is_flag_true(value) -> bool:
    return (value or "").strip().lower() in _TRUE_FLAG_VALUES


def is_cash_payment_mode(value) -> bool:
    return "cash" in (value or "").strip().lower()


# A FinSight default used only when an engagement's own Entity Profile
# hasn't set `overall_materiality` yet — never presented as a
# statutory/SA figure, always disclosed per-finding which source was
# actually used (see resolve_materiality_threshold_paise() below).
DEFAULT_MATERIALITY_FALLBACK_PAISE = 10_000_000  # ₹1,00,000


def resolve_materiality_threshold_paise(engagement, default_paise: int = DEFAULT_MATERIALITY_FALLBACK_PAISE) -> tuple[int, str]:
    """(threshold_paise, source_description) — prefers the engagement's
    own Entity Profile `overall_materiality` (an already-approved paise
    field, Blueprint Section 2.13) when set; falls back to a disclosed
    FinSight default otherwise. Every rule using this must include
    `source_description` in its finding text so a reviewer always knows
    which basis produced the threshold actually applied."""
    profile = engagement_service.get_entity_profile(engagement.engagement_id)
    if profile is not None and profile.overall_materiality:
        return profile.overall_materiality, "the engagement's own Overall Materiality (Entity Profile)"
    return default_paise, "a FinSight default analytical threshold (no Overall Materiality set in the Entity Profile)"


def reversal_movement_amount_and_pct(prior_closing_paise: int, current_net_movement_paise: int) -> tuple[int, float]:
    """A large NEGATIVE current-period movement (a net debit) against a
    positive prior-period closing (credit) balance looks like a
    reversal/utilization of whatever was carried forward. Returns
    (movement_amount_paise, movement_pct) — movement_amount is 0 when
    the current period moved the balance up or left it unchanged (only
    a reduction counts as a "reversal" for this detector's purpose);
    movement_pct is 0.0 when prior_closing_paise is 0 (nothing to
    express a percentage of). Shared by AS29-PROV-010 (Accounting) and
    AUD-EST-009 (Audit, Stage 9) — extracted from AS29-PROV-010's
    original inline calculation, behavior unchanged."""
    movement_amount = max(-current_net_movement_paise, 0)
    movement_pct = round(movement_amount / prior_closing_paise * 100, 1) if prior_closing_paise else 0.0
    return movement_amount, movement_pct
