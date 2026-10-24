import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import engine as E  # noqa: E402
import interest as X  # noqa: E402

FLAT = pd.DataFrame({"Effective From": pd.to_datetime(["2020-01-01"]), "Bank Rate %": [5.75]})
R = 3 * 0.0575


def test_monthly_rest_compounding_matches_hand_calc():
    got, last = X.bill_interest(100000, "2026-07-17", "2026-08-31", [], FLAT)
    jul = 100000 * R / 365 * 15                     # 17-31 Jul
    aug = (100000 + jul) * R / 365 * 31             # July interest capitalised at month end
    assert got == pytest.approx(jul + aug, abs=0.01) and last == pd.Timestamp("2026-08-31")


def test_interest_within_single_month_is_simple():
    got, _ = X.bill_interest(50000, "2026-09-05", "2026-09-30", [], FLAT)
    assert got == pytest.approx(50000 * R / 365 * 26, abs=0.01)


def test_partial_payment_reduces_principal_after_payment_day():
    got, _ = X.bill_interest(100000, "2026-09-01", "2026-09-30", [(pd.Timestamp("2026-09-10"), 40000)], FLAT)
    assert got == pytest.approx(100000 * R / 365 * 10 + 60000 * R / 365 * 20, abs=0.01)


def test_full_payment_stops_interest():
    got, last = X.bill_interest(100000, "2026-09-01", "2026-09-30", [(pd.Timestamp("2026-09-10"), 100000)], FLAT)
    assert got == pytest.approx(100000 * R / 365 * 10, abs=0.01) and last == pd.Timestamp("2026-09-10")


def test_rate_change_mid_month():
    rates = pd.DataFrame({"Effective From": pd.to_datetime(["2020-01-01", "2026-09-16"]), "Bank Rate %": [5.50, 6.00]})
    got, _ = X.bill_interest(100000, "2026-09-01", "2026-09-30", [], rates)
    assert got == pytest.approx(100000 * 3 * 0.055 / 365 * 15 + 100000 * 3 * 0.06 / 365 * 15, abs=0.01)


def _res(bill_rows, pay_rows=None):
    m, _ = E.standardise(pd.DataFrame({"Vendor Name": ["Micro Co", "Med Co"], "MSME Category": ["Micro", "Medium"]}), "vendor_master")
    b, _ = E.standardise(pd.DataFrame(bill_rows, columns=["Bill No", "Vendor Name", "Bill Date", "Bill Amount"]), "bills")
    p = None
    if pay_rows:
        p, _ = E.standardise(pd.DataFrame(pay_rows, columns=["Vendor Name", "Payment Date", "Amount Paid", "Bill No"]), "payments")
    return E.build_ledger(b, p, m, "2026-09-30")


def test_compute_interest_only_covered_and_only_late():
    res = _res([["1", "Micro Co", "01-07-2026", 100000],      # due 16 Jul, open at 30 Sep
                ["2", "Micro Co", "01-09-2026", 100000],      # due 16 Sep, open
                ["3", "Med Co", "01-07-2026", 100000],        # not covered
                ["4", "Micro Co", "01-07-2026", 50000]],      # paid on time -> no interest
               [["Micro Co", "10-07-2026", 50000, "4"]])
    d = X.compute_interest(res, "2026-09-30", FLAT)
    assert set(d["Bill No"]) == {"1", "2"}
    row1 = d[d["Bill No"] == "1"].iloc[0]
    exp, _ = X.bill_interest(100000, "2026-07-17", "2026-09-30", [], FLAT)
    assert row1["Interest Payable"] == pytest.approx(exp) and row1["Status"] == "Open" and row1["Days"] == 76


def test_paid_late_bill_accrues_until_payment_date():
    res = _res([["1", "Micro Co", "01-07-2026", 100000]], [["Micro Co", "05-08-2026", 100000, "1"]])
    d = X.compute_interest(res, "2026-09-30", FLAT).iloc[0]
    assert d["Status"] == "Paid late" and d["Interest To"] == pd.Timestamp("2026-08-05") and d["Days"] == 20
    assert d["Interest Payable"] == pytest.approx(100000 * R / 365 * 15 + (100000 + 100000 * R / 365 * 15) * R / 365 * 5, abs=0.01)


def test_vendor_summary_and_rate_table_cleaning():
    res = _res([["1", "Micro Co", "01-07-2026", 100000], ["2", "Micro Co", "01-08-2026", 100000]])
    s = X.vendor_summary(X.compute_interest(res, "2026-09-30", FLAT))
    assert len(s) == 1 and s.loc[0, "Bills"] == 2
    messy = pd.DataFrame({"Effective From": ["07-10-2026", "04-05-2022", None], "Bank Rate %": ["5.75", 4.65, 9]})
    c = X.clean_rates(messy)
    assert list(c["Bank Rate %"]) == [4.65, 5.75] and c["Effective From"].is_monotonic_increasing
    with pytest.raises(ValueError):
        X.clean_rates(pd.DataFrame({"Effective From": [None], "Bank Rate %": [None]}))


def test_parse_bank_rate_from_home_page_html():
    import interest
    html = ("<div>Policy Repo Rate</div><div>5.50%</div><script>var Bank Rate 9%</script>"
            "<td>Marginal Standing Facility Rate</td><td>5.75%</td><td>Bank Rate</td><td>: 5.75 %</td>"
            "<td>Base Rate</td><td>8.40%-10.00%</td>")
    assert interest.parse_bank_rate(html) == 5.75
    assert interest.parse_bank_rate("<p>nothing here</p>") is None


def test_saved_rate_table_round_trips_dates(tmp_path, monkeypatch):
    import pandas as pd, interest, store
    monkeypatch.setattr(store, "ROOT", tmp_path / "companies")
    df = pd.DataFrame({"Effective From": [pd.Timestamp("2026-10-07"), pd.Timestamp("2026-12-05")], "Bank Rate %": [5.75, 5.5]})
    store.save_bank_rates(df)
    got = store.load_bank_rates()
    assert list(got["Effective From"]) == [pd.Timestamp("2026-10-07"), pd.Timestamp("2026-12-05")]
    out = interest.clean_rates(pd.DataFrame({"Effective From": ["07-10-2026", "2026-12-05"], "Bank Rate %": [5.75, 5.5]}))
    assert list(out["Effective From"]) == [pd.Timestamp("2026-10-07"), pd.Timestamp("2026-12-05")]
