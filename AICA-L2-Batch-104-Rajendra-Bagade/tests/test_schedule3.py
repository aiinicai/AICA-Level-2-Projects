"""Schedule III classification and the face of the financial statements."""

from __future__ import annotations

import pytest

from auditlens.financials import build_statements, map_trial_balance, unmapped_value
from auditlens.schedule3 import UNMAPPED, classify_account, natural_balance, summarise


@pytest.mark.parametrize(
    "code,name,expected",
    [
        ("1001", "Equity share capital", "Share capital"),
        ("1201", "Term loan from State Bank of India", "Long-term borrowings"),
        ("1331", "Trade payables - micro and small enterprises", "Trade payables"),
        ("2003", "Plant and machinery", "Property, plant and equipment"),
        ("2251", "Trade receivables - considered good", "Trade receivables"),
        ("2282", "Balances with banks in current accounts", "Cash and cash equivalents"),
        ("3001", "Sale of manufactured goods", "Revenue from operations"),
        ("4301", "Interest on term loan", "Finance costs"),
        ("4351", "Depreciation on tangible assets", "Depreciation and amortisation expense"),
        ("4901", "Current tax", "Current tax"),
    ],
)
def test_account_code_drives_the_mapping(code, name, expected):
    c = classify_account(code, name)
    assert c.head == expected
    assert c.basis == "account_code"
    assert c.confidence == 1.0
    assert not c.needs_review


def test_keyword_fallback_maps_but_flags_for_review():
    """A ledger outside the firm's numbering convention is mapped on its
    name, and always goes in front of the auditor."""
    c = classify_account("9911", "Capital advance for machinery under installation")
    assert c.head == "Other non-current assets"
    assert c.basis == "keyword"
    assert c.needs_review


def test_unmappable_ledger_is_never_guessed():
    c = classify_account("9999", "Suspense account - to be cleared")
    assert c.head == UNMAPPED
    assert not c.is_mapped
    assert c.needs_review


def test_most_specific_keyword_wins():
    assert classify_account("X", "Deferred tax liability").head == "Deferred tax liabilities (net)"
    assert classify_account("X", "Deferred tax asset").head == "Deferred tax assets (net)"


def test_natural_balance():
    assert natural_balance("Trade payables") == "Cr"
    assert natural_balance("Revenue from operations") == "Cr"
    assert natural_balance("Trade receivables") == "Dr"
    assert natural_balance("Other expenses") == "Dr"


def test_mapping_summary_on_the_sample(tb):
    s = summarise(map_trial_balance(tb).classifications)
    assert s.total == 61
    assert s.coverage > 0.95
    assert len(s.unmapped) == 1
    assert s.unmapped[0].account_name.startswith("Suspense")
    # Everything not mapped on a code is queued for the auditor.
    assert len(s.review) == s.by_keyword + len(s.unmapped)


def test_balance_sheet_ties_once_profit_and_unmapped_are_dealt_with(tb, tb_prior):
    """The trial balance is pre-closing, so the balance sheet can only tie
    after the profit is taken to reserves; the residual difference must be
    exactly the unclassified value."""
    m, mp = map_trial_balance(tb), map_trial_balance(tb_prior)
    from auditlens.financials import derive_figures

    f = derive_figures(m)
    fs = build_statements(m, mp, profit_for_the_year=f.profit_after_tax)

    assert not fs.balance_sheet_tallies
    assert abs(fs.difference) == pytest.approx(unmapped_value(m), abs=1.0)
    assert "unmapped" in fs.reconciliation or "could not classify" in fs.reconciliation


def test_balance_sheet_tallies_when_nothing_is_unmapped(tmp_path):
    from auditlens.ingest import load_trial_balance
    from auditlens.financials import derive_figures

    path = tmp_path / "tb.csv"
    path.write_text(
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,1000000\n"
        "2281,Cash in hand,1300000,0\n"
        "3001,Sale of manufactured goods,0,500000\n"
        "4401,Power and fuel,200000,0\n"
    )
    m = map_trial_balance(load_trial_balance(path, "2024-25"))
    f = derive_figures(m)
    fs = build_statements(m, profit_for_the_year=f.profit_after_tax)
    assert f.profit_after_tax == 300000.0
    assert fs.balance_sheet_tallies, fs.reconciliation


def test_presented_figures_are_positive(tb):
    m = map_trial_balance(tb)
    for head in ("Share capital", "Trade payables", "Revenue from operations"):
        assert m.presented(head) > 0


def test_totals_carry_a_comparative(tb, tb_prior):
    """A blank prior-year total column reads as an unfinished statement."""
    from auditlens.financials import derive_figures

    m, mp = map_trial_balance(tb), map_trial_balance(tb_prior)
    f, fp = derive_figures(m), derive_figures(mp)
    fs = build_statements(
        m, mp, profit_for_the_year=f.profit_after_tax, prior_profit=fp.profit_after_tax
    )
    totals = [line for line in fs.balance_sheet if line.is_total]
    assert totals, "the balance sheet has no total lines"
    for line in totals:
        assert line.prior is not None, f"'{line.label}' has no comparative"
        assert line.prior > 0


def test_totals_have_no_comparative_when_none_is_supplied(tb):
    from auditlens.financials import derive_figures

    m = map_trial_balance(tb)
    fs = build_statements(m, profit_for_the_year=derive_figures(m).profit_after_tax)
    for line in fs.balance_sheet:
        if line.is_total:
            assert line.prior is None
