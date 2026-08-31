"""Indian conventions. Build Prompt v2 §12."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.formatting import (
    AmountsIn,
    DateStyle,
    financial_year,
    format_date,
    group_indian,
    in_words,
    rupees,
    scale,
    unit_caption,
)


class TestIndianGrouping:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, "0"),
            (7, "7"),
            (999, "999"),
            (1_000, "1,000"),
            (99_999, "99,999"),
            (1_00_000, "1,00,000"),
            (12_543_000, "1,25,43,000"),
            (1_00_00_000, "1,00,00,000"),
            (12_34_56_789, "12,34,56,789"),
        ],
    )
    def test_groups_by_lakh_and_crore(self, value: int, expected: str) -> None:
        assert group_indian(value) == expected

    def test_not_western_grouping(self) -> None:
        # 12,543,000 would be wrong in every Indian statutory document.
        assert group_indian(12_543_000) != "12,543,000"

    def test_negatives(self) -> None:
        assert group_indian(-12_543_000) == "-1,25,43,000"

    def test_rupee_symbol(self) -> None:
        assert rupees(12_543_000) == "₹1,25,43,000"
        assert rupees(12_543_000, symbol=False) == "1,25,43,000"

    def test_rounds_half_up(self) -> None:
        assert group_indian(Decimal("1000.5")) == "1,001"


class TestWords:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, "Rupees Zero Only"),
            (7, "Rupees Seven Only"),
            (15, "Rupees Fifteen Only"),
            (42, "Rupees Forty Two Only"),
            (100, "Rupees One Hundred Only"),
            (1_000, "Rupees One Thousand Only"),
            (1_00_000, "Rupees One Lakh Only"),
            (1_25_43_000, "Rupees One Crore Twenty Five Lakh Forty Three Thousand Only"),
        ],
    )
    def test_indian_scale(self, value: int, expected: str) -> None:
        assert in_words(value) == expected

    def test_uses_lakh_and_crore_not_million(self) -> None:
        words = in_words(1_25_43_000)
        assert "Million" not in words
        assert "Crore" in words and "Lakh" in words


class TestDates:
    FY_END = date(2025, 3, 31)

    def test_ui_style(self) -> None:
        assert format_date(date(2026, 8, 15), DateStyle.UI) == "15-Aug-2026"

    def test_long_style(self) -> None:
        assert format_date(self.FY_END, DateStyle.LONG) == "31st March, 2025"

    def test_numeric_style(self) -> None:
        assert format_date(self.FY_END, DateStyle.NUMERIC) == "31.03.2025"

    @pytest.mark.parametrize(
        ("day", "suffix"),
        [
            (1, "1st"),
            (2, "2nd"),
            (3, "3rd"),
            (4, "4th"),
            (11, "11th"),
            (12, "12th"),
            (13, "13th"),
            (21, "21st"),
            (22, "22nd"),
            (23, "23rd"),
            (31, "31st"),
        ],
    )
    def test_ordinals(self, day: int, suffix: str) -> None:
        assert format_date(date(2025, 1, day), DateStyle.LONG).startswith(suffix)


class TestFinancialYear:
    def test_march_year_end(self) -> None:
        assert financial_year(date(2026, 3, 31)) == "FY 2025-26"

    def test_december_year_end(self) -> None:
        assert financial_year(date(2025, 12, 31)) == "FY 2025-26"

    def test_century_rollover_digits(self) -> None:
        assert financial_year(date(2100, 3, 31)) == "FY 2099-00"


class TestAmountsIn:
    def test_captions(self) -> None:
        assert unit_caption(AmountsIn.LAKHS) == "Amount in ₹ Lakhs"
        assert unit_caption(AmountsIn.UNITS) == "Amount in ₹"

    def test_scaling(self) -> None:
        assert scale(12_543_000, AmountsIn.LAKHS) == Decimal("125.43")
        assert scale(12_543_000, AmountsIn.CRORES) == Decimal("1.25")
