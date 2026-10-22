"""
Tests for Data Normalisation.
Covers:
- Scientific-notation order IDs
- Place-of-supply variants (code, name, code-name)
- Rate normalisation (18 vs 0.18 vs "18%")
- Date formats
- Indian number strings
- Float noise rounding (11833.809999999996 -> 11833.81)
- Mixed-length HSN matching (exact and 4-digit prefix)
"""
from decimal import Decimal
from datetime import datetime
import pytest
from core.normalise import (
    to_decimal, clean_id, normalise_rate, rate_to_display_percent,
    normalise_state, normalise_hsn, match_hsn, parse_date, to_iso_date, to_display_date
)


def test_float_noise_rounding():
    val = 11833.809999999996
    d = to_decimal(val)
    assert d == Decimal("11833.81")

    val2 = "25338.219999999998"
    assert to_decimal(val2) == Decimal("25338.22")


def test_indian_number_strings():
    assert to_decimal("₹ 1,23,456.78") == Decimal("123456.78")
    assert to_decimal("INR 9,50,000.50") == Decimal("950000.50")
    assert to_decimal("(1,500.00)") == Decimal("-1500.00")
    assert to_decimal(" - ₹ 450.25 ") == Decimal("-450.25")
    assert to_decimal(None) == Decimal("0.00")
    assert to_decimal("") == Decimal("0.00")


def test_scientific_notation_ids():
    assert clean_id(4.07e12) == "4070000000000"
    assert clean_id("4.07E+12") == "4070000000000"
    assert clean_id(" 402-8773165-3571550 ") == "402-8773165-3571550"
    assert clean_id('"IN-2026-001"') == "IN-2026-001"
    assert clean_id("0012345") == "0012345"  # retains leading zeros


def test_rate_normalisation():
    assert normalise_rate(18) == Decimal("0.18")
    assert normalise_rate("18%") == Decimal("0.18")
    assert normalise_rate(0.18) == Decimal("0.18")
    assert normalise_rate(0.05) == Decimal("0.05")
    assert normalise_rate("5") == Decimal("0.05")
    assert rate_to_display_percent(Decimal("0.18")) == "18%"
    assert rate_to_display_percent(Decimal("0.05")) == "5%"
    assert rate_to_display_percent(Decimal("0.025")) == "2.50%"


def test_place_of_supply_variants():
    # GST portal format
    c1, n1 = normalise_state("33-Tamil Nadu")
    assert c1 == "33"
    assert n1 == "TAMIL NADU"

    # Bare code
    c2, n2 = normalise_state("29")
    assert c2 == "29"
    assert n2 == "KARNATAKA"

    # Bare name
    c3, n3 = normalise_state("Maharashtra")
    assert c3 == "27"
    assert n3 == "MAHARASHTRA"

    # Alias name
    c4, n4 = normalise_state("Pondicherry")
    assert c4 == "34"
    assert n4 == "PUDUCHERRY"

    c5, n5 = normalise_state("Orissa")
    assert c5 == "21"
    assert n5 == "ODISHA"


def test_date_parsing_and_formatting():
    # UTC string format from Payments
    d1 = parse_date("3 May 2026 9:09:23 am UTC")
    assert d1 is not None
    assert d1.year == 2026
    assert d1.month == 5
    assert d1.day == 3

    # ISO format from MTR
    d2 = parse_date("2026-03-04 15:07:12")
    assert d2 is not None
    assert d2.year == 2026
    assert d2.month == 3
    assert d2.day == 4

    assert to_iso_date(d2) == "2026-03-04"
    assert to_display_date(d2) == "04-03-2026"


def test_mixed_length_hsn_matching():
    # Exact match
    matched, method = match_hsn("33049930", "33049930")
    assert matched is True
    assert method == "exact"

    # 4-digit prefix match (8 digit vs 4 digit)
    matched2, method2 = match_hsn("33049930", "3304")
    assert matched2 is True
    assert method2 == "4digit_prefix"

    # Non-match
    matched3, method3 = match_hsn("34011110", "3304")
    assert matched3 is False
    assert method3 == "none"
