"""
Stage 5 — app/utils/currency.py (paise <-> rupee conversion).

Pure functions, no SQLAlchemy/Flask dependency for the logic itself —
but importing anything under `app.*` still runs `app/__init__.py`
first, which imports Flask and (transitively, via other modules) will
need SQLAlchemy once real dependencies are installed.

Ran for real under `pytest` in the delivery sandbox (11/11 passed) —
see the Stage 5 delivery notes for how: a genuinely real Flask 3.1.3
this sandbox happens to have cached, plus a scoped SQLAlchemy 2.x
declarative-ORM shim standing in for the still-uninstallable real
SQLAlchemy/Alembic (network to PyPI/apt confirmed 403 again during
Stage 5 delivery). Also runs unmodified once real dependencies are
installed per requirements.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from app.utils.currency import CurrencyParseError, paise_to_display, paise_to_rupees_float, rupees_to_paise


def test_blank_and_none_return_none():
    assert rupees_to_paise(None) is None
    assert rupees_to_paise("") is None
    assert rupees_to_paise("   ") is None


def test_plain_and_decimal_amounts():
    assert rupees_to_paise("100") == 10000
    assert rupees_to_paise("100.5") == 10050
    assert rupees_to_paise("19.99") == 1999
    assert rupees_to_paise(1000) == 100000


def test_indian_grouped_input():
    assert rupees_to_paise("1,23,45,678.90") == 1234567890


def test_currency_symbol_and_whitespace_tolerated():
    assert rupees_to_paise("₹500") == 50000
    assert rupees_to_paise(" 500 ") == 50000


def test_negative_amount_rejected():
    with pytest.raises(CurrencyParseError):
        rupees_to_paise("-100")


def test_garbage_input_rejected():
    with pytest.raises(CurrencyParseError):
        rupees_to_paise("not a number")


def test_paise_to_rupees_float():
    assert paise_to_rupees_float(None) is None
    assert paise_to_rupees_float(10050) == 100.5


def test_paise_to_display_blank_and_zero():
    assert paise_to_display(None) == "—"
    assert paise_to_display(0) == "₹0.00"


def test_paise_to_display_indian_grouping():
    assert paise_to_display(1234567890) == "₹1,23,45,678.90"
    assert paise_to_display(123456) == "₹1,234.56"


def test_paise_to_display_negative():
    assert paise_to_display(-50000) == "-₹500.00"


def test_round_trip_stability():
    for rupees_text in ("1", "99.99", "12,34,567", "0"):
        paise = rupees_to_paise(rupees_text)
        # Converting back and re-parsing the displayed string must land
        # on the same paise value — no silent drift through the pair.
        displayed = paise_to_display(paise)
        assert rupees_to_paise(displayed) == paise
