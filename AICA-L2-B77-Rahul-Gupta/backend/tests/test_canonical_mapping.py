"""Label → canonical metric mapping, especially the cash flow statement.

CFO used to capture "Cash generated from operations" — the subtotal ABOVE
"Income taxes paid" — instead of "Net cash from operating activities", which is
CFO under AS-3. It read 117.00 lakh instead of 95.00, overstating operating cash
by 23%. CFF matched nothing at all, and opening/closing cash were shadowed by the
generic "cash" pattern, so the CASH_BRIDGE and COMPARATIVE_CASH validation checks
silently reported "Insufficient data" instead of ever running.

The arithmetic is the real guard: opening + CFO + CFI + CFF must equal closing.
A wrong CFO cannot balance.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.document.extractor import extract_pdf_items, inspect_pdf
from app.services.financial.canonical import map_label_to_metric

FIXTURE = Path(__file__).parent / "fixtures" / "CompanyVal_AI_Schedule_III_Financials_FY2023-24.pdf"
LAKH = 100_000.0


@pytest.fixture(scope="module")
def cf_values():
    """First value per metric, mirroring how _upsert_line_items resolves duplicates."""
    ext = extract_pdf_items(FIXTURE, inspect_pdf(FIXTURE))
    out: dict[str, float] = {}
    for item in ext.items:
        if item.period_label == "FY2023-24" and item.metric and item.metric not in out:
            out[item.metric] = item.value
    return out


# -- the mapping itself ------------------------------------------------------

def test_cfo_is_the_post_tax_figure_not_the_pre_tax_subtotal():
    assert map_label_to_metric("Net cash from operating activities (A)") == "cfo"
    # the subtotal before "Income taxes paid" is NOT cash flow from operations
    assert map_label_to_metric("Cash generated from operations") is None


@pytest.mark.parametrize("label, metric", [
    ("Net cash from / (used in) financing activities (C)", "cff"),
    ("Net cash used in investing activities (B)", "cfi"),
    ("Net cash generated from operating activities", "cfo"),
    ("Cash flows from financing activities", "cff"),
    ("Cash and cash equivalents at the beginning of the year", "opening_cash"),
    ("Cash and cash equivalents at the end of the year", "closing_cash"),
])
def test_cash_flow_totals_map_across_common_wordings(label, metric):
    assert map_label_to_metric(label) == metric


@pytest.mark.parametrize("label", [
    "Net increase / (decrease) in cash and cash equivalents (A+B+C)",
    "Increase / (decrease) in short-term borrowings",
])
def test_movement_lines_are_not_mistaken_for_balances(label):
    """These state the change over the year, not a closing balance."""
    assert map_label_to_metric(label) is None


def test_balance_sheet_cash_still_maps():
    assert map_label_to_metric("(d) Cash and cash equivalents") == "cash"


# -- against the real statement ----------------------------------------------

@pytest.mark.parametrize("metric, expected_lakh", [
    ("cfo", 95.00),           # was wrongly 117.00
    ("cfi", -63.00),
    ("cff", -22.00),          # was missing entirely
    ("opening_cash", 35.00),  # was missing entirely
    ("closing_cash", 45.00),  # was missing entirely
])
def test_extracted_cash_flow_values(cf_values, metric, expected_lakh):
    assert cf_values.get(metric) == pytest.approx(expected_lakh * LAKH)


def test_cash_flow_statement_reconciles(cf_values):
    """opening + CFO + CFI + CFF == closing. This is what CASH_BRIDGE asserts,
    and it cannot hold if CFO is the pre-tax subtotal."""
    derived = (cf_values["opening_cash"] + cf_values["cfo"]
               + cf_values["cfi"] + cf_values["cff"])
    assert derived == pytest.approx(cf_values["closing_cash"])
