"""The six clients in demo_clients/: the files are read by the same importers the screens use.

The income-side figures below are worked by hand from the files (the arithmetic is written out).
The tax on them is the engine's, which is covered by tests/test_engine.py and tests/test_demo_clients.py.
"""
from datetime import date

import pytest

from advtax import demo, storage
from advtax.engine import compute, load_rules

BY_NAME = {f.name: f for f in demo.client_folders()}


def test_six_client_folders_exist():
    assert len(BY_NAME) == 6
    assert (demo.DEMO_DIR / "templates" / "trial_balance_template.xlsx").exists()
    assert (demo.DEMO_DIR / "templates" / "capital_gains_template.xlsx").exists()


# Books to 31 Oct 2026 = 214 of 365 days; 151 days remain.
# Base books: income 1,21,39,000; expenses 1,04,93,000; opening stock 14,50,000; one-off income 1,20,000.
@pytest.mark.parametrize("folder,expected", [
    # 1,21,39,000 - 1,04,93,000 - 14,50,000 + 16,20,000 = 18,16,000 to date
    # 18,16,000 / 214 x 151 = 12,81,383; + 1,20,000 one-off = 32,17,383; + 45,000 - 30,000 = 32,32,383
    ("D01 Marudhar Hardware Stores", 3232383),
    # half-size books: 9,08,000 to date; / 214 x 151 = 6,40,692; + 60,000 = 16,08,692
    ("D04 S Verma HUF", 1608692),
    # double-size books: 36,32,000 to date; / 214 x 151 = 25,62,766; + 2,40,000 = 64,34,766; - 6,00,000 = 58,34,766
    ("D05 Demo Traders Firm", 5834766),
    # receipts 21,40,000 / 214 x 365 = 36,50,000 at 50% = 18,25,000
    ("D02 Dr A Mehta", 1825000),
    ("D03 Mrs K Iyer", 0),
    ("D06 Demo Textiles LLP", 4250000),
])
def test_business_income(folder, expected):
    assert demo.build(BY_NAME[folder])["inputs"].business_income == expected


@pytest.mark.parametrize("folder,stcg_eq,ltcg_eq,ltcg_ot,stcg_ot", [
    # broker: equity short -30,000 + 12,000 = -18,000 set off against the debt fund 45,000 -> 27,000;
    # equity long 60,000; gold held over 24 months 90,000; F&O row left out
    ("D02 Dr A Mehta", 0, 60000, 90000, 27000),
    # fund app (term column): equity long 1,80,000 - 20,000; equity short 25,000; debt fund 15,000 at slab
    ("D03 Mrs K Iyer", 25000, 160000, 0, 15000),
    # plot 41,00,000 - 25,00,000 - 1,00,000 = 15,00,000 long; unlisted shares -2,00,000 short, set off -> 13,00,000
    ("D06 Demo Textiles LLP", 0, 0, 1300000, 0),
    ("D01 Marudhar Hardware Stores", 0, 0, 0, 0),
])
def test_capital_gains(folder, stcg_eq, ltcg_eq, ltcg_ot, stcg_ot):
    i = demo.build(BY_NAME[folder])["inputs"]
    assert (i.stcg_equity, i.ltcg_equity, i.ltcg_other, i.stcg_other) == (stcg_eq, ltcg_eq, ltcg_ot, stcg_ot)


@pytest.mark.parametrize("folder,tds", [
    ("D01 Marudhar Hardware Stores", 4200 + 3000), ("D02 Dr A Mehta", 120000 + 60000), ("D03 Mrs K Iyer", 210000),
    ("D04 S Verma HUF", 36000), ("D05 Demo Traders Firm", 6000 + 15000), ("D06 Demo Textiles LLP", 0)])
def test_tds_from_26as(folder, tds):
    assert demo.build(BY_NAME[folder])["inputs"].tds_tcs == tds


def test_loading_saves_clients_trial_balances_and_26as(tmp_path, monkeypatch):
    monkeypatch.setenv("ADVTAX_DATA_DIR", str(tmp_path))
    con = storage.connect()
    names = demo.load_demo_folder(con)
    assert len(names) == 6 and len(storage.list_clients(con)) == 6
    assert storage.counts(con)["trial_balances"] == 3
    tb = storage.get_trial_balance(con, "D04 S. Verma HUF - Demo")
    assert tb["filename"] == "trial_balance_busy.csv" and len(tb["ledgers"]) == 24
    assert storage.get_client(con, "D05 Demo Traders (Partnership Firm) - Demo")["working"]["mobile"] == "0000000005"
    assert len(list((tmp_path / "26AS").glob("*/26AS (demo).txt"))) == 5
    assert len(demo.load_demo_folder(con)) == 6 and len(storage.list_clients(con)) == 6  # loading again does not duplicate
    rules = load_rules()
    for c in storage.list_clients(con):
        from advtax.engine import ClientInputs
        result = compute(ClientInputs.from_dict(c["inputs"]), rules, date(2026, 11, 27))
        assert result["chosen"]["total_tax"] > 0
