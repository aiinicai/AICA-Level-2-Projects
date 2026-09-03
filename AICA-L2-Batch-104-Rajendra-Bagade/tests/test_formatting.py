"""Indian digit grouping."""

from __future__ import annotations

import pytest

from auditlens.formatting import compact, in_crores, in_lakhs, inr


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0.00"),
        (999, "999.00"),
        (1000, "1,000.00"),
        (99999, "99,999.00"),
        (100000, "1,00,000.00"),
        (1234567, "12,34,567.00"),
        (10000000, "1,00,00,000.00"),
        (50000000, "5,00,00,000.00"),
        (218440000, "21,84,40,000.00"),
        (1234567890, "1,23,45,67,890.00"),
    ],
)
def test_indian_grouping(value, expected):
    assert inr(value) == expected


def test_negative_amounts_keep_the_sign_outside_the_grouping():
    assert inr(-125000) == "-1,25,000.00"
    assert inr(-125000, decimals=0, prefix="Rs ") == "Rs -1,25,000"


def test_decimals_are_configurable():
    assert inr(1234567.891, decimals=0) == "12,34,568"
    assert inr(1234567.891, decimals=2) == "12,34,567.89"


def test_none_renders_as_a_dash():
    assert inr(None) == "-"
    assert compact(None) == "-"


def test_lakhs_and_crores():
    assert in_lakhs(2500000) == "25.00 lakh"
    assert in_crores(218440000) == "21.84 crore"


def test_compact_picks_the_unit_a_reader_would_say():
    assert compact(218440000) == "Rs 21.84 crore"
    assert compact(2500000) == "Rs 25.00 lakh"
    assert compact(4500) == "Rs 4,500"
