from ipt.core.gstin import check_char, validate_gstin
from ipt.core.money import format_inr, to_decimal
from decimal import Decimal


def test_known_valid_gstin():
    assert validate_gstin("27AAPFU0939F1ZV").valid


def test_lowercase_and_spaces_are_normalised():
    assert validate_gstin(" 27aapfu0939f1zv ").valid


def test_wrong_check_digit():
    r = validate_gstin("27AAPFU0939F1ZA")
    assert not r.valid and "Check digit" in r.message


def test_bad_length_and_format():
    assert not validate_gstin("27AAPFU0939F1Z").valid
    assert not validate_gstin("2XAAPFU0939F1ZV").valid


def test_unknown_state():
    g = "00AAPFU0939F1Z"
    assert not validate_gstin(g + check_char(g)).valid


def test_generated_gstin_round_trip():
    g = "08ABCDE1234F1Z"
    assert validate_gstin(g + check_char(g)).valid


def test_money():
    assert to_decimal("1,23,456.789") == Decimal("123456.79")
    assert to_decimal("abc") is None
    assert format_inr(Decimal("1234567.5")) == "12,34,567.50"
    assert format_inr(Decimal("999")) == "999.00"
