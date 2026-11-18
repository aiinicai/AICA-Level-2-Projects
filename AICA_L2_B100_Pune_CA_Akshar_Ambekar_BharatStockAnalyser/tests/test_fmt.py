import math

import pandas as pd
import pytest

from bsa.fmt import cagr, clean, fmt_cr, fmt_num, fmt_pct, fy_label, median, num, q_label


@pytest.mark.parametrize("value,expected", [
    (0, "0"), (999, "999"), (1000, "1,000"), (123456, "1,23,456"), (1234567, "12,34,567"),
    (123456789, "12,34,56,789"), (-4437, "(4,437)"),
])
def test_indian_grouping(value, expected):
    assert fmt_num(value) == expected


def test_crore_and_percent():
    assert fmt_cr(2_41_636 * 1e7) == "2,41,636"
    assert fmt_cr(459.6 * 1e7) == "459.6"
    assert fmt_pct(-1.63) == "(1.6)%"
    assert fmt_pct(26.2, signed=True) == "+26.2%"
    assert fmt_pct(None) == "-"


def test_fiscal_labels():
    assert fy_label(pd.Timestamp("2026-03-31")) == "FY26"
    assert fy_label(pd.Timestamp("2025-12-31")) == "Dec25"
    assert q_label(pd.Timestamp("2026-06-30")) == "Q1FY27"
    assert q_label(pd.Timestamp("2026-03-31")) == "Q4FY26"
    assert q_label(pd.Timestamp("2025-12-31")) == "Q3FY26"


def test_cagr_and_median():
    assert cagr(1000, 1331, 3) == pytest.approx(10.0)
    assert cagr(-5, 10, 3) is None
    assert median([3, None, 1, 2, float("nan")]) == 2
    assert median([1, 2, 3, 4]) == 2.5


def test_num_and_clean():
    assert num(float("inf")) is None
    assert num("12.5") == 12.5
    out = clean({"a": float("nan"), "b": [1, math.inf], "c": pd.Timestamp("2026-03-31")})
    assert out == {"a": None, "b": [1, None], "c": "2026-03-31T00:00:00"}
