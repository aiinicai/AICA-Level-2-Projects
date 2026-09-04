"""Reconciliation and ingestion integrity.

Covers defects that silently corrupted a case rather than raising:
  * verifications were keyed by metric alone, so a statement's comparative column
    received the current year's verified number and was flagged as a discrepancy;
  * reprocessing reset every shared row to "unverified", erasing the needs_review
    gate a human had already acted on;
  * model-supplied values were bound straight into Float columns, so a formatted
    number or a word failed the whole document;
  * a client-guessed fiscal-year label was trusted verbatim, so "FY2024-20" became
    a phantom period beside the real ones.
"""
from __future__ import annotations

import pytest

from app.services.document.extractor import normalise_period_label
from app.services.document.pipeline import _as_float


# -- model-supplied numbers ---------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    (12345, 12345.0),
    (1.5, 1.5),
    (None, None),
    ("high", None),          # a word where a number was requested
    ({"value": 1}, None),    # a nested object
    ([1, 2], None),
    (True, None),            # bool is an int subclass — must not become 1.0
])
def test_as_float_coerces_or_rejects(raw, expected):
    assert _as_float(raw) == expected


def test_as_float_parses_indian_formatted_numbers():
    """"1,23,456" reaching a Float column used to fail the whole document."""
    assert _as_float("1,23,456") == 123456.0


# -- fiscal-year labels -------------------------------------------------------

@pytest.mark.parametrize("label", ["FY2024-20", "FY2024-03", "garbage", ""])
def test_invalid_fiscal_labels_do_not_normalise(label):
    """The upload endpoint blanks anything that fails to normalise."""
    assert normalise_period_label(label) is None


@pytest.mark.parametrize("label, expected", [
    ("FY2023-24", "FY2023-24"),
    ("2023-24", "FY2023-24"),
    ("2023-2024", "FY2023-24"),
])
def test_valid_fiscal_labels_normalise(label, expected):
    assert normalise_period_label(label) == expected
