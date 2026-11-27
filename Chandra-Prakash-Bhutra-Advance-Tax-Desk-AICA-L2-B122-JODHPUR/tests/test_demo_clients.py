"""The 20 demo clients, each checked against a hand-worked computation.

Position date for all: 22 Nov 2026 (June and September instalments passed,
December instalment next). Figures below are worked independently of the
engine; the arithmetic is written out so it can be re-performed.

Columns: regime used, total tax, advance tax for the year (after TDS/TCS),
liable?, amount to pay now, interest for deferment already arisen.
"""
from datetime import date

import pytest

from advtax.engine import compute, load_rules
from advtax.projection import project_presumptive
from seed_demo import DEMO

R = load_rules()
AS_ON = date(2026, 11, 22)
CESS = 1.04

EXPECTED = {
    # 01 New: HP (1,80,000-6,000) x 70% = 1,21,800; income 20,26,800;
    #    tax 2,00,000 + 26,800 x 25% = 2,06,700; x 1.04 = 2,14,968. Less TDS 18,000 = 1,96,968.
    #    Jun 29,545 and Sep 88,636 covered (30,000 / 90,000). Dec 75% = 1,47,726 - 90,000 = 57,726.
    "01": ("new", 214968, 196968, True, 57726, 0),
    # 02 Old is lower: salary 14,50,000 - HP loss 2,00,000 + interest 60,000 - deductions 4,50,000 = 8,60,000;
    #    tax 12,500 + 3,60,000 x 20% = 84,500; LTCG (3,25,000-1,25,000) x 12.5% = 25,000; 1,09,500 x 1.04 = 1,13,880.
    #    (New: 14,85,000 -> 1,02,750 + 25,000 = 1,27,750 x 1.04 = 1,32,860.)  Net of TDS 60,000 = 53,880.
    #    Nothing paid: Jun 8,082 -> 8,000 x 3% = 240; Sep 24,246 -> 24,200 x 3% = 726. Dec 40,410.
    "02": ("old", 113880, 53880, True, 40410, 966),
    # 03 Old (fixed), senior: 9,00,000 + 1,20,000 - 1,50,000 = 8,70,000;
    #    2,00,000 x 5% + 3,70,000 x 20% = 84,000 x 1.04 = 87,360.
    #    Jun 13,104 covered by 15,000. Sep 39,312 - 15,000 = 24,312 -> 24,300 x 3% = 729. Dec 65,520 - 15,000.
    "03": ("old", 87360, 87360, True, 50520, 729),
    # 04 New, senior without business: HP 2,90,000 x 70% = 2,03,000; income 16,03,000;
    #    1,20,000 + 3,000 x 20% = 1,20,600 x 1.04 = 1,25,424. Not liable to advance tax.
    "04": ("new", 125424, 125424, False, 0, 0),
    # 05 New, super senior with business: income 16,00,000 -> 1,20,000 x 1.04 = 1,24,800.
    #    Jun 18,720 and Sep 56,160 covered (20,000 / 60,000). Dec 93,600 - 60,000.
    "05": ("new", 124800, 124800, True, 33600, 0),
    # 06 New, presumptive profession: receipts 37,96,000 x 50% = 18,98,000 + dividend 65,000 = 19,63,000;
    #    1,20,000 + 3,63,000 x 20% = 1,92,600; STCG 1,50,000 x 20% = 30,000; LTCG 1,95,000 x 12.5% = 24,375;
    #    2,46,975 x 1.04 = 2,56,854. Less TDS 1,90,000 = 66,854, all due by 15 March.
    "06": ("new", 256854, 66854, True, 66854, 0),
    # 07 New, presumptive trader: turnover 2,37,25,000 x 6% = 14,23,500 + 30,000 = 14,53,500;
    #    60,000 + 2,53,500 x 15% = 98,025 x 1.04 = 1,01,946, all due by 15 March.
    "07": ("new", 101946, 101946, True, 101946, 0),
    # 08 New: income 75,00,000; 3,00,000 + 51,00,000 x 30% = 18,30,000; surcharge 10% = 1,83,000;
    #    20,13,000 x 1.04 = 20,93,520. Less TDS 1,50,000 = 19,43,520.
    #    Jun 2,91,528 covered. Sep 8,74,584 - 3,00,000 (second challan paid late on 20 Sep) = 5,74,584
    #    -> 5,74,500 x 3% = 17,235. Dec 14,57,640 - 8,00,000.
    "08": ("new", 2093520, 1943520, True, 657640, 17235),
    # 09 New: normal 1,80,00,000 -> 3,00,000 + 1,56,00,000 x 30% = 49,80,000; STCG 10,00,000 x 20% = 2,00,000;
    #    LTCG 90,00,000 x 12.5% = 11,25,000; total 63,05,000. Surcharge capped at 15% (income excluding
    #    gains is below 2 crore) = 9,45,750; 72,50,750 x 1.04 = 75,40,780. Less TDS 2,00,000 = 73,40,780.
    #    Jun paid 11,00,000 (>= 12%) and Sep 33,00,000 (>= 36%): no interest. Dec 55,05,585 - 33,00,000.
    "09": ("new", 7540780, 7340780, True, 2205585, 0),
    # 10 New: salary 12,80,000 - 75,000 = 12,05,000; marginal relief limits tax to 5,000; x 1.04 = 5,200.
    #    Below Rs 10,000: no advance tax.
    "10": ("new", 5200, 5200, False, 0, 0),
    # 11 New, non-resident (no rebate): HP 9,40,000 x 70% - 1,50,000 = 5,08,000 + 1,00,000 = 6,08,000;
    #    2,08,000 x 5% = 10,400; LTCG 20,00,000 x 12.5% = 2,50,000; 2,60,400 x 1.04 = 2,70,816.
    #    Less TDS 1,20,000 = 1,50,816. Jun 22,622 -> 22,600 x 3% = 678; Sep 67,867 -> 67,800 x 3% = 2,034.
    #    Dec 1,13,112.
    "11": ("new", 270816, 150816, True, 113112, 2712),
    # 12 New: salary 17,25,000; business loss 3,00,000 absorbs interest 1,00,000, balance not set off
    #    against salary; 1,20,000 + 1,25,000 x 20% = 1,45,000 x 1.04 = 1,50,800. Less TDS 1,20,000 = 30,800.
    #    Jun 4,620 -> 4,600 x 3% = 138; Sep 13,860 -> 13,800 x 3% = 414. Dec 23,100.
    "12": ("new", 150800, 30800, True, 23100, 552),
    # 13 New: 24,00,000 -> 3,00,000 x 1.04 = 3,12,000. Paid 46,800 / 1,40,400 / 2,34,000 on time: nothing due.
    "13": ("new", 312000, 312000, True, 0, 0),
    # 14 HUF, new (no rebate): HP 3,48,000 x 70% - 90,000 = 1,53,600; income 9,58,600;
    #    20,000 + 1,58,600 x 10% = 35,860 x 1.04 = 37,294. Jun 5,594 -> 5,500 x 3% = 165;
    #    Sep 16,782 -> 16,700 x 3% = 501. Dec 27,970.
    "14": ("new", 37294, 37294, True, 27970, 666),
    # 15 HUF, old (fixed): 12,00,000 - 2,00,000 = 10,00,000 -> 1,12,500; LTCG 75,000 x 12.5% = 9,375;
    #    1,21,875 x 1.04 = 1,26,750. Jun 19,013 and Sep 57,038 covered. Dec 95,062 - 60,000.
    "15": ("old", 126750, 126750, True, 35062, 0),
    # 16 Firm: 29,00,000 x 30% = 8,70,000 x 1.04 = 9,04,800. Less TDS 40,000 = 8,64,800.
    #    Jun 1,29,720 - 1,00,000 = 29,720 (below 12% safe limit of 1,03,776) -> 29,700 x 3% = 891.
    #    Sep 3,89,160 - 3,50,000: paid >= 36% (3,11,328), no interest. Dec 6,48,600 - 3,50,000.
    "16": ("firm", 904800, 864800, True, 298600, 891),
    # 17 Firm above 1 crore: 1,02,00,000 x 30% = 30,60,000 + 12% = 34,27,200, limited by marginal relief to
    #    30,00,000 + 2,00,000 = 32,00,000; x 1.04 = 33,28,000. Less TDS 1,00,000 = 32,28,000.
    #    Jun 4,84,200 and Sep 14,52,600 covered. Dec 24,21,000 - 14,55,000.
    "17": ("firm", 3328000, 3228000, True, 966000, 0),
    # 18 Firm, presumptive: turnover 1,46,00,000 x 8% = 11,68,000 x 30% = 3,50,400 x 1.04 = 3,64,416 by 15 March.
    "18": ("firm", 364416, 364416, True, 364416, 0),
    # 19 LLP: 43,60,000 x 30% = 13,08,000 + LTCG 6,00,000 x 12.5% = 75,000; 13,83,000 x 1.04 = 14,38,320.
    #    Less TDS 95,000 = 13,43,320. Jun 2,01,498: paid 2,00,000 (>= 12%). Sep 6,04,494 - 2,00,000
    #    -> 4,04,400 x 3% = 12,132. Dec 10,07,490 - 2,00,000.
    "19": ("firm", 1438320, 1343320, True, 807490, 12132),
    # 20 LLP with business loss larger than interest income: nil tax.
    "20": ("firm", 0, 0, False, 0, 0),
}


def test_at_least_15_clients_of_every_type():
    kinds = [inp.constitution for inp, _ in DEMO]
    assert len(DEMO) >= 15 and len(DEMO) == len(EXPECTED)
    assert {"Individual", "HUF", "Firm", "LLP"} <= set(kinds)


@pytest.mark.parametrize("inp,working", DEMO, ids=[i.name[:2] for i, _ in DEMO])
def test_demo_client(inp, working):
    regime, total_tax, net, liable, pay_now, interest = EXPECTED[inp.name[:2]]
    res = compute(inp, R, AS_ON)
    assert res["chosen_key"] == regime
    assert res["chosen"]["total_tax"] == total_tax
    assert res["net_liability"] == net
    assert res["liable"] is liable
    nd = res["schedule"]["next_due"]
    assert (nd["pay_now"] if liable else 0) == pytest.approx(pay_now, abs=1)
    assert res["schedule"]["interest_incurred"] == interest
    expected_due = date(2027, 3, 15) if inp.presumptive else date(2026, 12, 15)
    assert nd["date"] == expected_due


@pytest.mark.parametrize("inp,working", [d for d in DEMO if d[0].presumptive], ids=lambda x: getattr(x, "name", "")[:2])
def test_presumptive_working_reproduces_the_income(inp, working):
    p = project_presumptive(working["f_turnover"], working["f_presumptive_rate"], date(2026, 4, 1),
                            date.fromisoformat(working["f_books_date"]), date(2027, 3, 31))
    assert p["projected_business_income"] == inp.business_income


def test_cess_factor_used_in_workings():
    assert CESS == 1 + R["cess"]
