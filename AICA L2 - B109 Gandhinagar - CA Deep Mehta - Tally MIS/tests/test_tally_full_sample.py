"""The 4.5-year sample company (with stock): Tally MIS must reproduce figures worked out separately from the books.

Skipped if the sample folder is not present (it is shipped in sample_tally_data_full/).
"""
import json
from pathlib import Path

import pytest

from app.engine import reports as R
from app.engine.cashflow_ageing import ageing
from app.engine.statements import balance_sheet, profit_and_loss
from app.model.store import Store
from app.sync import Runs, import_files

DIR = Path(__file__).parent.parent / "sample_tally_data_full"
pytestmark = pytest.mark.skipif(not (DIR / "expected_figures.json").exists(), reason="sample folder not present")
EXP = json.loads((DIR / "expected_figures.json").read_text(encoding="utf-8")) if (DIR / "expected_figures.json").exists() else {}


@pytest.fixture(scope="module")
def mis():
    store = Store()
    cid = store.ensure_company(EXP["company"])
    runs = Runs()
    for f in sorted(DIR.glob("*.xml")):
        run = import_files(store, runs.new(company_id=cid, mode="file"), cid, [str(f)])
        assert run.status == "succeeded", (f.name, run.error)
    yield store, R.make_filters(store, cid, "2021-04-01", "2025-09-30", "none")
    store.wipe()


def test_voucher_counts(mis):
    store, _ = mis
    assert store.scalar("SELECT COUNT(*) FROM vouchers") == EXP["vouchers"]["total"]
    assert store.scalar("SELECT COUNT(*) FROM vouchers WHERE line_total_paise <> 0") == 0
    assert store.scalar("SELECT COUNT(*) FROM stock_items") == 30 and store.scalar("SELECT COUNT(*) FROM inventory_lines") > 3000


def test_every_voucher_dated_1st_2nd_or_31st():
    for f in DIR.glob("*.xml"):
        if f.name.startswith("1_"):
            continue
        for d in {m for m in __import__("re").findall(r"<DATE>(\d{8})</DATE>", f.read_text(encoding="utf-8"))}:
            assert d[6:] in ("01", "02", "31"), (f.name, d)


# Stock values depend on the costing method (Tally's own, the generator's, and the estimate Tally MIS makes without Tally's
# valuation differ by small amounts, e.g. how a return is costed when an item had run out). Everything else is exact.
STOCK_TOLERANCE = 500_000  # paise = Rs 5,000 on stock of about Rs 70 lakh


@pytest.mark.parametrize("fy", sorted(EXP.get("years", {})))
def test_profit_and_loss_each_year(mis, fy):
    _, f = mis
    e = EXP["years"][fy]
    p = profit_and_loss(f.ctx, R.DateRange(e["from"], e["to"])).figures
    got = lambda k: p[k].paise
    # exact
    assert got("revenue") == e["netRevenue"]
    assert got("purchases") == e["purchases"] and got("directExpenses") == e["directExpenses"]
    assert got("depreciation") == e["depreciation"] and got("tax") == e["incomeTax"] and got("otherIncome") == e["otherIncome"]
    assert got("financeCost") == e["interest"] + e["bankCharges"]  # Tally MIS counts bank charges as finance cost
    # depends on stock valuation
    for mine, theirs in (("openingStock", "openingStock"), ("closingStock", "closingStock"), ("cogs", "cogs"),
                         ("grossProfit", "grossProfit"), ("netProfit", "netProfit")):
        assert abs(got(mine) - e[theirs]) <= STOCK_TOLERANCE, (mine, got(mine), e[theirs])
    assert got("netProfit") > 0  # a healthy company in every year


def test_closing_balances(mis):
    _, f = mis
    b, t = EXP["balances"], balance_sheet(f.ctx, "2025-09-30")["totals"]
    assert t["bank"] == b["bank"] and t["cash"] == b["cash"] and t["bank"] > 0
    assert t["tradeReceivables"] == b["receivables"] and t["tradePayables"] == b["payables"]
    assert t["fixedAssets"] == b["fixedAssets"] and t["shortTermDebt"] == b["cashCredit"] and t["longTermDebt"] == b["termLoan"] == 0
    assert abs(t["inventory"] - b["stock"]) <= STOCK_TOLERANCE
    assert abs(t["difference"]) <= 100  # the balance sheet balances
    a = ageing(f.ctx, "receivable", "2025-09-30")
    assert a["totals"]["ledgerBalance"] == b["receivables"] and a["totals"]["billwiseCoveragePct"] > 90
