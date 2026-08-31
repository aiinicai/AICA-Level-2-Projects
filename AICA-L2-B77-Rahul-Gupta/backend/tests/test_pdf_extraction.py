"""PDF extraction regression tests against real Schedule III statements.

These fixtures previously extracted ZERO usable line items: the parser matched a
label and its values only when they sat on one physical text line, but these PDFs
emit every table cell as its own text object, so nothing matched except a stray
"Page N" footer. Extraction now runs through PyMuPDF's geometry-based table
detector, and these tests pin that behaviour.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.document.extractor import extract_pdf_items, inspect_pdf

FIXTURES = Path(__file__).parent / "fixtures"
FY2023_24 = FIXTURES / "CompanyVal_AI_Schedule_III_Financials_FY2023-24.pdf"

LAKH = 100_000.0


@pytest.fixture(scope="module")
def extraction():
    return extract_pdf_items(FY2023_24, inspect_pdf(FY2023_24))


def test_pdf_has_native_text(extraction):
    # a scanned PDF would be rejected upstream rather than parsed
    assert extraction.has_native_text
    assert extraction.page_count == 9


def test_extracts_many_line_items_not_zero(extraction):
    # the bug produced 5 junk items ("Page 1"..."Page 8"); a correct parse is ~180
    assert len(extraction.items) > 100


def test_uses_the_table_detector(extraction):
    # the single-line regex fallback cannot parse these cell-per-object tables
    assert any(i.method == "pymupdf_table" for i in extraction.items)


def test_detects_document_unit_and_periods(extraction):
    assert extraction.unit_name == "lakh"
    assert extraction.unit_multiplier == LAKH
    # statements carry the current year plus a comparative prior year
    assert "FY2023-24" in extraction.period_labels
    assert "FY2022-23" in extraction.period_labels


def _first(extraction, metric: str, period: str = "FY2023-24") -> float | None:
    for item in extraction.items:
        if item.metric == metric and item.period_label == period:
            return item.value
    return None


@pytest.mark.parametrize("metric, expected_lakh", [
    ("revenue", 800.00),        # Revenue from operations
    ("share_capital", 100.00),  # Share capital
    ("pat", 60.00),             # Profit for the year
])
def test_canonical_metrics_carry_correct_values(extraction, metric, expected_lakh):
    """Values normalise to absolute INR using the document's declared unit."""
    assert _first(extraction, metric) == pytest.approx(expected_lakh * LAKH)


def test_prior_year_column_is_attributed_to_the_prior_period(extraction):
    """Two-column statements must not collapse both years onto one period."""
    assert _first(extraction, "revenue", "FY2022-23") == pytest.approx(720.00 * LAKH)
