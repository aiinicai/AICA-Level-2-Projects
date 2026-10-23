import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "samples"))

import make_sample  # noqa: E402
from daybook_auditor import narration as N  # noqa: E402
from daybook_auditor.parser import load_daybook  # noqa: E402
from daybook_auditor.rules import Config, _mk, run_rules  # noqa: E402

CFG = Config(fy_start=date(2025, 4, 1), fy_end=date(2026, 3, 31))


def themes(text):
    return {t.id for t, _ in N.scan_narration(text)}


# ----------------------------------------------------------------------------- narration themes
@pytest.mark.parametrize("text,theme", [
    ("Amount recovered after fraud by storekeeper", "fraud"),
    ("Embezzlement by cashier detected", "fraud"),
    ("Bribe paid to inspector", "bribe"),
    ("Speed money to clear the consignment", "bribe"),
    ("Paid under the table for approval", "bribe"),
    ("Diwali gifts to customers", "gift"),
    ("Client hospitality, dinner and liquor", "gift"),
    ("Penalty paid for late filing of GSTR-3B", "penalty"),
    ("Late fee charged by ROC", "penalty"),
    ("Show cause notice response charges", "penalty"),
    ("Donation to Shree Ram Mandir Trust", "donation"),
    ("CSR contribution to school", "donation"),
    ("Entry passed as instructed by MD", "instructed"),
    ("Booked as per verbal instruction of director", "instructed"),
    ("On the direction of the chairman", "instructed"),
    ("Suspense balance transferred", "suspense"),
    ("Unexplained difference in bank reconciliation", "suspense"),
    ("Bad debts written off", "writeoff"),
    ("Dues waived by management", "writeoff"),
    ("Director's family holiday to Goa", "personal"),
    ("Personal expenses of director", "personal"),
    ("Loan to director for house purchase", "director_loan"),
    ("Paid without bill, bill to follow", "unsupported"),
    ("Settled in cash with the supplier", "cash_settle"),
    ("Back dated entry, correction entry", "correction"),
])
def test_each_theme_is_recognised(text, theme):
    assert theme in themes(text)


@pytest.mark.parametrize("text", [
    "No penalty was levied; interest paid on time",
    "Not a gift, purchase of stationery",
    "Without any penalty",
    "There was nil donation this month",
    "Never any bribe, only courier fees",
])
def test_negated_mentions_are_not_flagged(text):
    assert themes(text) == set() or not ({"penalty", "gift", "donation", "bribe"} & themes(text))


@pytest.mark.parametrize("text", [
    "Being purchase of raw material from Sharma Steel Traders vide invoice, GST @18% availed",
    "Being sale of finished goods (precision components) to Metro Auto Components Ltd",
    "Payment made through banking channel against standing instruction",
    "Salary for the month of March",
    "Being job work charges paid to Bright Engineering Works (installment 2)",
    "Presentation charges for the annual report",         # 'present' inside another word must not be a gift
    "Sonata hotel stay for site visit",                    # 'son' inside a word
])
def test_ordinary_narrations_raise_nothing_serious(text):
    assert not ({"fraud", "bribe", "gift", "penalty", "donation", "instructed", "personal"} & themes(text))


def test_a_negation_in_one_clause_does_not_hide_a_real_flag_in_the_next():
    assert "penalty" in themes("No bribe involved. Penalty paid for late filing")


def test_several_themes_in_one_narration_each_give_a_finding():
    assert {"instructed", "unsupported"} <= themes("Entry passed as instructed by MD; bill to follow")


def test_every_theme_has_a_reference_and_a_valid_severity():
    assert len(N.THEMES) >= 13 and len({t.id for t in N.THEMES}) == len(N.THEMES)
    assert all(t.reference and t.severity in ("High", "Medium", "Low") for t in N.THEMES)


# ----------------------------------------------------------------------------- the 999 / threshold test
def rec(total, vtype="Payment", narration="", no="1", day=1):
    return {"voucher_id": f"V{no}", "date": date(2025, 5, day), "vch_type": vtype, "vch_no": no, "narration": narration,
            "total": float(total), "dr_total": float(total), "cr_total": float(total),
            "dr_lines": [("Party", float(total))], "cr_lines": [("HDFC Bank", float(total))]}


def near(*amounts, vtype="Payment"):
    recs = [rec(a, vtype, no=str(i + 1)) for i, a in enumerate(amounts)]
    return N.threshold_findings(recs, CFG, _mk)


@pytest.mark.parametrize("amount", [9_999, 19_999, 29_999, 49_999, 99_999, 199_999, 59_999.50, 249_999])
def test_amounts_ending_in_999_are_flagged(amount):
    assert len(near(amount)) == 1


@pytest.mark.parametrize("amount", [9_800, 9_950.25, 29_500, 49_200, 196_000])
def test_amounts_just_under_a_threshold_are_flagged_as_medium(amount):
    f = near(amount)
    assert len(f) == 1 and f[0]["severity"] == "Medium" and "just under" in f[0]["detail"]


@pytest.mark.parametrize("amount", [10_000, 30_000, 200_000, 9_700, 12_345, 1_999, 999, 50_000.10, 150_000])
def test_amounts_at_or_well_clear_of_a_threshold_are_not_flagged(amount):
    assert near(amount) == []


def test_ends_in_999_but_not_near_a_limit_is_low():
    f = near(59_999)
    assert f[0]["severity"] == "Low" and "ends in 999" in f[0]["detail"] and "just under" not in f[0]["detail"]


def test_both_reasons_are_reported_in_one_finding():
    f = near(49_999)
    assert len(f) == 1 and "ends in 999" in f[0]["detail"] and "just under Rs 50,000" in f[0]["detail"]


def test_sales_and_contra_vouchers_are_not_tested():
    assert near(49_999, vtype="Sales") == [] and near(9_999, vtype="Contra") == []


def test_sensitivity_is_adjustable():
    wide = Config(CFG.fy_start, CFG.fy_end, near_threshold_pct=10)
    assert len(N.threshold_findings([rec(9_300)], wide, _mk)) == 1 and N.threshold_findings([rec(9_300)], CFG, _mk) == []


# ----------------------------------------------------------------------------- repeated amounts
def test_three_identical_amounts_to_one_party_in_a_month_are_flagged_once():
    recs = [rec(7_500, no=str(i), day=1 + 7 * i) for i in range(3)]
    f = N.repeated_findings(recs, CFG, _mk)
    assert len(f) == 1 and "3 times" in f[0]["detail"] and f[0]["amount"] == 7_500


def test_repeats_spread_over_many_months_or_below_the_floor_are_not_flagged():
    spread = [rec(7_500, no=str(i)) | {"date": date(2025, 4 + 2 * i, 1)} for i in range(3)]
    assert N.repeated_findings(spread, CFG, _mk) == []
    small = [rec(900, no=str(i), day=1 + i) for i in range(5)]
    assert N.repeated_findings(small, CFG, _mk) == []


# ----------------------------------------------------------------------------- Benford
def amounts_following_benford(n, seed=1):
    rng = random.Random(seed)
    return [10 ** rng.uniform(2, 6) for _ in range(n)]          # log-uniform values obey Benford's law


def test_benford_conforming_data_is_not_flagged():
    recs = [rec(a, no=str(i)) for i, a in enumerate(amounts_following_benford(600))]
    assert N.benford_findings(recs, CFG, _mk) == []


def test_data_with_an_invented_pattern_is_flagged():
    rng = random.Random(2)
    recs = [rec(rng.randint(5_000, 5_999) + 0.0, no=str(i)) for i in range(150)]      # everything starts with 5
    f = N.benford_findings(recs, CFG, _mk)
    assert len(f) == 1 and f[0]["severity"] == "Medium" and "5 (" in f[0]["detail"]


def test_benford_needs_enough_vouchers():
    assert N.benford_findings([rec(5_000 + i, no=str(i)) for i in range(40)], CFG, _mk) == []


# ----------------------------------------------------------------------------- end to end on the sample Day Book
@pytest.fixture(scope="module")
def sample_findings():
    df, meta = load_daybook("s.xml", make_sample.build().encode())
    return run_rules(df, CFG, meta["ledger_level"])


def rules_for(f, vch_type, vch_no):
    return set(f[(f["vch_type"] == vch_type) & (f["vch_no"] == str(vch_no))]["rule"])


def test_the_seeded_issues_are_all_found(sample_findings):
    got = set(sample_findings["rule"])
    for label in ("Fraud or misappropriation wording", "Bribe or illegal payment wording", "Gift or hospitality",
                  "Penalty, fine or late fee", "Donation, charity, CSR or political contribution",
                  "Entry made on instruction", "Suspense, plug or unexplained difference", "Personal or family spend",
                  "No supporting document", "Write-off or waiver"):
        assert N.R_NARR_PREFIX + label in got, label
    assert {N.R_NEAR, N.R_REPEAT} <= got


def test_the_negated_narration_is_not_flagged(sample_findings):
    f = sample_findings
    interest = f[f["detail"].str.contains("No penalty was levied", na=False)]
    assert interest.empty


def test_each_finding_carries_a_reference_and_the_words_that_triggered_it(sample_findings):
    n = sample_findings[sample_findings["rule"].str.startswith(N.R_NARR_PREFIX)]
    assert len(n) >= 10 and (n["reference"].str.len() > 20).all() and n["detail"].str.contains("narration says '").all()


def test_findings_on_the_original_sample_are_unchanged_by_the_new_tests():
    df, meta = load_daybook("s.xml", make_sample.build(extra=False).encode())
    base = run_rules(df, Config(CFG.fy_start, CFG.fy_end, run_narration_tests=False), meta["ledger_level"])
    with_tests = run_rules(df, CFG, meta["ledger_level"])
    old = with_tests[~with_tests["rule"].str.startswith((N.R_NARR_PREFIX, N.R_NEAR, N.R_REPEAT, N.R_BENFORD))]
    assert len(old) == len(base)


def test_narration_tests_can_be_switched_off():
    df, meta = load_daybook("s.xml", make_sample.build().encode())
    f = run_rules(df, Config(CFG.fy_start, CFG.fy_end, run_narration_tests=False), meta["ledger_level"])
    assert not f["rule"].str.startswith((N.R_NARR_PREFIX, N.R_NEAR, N.R_REPEAT, N.R_BENFORD)).any()


def test_narration_tests_work_on_a_condensed_export_where_ledger_rules_cannot():
    csv = ("Date,Particulars,Vch Type,Vch No.,Debit Amount,Credit Amount,Narration\n"
           "1-May-25,Cash,Payment,1,18433.43,,Being cash payment of Rs.18433.43 made to Precision Tools Suppliers\n"
           "2-May-25,HDFC Bank,Payment,2,148069.25,,Payment to Cox & Kings for the Director's family visit to Singapore\n"
           "3-May-25,HDFC Bank,Payment,3,49999,,Consultancy fee paid in full\n")
    df, meta = load_daybook("daybook.csv", csv.encode())
    assert not meta["ledger_level"]
    f = run_rules(df, CFG, meta["ledger_level"])
    cash = f[f["rule"] == N.R_NARR_PREFIX + "Cash settlement wording"]
    assert len(cash) == 1 and cash.iloc[0]["severity"] == "Medium" and "exceeds the Rs 10,000 limit" in cash.iloc[0]["detail"]
    assert N.R_NARR_PREFIX + "Personal or family spend" in set(f["rule"])
    assert N.R_NEAR in set(f["rule"])


# ----------------------------------------------------------------------------- real narrations from the sample company's Tally
@pytest.mark.parametrize("text,expected", [
    ("Being payment made to Cox & Kings Travel for air tickets and hotel booking - Director's family visit to Singapore.", {"personal"}),
    ("Being purchase of ball bearings and precision components from Bright Bearings Co. (Udyam Registered - Micro Enterprise) vide their Invoice.", {"msme"}),
    ("Being consultancy fee paid to Kavita Sharma & Associates for process improvement study, full amount remitted.", {"no_tds"}),
    ("Being legal & professional charges paid/payable to Verma Legal Associates, TDS deducted @2% and remitted; balance paid through bank.", set()),
    ("Being consultancy fee paid to R.K. Financial Consultants, TDS deducted @10% u/s 194J and remitted; balance paid through bank.", set()),
    ("Being job work charges paid to Bright Engineering Works (installment 2).", set()),
    ("Being GST input credit set off against output tax liability and net GST paid for the period.", set()),
    ("Being discount received from supplier adjusted against outstanding balance.", set()),
    ("Being payment made to Precision Engineering Machines Pvt Ltd for supply and installation of a new CNC lathe machine at the factory.", set()),
    ("Being payment made to Cool Comfort Appliances for supply and installation of split air-conditioners in the office.", set()),
    ("Being amount received from Metro Auto Components Ltd against outstanding sales invoices through banking channel.", set()),
])
def test_real_narrations_from_the_sample_company(text, expected):
    risky = {"fraud", "bribe", "gift", "penalty", "donation", "instructed", "suspense", "writeoff", "personal", "director_loan",
             "unsupported", "msme", "no_tds", "correction"}
    assert themes(text) & risky == expected


def test_the_cash_wording_theme_is_silent_when_ledger_lines_exist_and_speaks_when_they_do_not():
    r = rec(18_433.43, narration="Being cash payment of Rs.18,433.43 made to Precision Tools Suppliers")
    assert N.narration_findings([r], CFG, True, _mk) == []
    f = N.narration_findings([r], CFG, False, _mk)
    assert len(f) == 1 and f[0]["severity"] == "Medium"
