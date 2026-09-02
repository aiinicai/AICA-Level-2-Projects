"""Extraction/number-handling tests: Indian commas, parentheses, lakh/crore."""
from app.services.financial.numbers import format_indian, format_inr, parse_amount


def test_indian_comma_parsing():
    assert parse_amount("1,25,00,000") == 12_500_000
    assert parse_amount("12,34,56,789") == 123_456_789


def test_currency_symbols_and_crore():
    assert parse_amount("₹1.25 Cr") == 12_500_000
    assert parse_amount("Rs. 2 Crores") == 20_000_000


def test_lakh_variants():
    assert parse_amount("125 Lakhs") == 12_500_000
    assert parse_amount("36.20 lakh") == 3_620_000
    assert parse_amount("5 lacs") == 500_000


def test_parentheses_negative():
    assert parse_amount("(1,250)") == -1250
    assert parse_amount("(12.5) Cr") == -125_000_000


def test_default_unit_multiplier():
    # column headed "₹ in Lakhs" — plain number takes the document unit
    assert parse_amount("36.20", default_unit_multiplier=100_000) == 3_620_000
    # inline unit wins over the default
    assert parse_amount("1.5 Cr", default_unit_multiplier=100_000) == 15_000_000


def test_blank_and_nil():
    assert parse_amount("") is None
    assert parse_amount("-") is None
    assert parse_amount("Nil") is None
    assert parse_amount(None) is None


def test_numeric_passthrough():
    assert parse_amount(1250.5) == 1250.5
    assert parse_amount(12, default_unit_multiplier=1e7) == 120_000_000


def test_format_indian_grouping():
    assert format_indian(12_500_000) == "1,25,00,000"
    assert format_indian(-123456789) == "-12,34,56,789"


def test_format_inr_crore():
    assert format_inr(21_100_000) == "₹ 2.11 Cr"
