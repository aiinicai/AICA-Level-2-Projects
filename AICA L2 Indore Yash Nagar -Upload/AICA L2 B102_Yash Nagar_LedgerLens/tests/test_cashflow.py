import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fsbuilder.cashflow import build_cash_flow  # noqa: E402
from fsbuilder.mapping import Rulebook, map_ledgers  # noqa: E402
from fsbuilder.model import build_model  # noqa: E402
from fsbuilder.tb import load_snapshot, normalise  # noqa: E402

RB = Rulebook.load()


def _model(edit=None):
    tb = normalise(load_snapshot(ROOT / "samples" / "rpi_trial_balance.csv", ROOT / "samples" / "rpi_groups.csv",
                                 "RPI", date(2024, 4, 1), date(2025, 3, 31)))
    if edit:
        L = tb.ledgers.copy()
        edit(L)
        tb = replace(tb, ledgers=L)
    return build_model(tb, map_ledgers(tb))


def _cf(m):
    return {r.label: r.cur for r in m.cashflow}


def test_sample_company_matches_independent_hand_calculation():
    c = _cf(_model())
    assert c["Net profit / (loss) before tax"] == 2_489_416
    assert c["Operating profit before working capital changes"] == 2_604_914     # + dep 1,23,259 + interest 41,913 - income 49,674
    assert c["(Increase) / decrease in trade receivables"] == -7_917_376         # 86,12,376 - 6,95,000
    assert c["Increase / (decrease) in trade payables"] == 5_906_803             # 65,01,803 - 5,95,000
    assert c["Cash generated from operations"] == 1_204_538
    assert c["Net cash from / (used in) operating activities (A)"] == 1_204_538
    assert c["Net cash from / (used in) investing activities (B)"] == 49_674
    assert c["Net cash from / (used in) financing activities (C)"] == -41_913
    assert c["D. NET INCREASE / (DECREASE) IN CASH AND CASH EQUIVALENTS (A + B + C)"] == 1_212_299
    assert c["Cash and cash equivalents at the beginning of the year"] == 1_240_000   # cash + current accounts, FD excluded
    assert c["Cash and cash equivalents at the end of the year"] == 2_452_299


def test_closing_cash_agrees_to_balance_sheet_components():
    m = _model()
    assert not any("does not reconcile" in b for b in m.basis)
    assert sum(r[1] for r in m.cce) == _cf(m)["Cash and cash equivalents at the end of the year"]
    assert sum(r[2] for r in m.cce) == _cf(m)["Cash and cash equivalents at the beginning of the year"]


def test_deposit_is_investing_and_carries_the_maturity_flag():
    def add_fd(L):  # the deposit grows by Rs 1,00,000, funded from the HDFC current account
        L.loc[L["name"] == "Fixed Deposit - HDFC Bank", "closing"] += 100_000
        L.loc[L["name"] == "HDFC Bank - Current A/c", "closing"] -= 100_000
    m = _model(add_fd)
    rows = {r.label: r for r in m.cashflow}
    dep = rows["Bank deposits placed (net of maturities)"]
    assert dep.cur == -100_000 and dep.flags          # outflow, flagged for the maturity question
    assert _cf(m)["Cash and cash equivalents at the end of the year"] == 2_352_299
    assert not any("does not reconcile" in b for b in m.basis)


def test_share_issue_loan_repayment_and_asset_purchase_all_reconcile():
    def edit(L):
        L.loc[L["name"] == "Share Capital", "closing"] -= 500_000          # more Cr = shares issued
        L.loc[L["name"] == "Term Loan - HDFC Bank", "closing"] += 250_000  # less Cr = repaid
        L.loc[L["name"] == "Computers", "closing"] += 60_000               # asset bought
        L.loc[L["name"] == "ICICI Bank - Current A/c", "closing"] += 500_000 - 250_000 - 60_000
    m = _model(edit)
    c = _cf(m)
    assert c["Proceeds from issue of share capital"] == 500_000
    assert c["Proceeds from / (repayment of) long-term borrowings"] == -250_000
    assert c["Purchase of property, plant and equipment (net of sales)"] == -60_000
    assert not any("does not reconcile" in b for b in m.basis)


def test_tax_paid_is_expense_less_unpaid_provision():
    subs = {"CL.STP": [["Provision for tax", 70_000, 20_000]], "CA.CBB": [["Cash on hand", 0, 0]]}
    cf = build_cash_flow(subs, RB.lines, dict(pbt=300_000, profit=210_000, tax_expense=90_000, dep=0, fin=0,
                                              interest=0, dividend=0, gain=0))
    rows = {r[0]: r[1] for r in cf["rows"]}
    # 90,000 expensed, provision rose by 50,000, so 40,000 was actually paid
    assert rows["Direct taxes paid (net of refunds)"] == -40_000


def test_unknown_balance_sheet_line_is_an_error_not_silently_dropped():
    with pytest.raises(ValueError):
        build_cash_flow({"ZZ.NEW": [["x", 1, 0]]}, {**RB.lines, "ZZ.NEW": {"statement": "BS", "side": "A"}},
                        dict(pbt=0, profit=0, tax_expense=0, dep=0, fin=0, interest=0, dividend=0, gain=0))


def test_small_company_observation_is_raised_for_the_sample():
    m = _model()
    obs = [f for f in m.flags if f.area == "Cash flow statement"]
    assert len(obs) == 1 and "Sec 2(40)" in obs[0].text
