"""
Stage 5 — app/services/applicability_engine.py.

Pure functions, no SQLAlchemy dependency for the logic itself (though
importing anything under `app.*` still runs `app/__init__.py` first,
which needs Flask and, transitively, SQLAlchemy).

Stage 5 round-2 corrections covered here:
1. Audit Review is decoupled from `statutory_audit_applicable` — it is
   always-on, like Accounting Standards / Income Tax Review, and must
   never be suppressed just because statutory audit is not applicable.
2. `entity_profile_input()` / `suggestion_display()` — the three-line
   Entity Profile Input / System Suggestion / Professional Confirmation
   display wording.

Ran for real under `pytest` in the delivery sandbox — see the Stage 5
delivery notes for the sandbox's real-Flask + shimmed-SQLAlchemy setup.
Also runs unmodified once real dependencies are installed per
requirements.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.applicability_engine import (
    AREAS,
    NAV_HIDE,
    NAV_REVIEW_REQUIRED,
    NAV_SHOW,
    compute_sebi_nav_state,
    entity_profile_input,
    suggest_applicability,
    suggestion_display,
)

LISTED_IND_AS_FACTS = {
    "accounting_framework": "IND_AS",
    "statutory_audit_applicable": True,
    "tax_audit_status": "APPLICABLE",
    "is_listed": True,
}

UNLISTED_AS_FACTS = {
    "accounting_framework": "AS",
    "statutory_audit_applicable": False,
    "tax_audit_status": "NOT_APPLICABLE",
    "is_listed": False,
}


def test_areas_has_exactly_six_entries_matching_original_spec_example():
    assert len(AREAS) == 6
    assert set(AREAS) == {
        "Accounting Standards", "Ind AS", "Audit Review",
        "Income Tax Review", "Tax Audit Review", "SEBI/LODR",
    }


def test_every_area_has_a_suggester_and_returns_a_non_empty_reason():
    result = suggest_applicability(LISTED_IND_AS_FACTS)
    assert set(result.keys()) == set(AREAS)
    for status, reason in result.values():
        assert status in ("YES", "NO", "REVIEW_REQUIRED")
        assert isinstance(reason, str) and reason.strip()


def test_listed_ind_as_entity_suggestions():
    result = suggest_applicability(LISTED_IND_AS_FACTS)
    assert result["SEBI/LODR"][0] == "YES"
    assert result["Ind AS"][0] == "YES"
    assert result["Audit Review"][0] == "YES"
    assert result["Tax Audit Review"][0] == "YES"
    assert result["Accounting Standards"][0] == "YES"  # always-on
    assert result["Income Tax Review"][0] == "YES"  # always-on


def test_unlisted_as_entity_suggestions_are_the_opposite():
    result = suggest_applicability(UNLISTED_AS_FACTS)
    assert result["SEBI/LODR"][0] == "NO"
    assert result["Ind AS"][0] == "NO"
    assert result["Tax Audit Review"][0] == "NO"
    # Audit Review is NOT the opposite here — see round-2 correction #1
    # and test_audit_review_is_never_disabled_by_statutory_audit_fact below.
    assert result["Audit Review"][0] == "YES"


def test_missing_facts_yield_review_required_not_a_guess():
    result = suggest_applicability({})
    for area in ("Ind AS", "Tax Audit Review", "SEBI/LODR"):
        assert result[area][0] == "REVIEW_REQUIRED"
    # Audit Review is always-on, even with a fully empty profile — it is
    # not derived from any single fact, so there is nothing to be
    # "REVIEW_REQUIRED" about.
    assert result["Audit Review"][0] == "YES"


def test_reasons_reference_entity_profile_never_a_statutory_threshold():
    """Design guardrail: the suggestion engine must never encode a
    statutory numeric threshold (turnover limits etc.) — those haven't
    been through the Section 5/6 verification register. Every
    non-trivial suggestion's reason should attribute itself to the
    Entity Profile, not to an invented rule."""
    result = suggest_applicability(LISTED_IND_AS_FACTS)
    for area in ("Ind AS", "Audit Review", "Tax Audit Review", "SEBI/LODR"):
        assert "Entity profile" in result[area][1]


def test_raw_int_booleans_behave_identically_to_real_bool():
    """Regression: a value fetched fresh from SQLite can arrive as a
    plain 0/1 int rather than a real Python bool (real SQLAlchemy's
    Boolean type coerces this correctly on read, but the suggestion
    logic must not silently depend on that — see the Stage 5 delivery
    notes for the bug this guards against)."""
    facts_with_ints = {**LISTED_IND_AS_FACTS, "is_listed": 1, "statutory_audit_applicable": 1}
    result = suggest_applicability(facts_with_ints)
    assert result["SEBI/LODR"][0] == "YES"
    assert result["Audit Review"][0] == "YES"
    # The int is still normalized correctly in the (informational-only)
    # reason text, even though it no longer drives the status itself.
    assert "Statutory Audit Applicable = Yes" in result["Audit Review"][1]


# --- Round-2 correction #1: Audit Review vs Statutory Audit Applicability --

def test_audit_review_is_never_disabled_by_statutory_audit_fact():
    """The core round-2 correction: Statutory Audit Applicability (an
    entity fact) and Audit Review (FinSight's own analytical capability)
    are different concepts. Audit Review must stay YES regardless of
    what statutory_audit_applicable says — including when it's False,
    None (not yet recorded), or missing from facts entirely."""
    for statutory_audit_value in (True, False, None, "not-a-bool-at-all"):
        facts = {**LISTED_IND_AS_FACTS, "statutory_audit_applicable": statutory_audit_value}
        assert suggest_applicability(facts)["Audit Review"][0] == "YES"

    facts_without_the_field_at_all = {k: v for k, v in LISTED_IND_AS_FACTS.items() if k != "statutory_audit_applicable"}
    assert suggest_applicability(facts_without_the_field_at_all)["Audit Review"][0] == "YES"


def test_audit_review_reason_still_surfaces_the_statutory_audit_fact_as_context():
    """The statutory-audit fact isn't discarded — it's shown, but
    explicitly labeled as context that does not determine the
    suggestion, so a reviewer can still see it without it looking like
    the driver of Audit Review's applicability."""
    reason = suggest_applicability(UNLISTED_AS_FACTS)["Audit Review"][1]
    assert "Statutory Audit Applicable = No" in reason
    assert "does not determine this suggestion" in reason


# --- Round-2 correction #2: Entity Profile Input / System Suggestion labels

def test_entity_profile_input_returns_none_for_the_three_non_single_fact_areas():
    facts = LISTED_IND_AS_FACTS
    assert entity_profile_input("Accounting Standards", facts) is None
    assert entity_profile_input("Income Tax Review", facts) is None
    # Audit Review's driving concept was deliberately decoupled from any
    # single Entity Profile fact by round-2 correction #1.
    assert entity_profile_input("Audit Review", facts) is None


def test_entity_profile_input_labels_match_the_correction_example():
    # The round-2 correction's own example: "Listed Entity: No".
    assert entity_profile_input("SEBI/LODR", UNLISTED_AS_FACTS) == "Listed Entity: No"
    assert entity_profile_input("SEBI/LODR", LISTED_IND_AS_FACTS) == "Listed Entity: Yes"
    assert entity_profile_input("SEBI/LODR", {}) == "Listed Entity: Not yet recorded"

    assert entity_profile_input("Ind AS", LISTED_IND_AS_FACTS) == "Accounting Framework: Ind AS"
    assert entity_profile_input("Ind AS", UNLISTED_AS_FACTS) == "Accounting Framework: AS"
    assert entity_profile_input("Ind AS", {}) == "Accounting Framework: Not yet recorded"

    assert entity_profile_input("Tax Audit Review", LISTED_IND_AS_FACTS) == "Tax Audit Status: Applicable"
    assert entity_profile_input("Tax Audit Review", {}) == "Tax Audit Status: Not yet recorded"


def test_suggestion_display_wording_matches_the_correction_example():
    # The round-2 correction's own example:
    # "System Suggestion: SEBI/LODR — Not Suggested based on current profile"
    assert suggestion_display("SEBI/LODR", "NO") == "SEBI/LODR — Not Suggested based on current profile"
    assert suggestion_display("SEBI/LODR", "YES") == "SEBI/LODR — Suggested based on current profile"
    assert suggestion_display("Ind AS", "REVIEW_REQUIRED") == "Ind AS — Review Required — profile information incomplete"
    # Never renders the bare enum value (YES/NO) on its own — always full,
    # non-definitive wording instead.
    assert "SEBI/LODR — YES" != suggestion_display("SEBI/LODR", "YES")
    assert "SEBI/LODR — NO" != suggestion_display("SEBI/LODR", "NO")


# --- SEBI nav state --------------------------------------------------------

def test_nav_state_hide_when_unlisted():
    assert compute_sebi_nav_state(False, None) == NAV_HIDE
    assert compute_sebi_nav_state(False, "REQUIRES_FURTHER_REVIEW") == NAV_HIDE  # unlisted always wins


def test_nav_state_hide_when_explicitly_confirmed_not_applicable():
    assert compute_sebi_nav_state(True, "NOT_APPLICABLE") == NAV_HIDE


def test_nav_state_show_only_when_listed_and_confirmed_applicable():
    assert compute_sebi_nav_state(True, "APPLICABLE") == NAV_SHOW


def test_nav_state_review_required_when_not_yet_confirmed():
    assert compute_sebi_nav_state(True, None) == NAV_REVIEW_REQUIRED
    assert compute_sebi_nav_state(None, None) == NAV_REVIEW_REQUIRED
    assert compute_sebi_nav_state(True, "REQUIRES_FURTHER_REVIEW") == NAV_REVIEW_REQUIRED


def test_nav_state_raw_int_booleans_behave_identically_to_real_bool():
    assert compute_sebi_nav_state(1, "APPLICABLE") == NAV_SHOW
    assert compute_sebi_nav_state(0, None) == NAV_HIDE
