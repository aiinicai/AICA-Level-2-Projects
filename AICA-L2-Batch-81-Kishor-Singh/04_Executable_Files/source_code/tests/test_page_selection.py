"""Tests for core.page_selection: the page-expression parser used by every engine."""
import pytest

from core.page_selection import PageSelectionRule, resolve_pages
from models.enums import PageSelectionMode
from utils.validation import ValidationError


def test_single_page():
    assert resolve_pages("1", 10) == [1]


def test_explicit_list():
    assert resolve_pages("1,3,5", 10) == [1, 3, 5]


def test_range():
    assert resolve_pages("2-5", 10) == [2, 3, 4, 5]


def test_range_reversed_order_is_normalised():
    assert resolve_pages("5-2", 10) == [2, 3, 4, 5]


def test_first_and_last():
    assert resolve_pages("first,last", 7) == [1, 7]


def test_first_last_independent_per_document():
    # The whole point of "Last Page": it resolves independently per file.
    assert resolve_pages("last", 3) == [3]
    assert resolve_pages("last", 42) == [42]


def test_all_pages():
    assert resolve_pages("all", 5) == [1, 2, 3, 4, 5]


def test_odd_even():
    assert resolve_pages("odd", 6) == [1, 3, 5]
    assert resolve_pages("even", 6) == [2, 4, 6]


def test_every_nth_page():
    assert resolve_pages("every:2", 10) == [1, 3, 5, 7, 9]
    assert resolve_pages("every:3", 10) == [1, 4, 7, 10]


def test_last_n_pages():
    assert resolve_pages("lastn:2", 10) == [9, 10]
    assert resolve_pages("lastn:5", 5) == [1, 2, 3, 4, 5]


def test_combination_expression():
    assert resolve_pages("1,3,5-8,last", 10) == [1, 3, 5, 6, 7, 8, 10]


def test_range_with_first_last_keywords():
    assert resolve_pages("first-last", 5) == [1, 2, 3, 4, 5]


def test_out_of_range_pages_are_clamped_not_fatal():
    # A rule set once ("1,3,5,20") should keep working on shorter documents.
    assert resolve_pages("1,3,20", 5) == [1, 3]


def test_all_out_of_range_raises():
    with pytest.raises(ValidationError):
        resolve_pages("20,30", 5)


def test_empty_expression_raises():
    with pytest.raises(ValidationError):
        resolve_pages("", 5)


def test_zero_pages_raises():
    with pytest.raises(ValidationError):
        resolve_pages("1", 0)


def test_invalid_token_raises():
    with pytest.raises(ValidationError):
        resolve_pages("abc", 5)


def test_duplicates_are_deduplicated_and_sorted():
    assert resolve_pages("5,1,3,1,5", 10) == [1, 3, 5]


@pytest.mark.parametrize(
    "mode,expected_expr",
    [
        (PageSelectionMode.FIRST_PAGE, "first"),
        (PageSelectionMode.LAST_PAGE, "last"),
        (PageSelectionMode.ALL_PAGES, "all"),
        (PageSelectionMode.ODD_PAGES, "odd"),
        (PageSelectionMode.EVEN_PAGES, "even"),
    ],
)
def test_rule_to_expression_simple_modes(mode, expected_expr):
    rule = PageSelectionRule(mode=mode)
    assert rule.to_expression() == expected_expr


def test_rule_every_nth():
    rule = PageSelectionRule(mode=PageSelectionMode.EVERY_NTH_PAGE, nth=3)
    assert rule.to_expression() == "every:3"
    assert rule.resolve(9) == [1, 4, 7]


def test_rule_last_n():
    rule = PageSelectionRule(mode=PageSelectionMode.LAST_N_PAGES, last_n=2)
    assert rule.resolve(10) == [9, 10]


def test_rule_round_trip_through_dict():
    rule = PageSelectionRule(mode=PageSelectionMode.PAGE_RANGE, range_start=2, range_end=9)
    restored = PageSelectionRule.from_dict(rule.to_dict())
    assert restored.to_expression() == rule.to_expression()


def test_from_expression_reconstructs_known_shorthands():
    assert PageSelectionRule.from_expression("last").mode == PageSelectionMode.LAST_PAGE
    assert PageSelectionRule.from_expression("every:4").nth == 4
    assert PageSelectionRule.from_expression("lastn:3").last_n == 3
    assert PageSelectionRule.from_expression("2-9").range_start == 2
    custom = PageSelectionRule.from_expression("1,3,5-8,last")
    assert custom.mode == PageSelectionMode.CUSTOM
    assert custom.custom_expression == "1,3,5-8,last"
