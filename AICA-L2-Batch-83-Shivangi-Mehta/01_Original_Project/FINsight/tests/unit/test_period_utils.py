"""
Stage 8 — app/rules/period_utils.py (pure functions, no DB/Flask).
Run with: pytest tests/unit/test_period_utils.py -v
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rules.period_utils import (
    days_held_in_period,
    financial_year_bounds,
    prior_financial_year,
    total_days_in_period,
)


def test_financial_year_bounds_normal():
    assert financial_year_bounds("2025-26") == (date(2025, 4, 1), date(2026, 3, 31))


def test_financial_year_bounds_invalid_format_returns_none():
    assert financial_year_bounds("2025") is None
    assert financial_year_bounds("not-a-year") is None
    assert financial_year_bounds("") is None
    assert financial_year_bounds(None) is None


def test_prior_financial_year():
    assert prior_financial_year("2025-26") == "2024-25"
    assert prior_financial_year("2000-01") == "1999-00"


def test_prior_financial_year_invalid_format_returns_none():
    assert prior_financial_year("bad") is None


def test_total_days_in_period_non_leap_year():
    assert total_days_in_period(date(2025, 4, 1), date(2026, 3, 31)) == 365


def test_total_days_in_period_leap_year():
    # FY 2023-24 includes 29 Feb 2024
    assert total_days_in_period(date(2023, 4, 1), date(2024, 3, 31)) == 366


def test_days_held_asset_put_to_use_mid_year():
    fy_start, fy_end = date(2025, 4, 1), date(2026, 3, 31)
    # Put to use 1 Oct 2025 -> held from 1 Oct through 31 Mar inclusive
    assert days_held_in_period(date(2025, 10, 1), fy_start, fy_end) == 182


def test_days_held_asset_put_to_use_before_fy_start_counts_whole_fy():
    fy_start, fy_end = date(2025, 4, 1), date(2026, 3, 31)
    assert days_held_in_period(date(2020, 1, 1), fy_start, fy_end) == total_days_in_period(fy_start, fy_end)


def test_days_held_asset_put_to_use_after_fy_end_is_zero():
    fy_start, fy_end = date(2025, 4, 1), date(2026, 3, 31)
    assert days_held_in_period(date(2026, 6, 1), fy_start, fy_end) == 0


def test_days_held_asset_put_to_use_on_fy_end_is_one_day():
    fy_start, fy_end = date(2025, 4, 1), date(2026, 3, 31)
    assert days_held_in_period(date(2026, 3, 31), fy_start, fy_end) == 1
