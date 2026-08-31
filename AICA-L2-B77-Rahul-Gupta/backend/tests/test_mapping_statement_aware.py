"""Statement-aware label mapping over real Schedule III statements.

Schedule III splits several canonical figures across lines of the same table
(payables into MSME/non-MSME, COGS into materials + purchases + stock change),
enumerates almost every row ("(a) Share capital", "IX. Profit before tax"), and
reuses the same nouns on the P&L, balance sheet and cash flow statement for
completely different concepts. Matching a bare regex against the raw label
therefore produced silent, material errors: payables never populated at all,
COGS understated by 15%, a P&L interest line written into a debt stock.

The end-to-end guard is arithmetic: with the mapping correct, all 23 accounting
validation checks over the three fixtures pass with none skipped.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.document.extractor import extract_pdf_items, inspect_pdf
from app.services.document.pipeline import _resolve_items
from app.services.financial.canonical import map_label_to_metric, normalise_metric_sign

FIXTURE = Path(__file__).parent / "fixtures" / "CompanyVal_AI_Schedule_III_Financials_FY2023-24.pdf"
LAKH = 100_000.0


@pytest.fixture(scope="module")
def resolved():
    ext = extract_pdf_items(FIXTURE, inspect_pdf(FIXTURE))
    out = _resolve_items(ext, None)
    return {m: d["value"] for (period, m), d in out.items() if period == "FY2023-24"}


# -- values Schedule III splits across several lines --------------------------

@pytest.mark.parametrize("metric, expected_lakh, why", [
    ("trade_payables", 82.00, "MSME 12 + non-MSME 70 — previously unmappable, so 0"),
    ("other_liabilities", 53.00, "other current liabilities 33 + short-term provisions 20"),
    ("material_cost", 420.00, "materials 355 + purchases 72 + stock change -7"),
    ("fixed_assets", 280.00, "tangible assets 260 + capital work-in-progress 20"),
])
def test_split_lines_are_summed(resolved, metric, expected_lakh, why):
    assert resolved.get(metric) == pytest.approx(expected_lakh * LAKH), why


# -- concepts that share a noun across statements -----------------------------

def test_pnl_stock_movement_is_cogs_not_the_balance_sheet_stock():
    """"Changes in inventories…" is a Part II expense, not closing inventory."""
    assert map_label_to_metric(
        "Changes in inventories of finished goods, work-in-progress and Stock-in-Trade",
        "profit_and_loss") == "material_cost"


def test_closing_inventory_still_maps_to_the_stock(resolved):
    assert resolved.get("inventory") == pytest.approx(110.00 * LAKH)


def test_interest_on_term_loans_is_a_finance_cost_not_a_debt_stock():
    """`term loans?` in long_term_borrowings used to swallow this P&L expense."""
    assert map_label_to_metric("Interest on term loans", "profit_and_loss") == "finance_cost"


def test_balance_sheet_stocks_cannot_be_sourced_from_a_cash_flow_page():
    """Every borrowings/cash noun on the cash flow statement names a movement."""
    assert map_label_to_metric("Proceeds from long-term borrowings", "cash_flow") is None
    assert map_label_to_metric("Repayment of long-term borrowings", "cash_flow") is None


def test_enumerated_labels_still_match():
    """Schedule III prefixes nearly every row; the enumerator must be stripped."""
    assert map_label_to_metric("(a) Share capital", "balance_sheet") == "share_capital"
    assert map_label_to_metric("IX. Profit before tax (VII - VIII)", "profit_and_loss") == "pbt"


def test_bare_total_on_a_balance_sheet_is_total_assets():
    """Division I prints the totals with no noun; without this BS_EQUATION never ran."""
    assert map_label_to_metric("TOTAL", "balance_sheet") == "total_assets"
    # ...but a bare TOTAL anywhere else is a subtotal of something unknown
    assert map_label_to_metric("TOTAL", "profit_and_loss") != "total_assets"


def test_note_ratio_rows_are_ignored():
    """The 2021 amendment mandates a ratio table whose small numbers would
    otherwise be read as the figures themselves."""
    assert map_label_to_metric("Inventory turnover ratio", "balance_sheet") is None
    assert map_label_to_metric("Trade payables turnover ratio", "balance_sheet") is None


# -- signs --------------------------------------------------------------------

def test_capex_is_stored_as_a_magnitude(resolved):
    """Printed as a bracketed outflow, but seeded and consumed as a magnitude."""
    assert normalise_metric_sign("capex", resolved["capex"]) == pytest.approx(63.00 * LAKH)


@pytest.mark.parametrize("metric, value", [("cfi", -1.0), ("cff", -1.0), ("tax", -1.0)])
def test_directional_metrics_keep_their_sign(metric, value):
    """Only capex is magnitude-normalised: a deferred tax credit is genuinely
    negative, and investing/financing flows are directional by definition."""
    assert normalise_metric_sign(metric, value) == value


# -- the arithmetic guard -----------------------------------------------------

def test_cash_flow_statement_reconciles(resolved):
    derived = (resolved["opening_cash"] + resolved["cfo"]
               + resolved["cfi"] + resolved["cff"])
    assert derived == pytest.approx(resolved["closing_cash"])


def test_balance_sheet_equation_holds(resolved):
    """total assets == (share capital + reserves) + liabilities."""
    net_worth = resolved["share_capital"] + resolved["reserves"]
    liabilities = (resolved["long_term_borrowings"] + resolved["short_term_borrowings"]
                   + resolved["trade_payables"] + resolved["other_liabilities"])
    assert resolved["total_assets"] == pytest.approx(net_worth + liabilities)
