"""Identifier validation. Build Prompt v2 §8.6."""

from __future__ import annotations

from datetime import date

import pytest

from app.core.validators import (
    ValidationError,
    validate_cin,
    validate_din,
    validate_frn,
    validate_fy,
    validate_gstin,
    validate_membership_no,
    validate_pan,
    validate_report_date,
    validate_udin,
)


class TestCin:
    VALID = "U72200MH2010PTC054288"

    def test_valid(self) -> None:
        assert validate_cin(self.VALID) == self.VALID

    def test_normalises_case_and_spacing(self) -> None:
        assert validate_cin(" u72200 mh2010 ptc054288 ") == self.VALID

    @pytest.mark.parametrize(
        ("cin", "reason"),
        [
            ("U72200MH2010PTC05428", "21 characters"),
            ("X72200MH2010PTC054288", "structure"),
            ("U72200ZZ2010PTC054288", "state code"),
            ("U72200MH1600PTC054288", "implausible"),
            ("U72200MH2010XXX054288", "ownership class"),
            ("L72200MH2010PTC054288", "listed"),
        ],
    )
    def test_rejected(self, cin: str, reason: str) -> None:
        with pytest.raises(ValidationError, match=reason):
            validate_cin(cin)

    def test_listed_public_company_accepted(self) -> None:
        assert validate_cin("L72200MH2010PLC054288").startswith("L")


class TestPan:
    def test_valid(self) -> None:
        assert validate_pan("aabca1234c") == "AABCA1234C"

    @pytest.mark.parametrize("pan", ["AABCA1234", "AABC11234C", "AABCA1234CC", "1ABCA1234C"])
    def test_malformed_rejected(self, pan: str) -> None:
        with pytest.raises(ValidationError):
            validate_pan(pan)

    def test_invalid_holder_type_rejected(self) -> None:
        # The fourth character encodes the holder type; 'X' is not one.
        with pytest.raises(ValidationError, match="holder-type"):
            validate_pan("AABXA1234C")


class TestOtherIdentifiers:
    def test_gstin(self) -> None:
        assert validate_gstin("27AABCA1234C1ZP") == "27AABCA1234C1ZP"

    def test_gstin_rejects_wrong_length(self) -> None:
        with pytest.raises(ValidationError):
            validate_gstin("27AABCA1234C1Z")

    def test_din(self) -> None:
        assert validate_din("00123456") == "00123456"

    @pytest.mark.parametrize("din", ["1234567", "123456789", "0012345A"])
    def test_din_rejected(self, din: str) -> None:
        with pytest.raises(ValidationError):
            validate_din(din)

    def test_frn_with_and_without_suffix(self) -> None:
        assert validate_frn("000000W") == "000000W"
        assert validate_frn("123456") == "123456"

    def test_membership_number(self) -> None:
        assert validate_membership_no("123456") == "123456"
        with pytest.raises(ValidationError):
            validate_membership_no("1234")

    def test_udin(self) -> None:
        # 26 (year) + 123456 (membership) + 10 alphanumeric = 18 characters.
        assert validate_udin("26123456AB1234CD56") == "26123456AB1234CD56"

    def test_udin_is_exactly_eighteen_characters(self) -> None:
        with pytest.raises(ValidationError):
            validate_udin("26123456AB1234CD5")  # 17
        with pytest.raises(ValidationError):
            validate_udin("26123456AB1234CD567")  # 19

    @pytest.mark.parametrize("udin", ["2612345", "26123456AAAA", "AA123456AB1234CD56"])
    def test_udin_rejected(self, udin: str) -> None:
        with pytest.raises(ValidationError):
            validate_udin(udin)


class TestDates:
    def test_normal_financial_year(self) -> None:
        validate_fy(date(2025, 4, 1), date(2026, 3, 31))

    def test_reversed_year_rejected(self) -> None:
        with pytest.raises(ValidationError, match="after its start"):
            validate_fy(date(2026, 3, 31), date(2025, 4, 1))

    def test_first_year_may_exceed_twelve_months(self) -> None:
        # s.2(41) — a first financial year can run longer than a year.
        validate_fy(date(2025, 1, 10), date(2026, 3, 31))

    def test_but_not_beyond_fifteen_months(self) -> None:
        with pytest.raises(ValidationError, match="fifteen months"):
            validate_fy(date(2024, 1, 1), date(2026, 3, 31))

    def test_report_date_cannot_precede_year_end(self) -> None:
        with pytest.raises(ValidationError, match="cannot precede"):
            validate_report_date(date(2026, 3, 30), date(2026, 3, 31))

    def test_report_date_on_year_end_allowed(self) -> None:
        validate_report_date(date(2026, 3, 31), date(2026, 3, 31))
