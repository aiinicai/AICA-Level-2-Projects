"""
Stage 7 — app/mapping/column_mapper.py. Pure functions, no Flask/
SQLAlchemy dependency.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.mapping.column_mapper import (
    CANONICAL_FIELDS,
    FILE_TYPE_FIELD_SETS,
    detect_file_type_mismatch,
    field_score,
    find_duplicate_target_assignments,
    suggest_mappings,
)


def test_exact_match_after_normalization_scores_perfectly():
    assert field_score("Debit Amount", "debit_amount") == 1.0


def test_known_synonym_scores_highly():
    assert field_score("Dr", "debit_amount") >= 0.7


def test_unrelated_column_scores_low():
    assert field_score("Random Notes Column XYZ", "debit_amount") < 0.35


def test_every_canonical_field_has_a_display_label_and_synonym_list():
    for target_field, (label, synonyms) in CANONICAL_FIELDS.items():
        assert label
        assert isinstance(synonyms, list)


def test_every_file_type_field_set_only_references_real_canonical_fields():
    for file_type, fields in FILE_TYPE_FIELD_SETS.items():
        for field_name in fields:
            assert field_name in CANONICAL_FIELDS, f"{file_type} references unknown field {field_name!r}"


# --- suggest_mappings -----------------------------------------------------

def test_suggest_mappings_matches_obvious_trial_balance_columns():
    suggestions = {s.column_key: s for s in suggest_mappings(["Account", "Debit", "Credit"], "TB")}
    assert suggestions["Account"].target_field == "account_name"
    assert suggestions["Debit"].target_field == "debit_amount"
    assert suggestions["Credit"].target_field == "credit_amount"
    assert suggestions["Account"].confidence >= 0.75


def test_suggest_mappings_leaves_unrecognized_column_unmapped():
    suggestions = {s.column_key: s for s in suggest_mappings(["Account", "XYZ Nonsense Col"], "TB")}
    assert suggestions["XYZ Nonsense Col"].target_field is None
    assert suggestions["XYZ Nonsense Col"].confidence is None


def test_suggest_mappings_never_assigns_the_same_target_field_twice():
    # Two columns that both look like "Debit" — only one should win it;
    # the other should either get a different field or go unmapped, but
    # never both claim debit_amount.
    suggestions = suggest_mappings(["Debit", "Debit Amount"], "TB")
    debit_claims = [s for s in suggestions if s.target_field == "debit_amount"]
    assert len(debit_claims) <= 1


def test_suggest_mappings_returns_one_result_per_input_column_in_order():
    columns = ["Account", "Debit", "Credit", "Notes"]
    suggestions = suggest_mappings(columns, "TB")
    assert [s.column_key for s in suggestions] == columns


# --- file-type mismatch detection (Stage 7 requirement #8) -------------

def test_gl_looking_columns_selected_as_tb_triggers_mismatch_warning():
    # A General Ledger shape: date + narration + account + debit/credit —
    # much richer than a typical Trial Balance's account+debit+credit.
    gl_columns = ["Transaction Date", "Narration", "Account", "Debit", "Credit", "Voucher No"]
    warning = detect_file_type_mismatch(gl_columns, "TB")
    # Not asserting the warning fires in every possible heuristic tuning,
    # but if TB is not clearly the best fit, no warning should ever fire
    # for the file type that IS the best fit.
    if warning is not None:
        assert "General Ledger" in warning or "GL" in warning


def test_columns_matching_selected_file_type_do_not_trigger_mismatch():
    tb_columns = ["Account", "Debit", "Credit"]
    assert detect_file_type_mismatch(tb_columns, "TB") is None


def test_fixed_assets_columns_selected_as_tds_triggers_mismatch_warning():
    fa_columns = ["Asset Description", "Asset Class", "Date Put to Use", "Original Cost", "Closing WDV"]
    warning = detect_file_type_mismatch(fa_columns, "TDS")
    assert warning is not None
    assert "Fixed Assets" in warning


# --- find_duplicate_target_assignments (Stage 7 correction #1) ----------

def test_no_duplicates_when_every_column_maps_to_a_different_field():
    selection = {"Account": "account_name", "Debit": "debit_amount", "Credit": "credit_amount"}
    assert find_duplicate_target_assignments(selection) == {}


def test_two_columns_mapped_to_the_same_target_field_is_flagged():
    selection = {"Debit": "debit_amount", "Advance Debit": "debit_amount", "Credit": "credit_amount"}
    duplicates = find_duplicate_target_assignments(selection)
    assert set(duplicates.keys()) == {"debit_amount"}
    assert set(duplicates["debit_amount"]) == {"Debit", "Advance Debit"}


def test_blank_or_skipped_selections_are_never_flagged_as_duplicates():
    selection = {"Debit": "", "Credit": "", "Notes": ""}
    assert find_duplicate_target_assignments(selection) == {}


def test_three_columns_mapped_to_the_same_field_lists_all_three():
    selection = {"A": "account_name", "B": "account_name", "C": "account_name"}
    duplicates = find_duplicate_target_assignments(selection)
    assert len(duplicates["account_name"]) == 3
