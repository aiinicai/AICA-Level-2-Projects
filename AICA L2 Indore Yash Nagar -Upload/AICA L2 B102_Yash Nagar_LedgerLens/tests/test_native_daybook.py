import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "samples"))

import make_native_daybook  # noqa: E402
import make_sample  # noqa: E402
from daybook_auditor import narration as N  # noqa: E402
from daybook_auditor import rules  # noqa: E402
from daybook_auditor.parser import load_daybook  # noqa: E402

CFG = rules.Config(fy_start=date(2025, 4, 1), fy_end=date(2026, 3, 31))
EXPECTED = list(make_sample.numbered())


def native(educational=True):
    buf = io.BytesIO()
    make_native_daybook.build(educational=educational).save(buf)
    return load_daybook("tally_daybook_export.xlsx", buf.getvalue())


@pytest.fixture(scope="module")
def masked():
    return native(True)


@pytest.fixture(scope="module")
def open_dates():
    return native(False)


def vouchers_of(df):
    return df.groupby("voucher_id", sort=True).agg(date=("date", "first"), vtype=("vch_type", "first"), no=("vch_no", "first"),
                                                   narration=("narration", "first"), dr=("amount", lambda s: 0.0))


# ------------------------------------------------------------------ reading Tally's real layout
def test_every_voucher_line_and_narration_survives(masked):
    df, meta = masked
    assert meta["vouchers"] == len(EXPECTED) and meta["ledger_level"]
    for vid, (d, vtype, no, narr, lines) in zip(sorted(df["voucher_id"].unique()), EXPECTED):
        g = df[df["voucher_id"] == vid]
        assert (g["vch_type"].iloc[0], g["vch_no"].iloc[0], g["narration"].iloc[0]) == (vtype, str(no), narr)
        assert sorted(zip(g["ledger"], g["side"], g["amount"].round(2))) == sorted((l, s, round(float(a), 2)) for l, a, s in lines)


def test_file_order_is_kept_so_numbers_stay_in_sequence(masked):
    df, _ = masked
    first = df.groupby("voucher_id").first()
    assert list(zip(first["vch_type"], first["vch_no"])) == [(t, str(n)) for _, t, n, _, _ in EXPECTED]


def test_hidden_dates_are_unknown_not_borrowed_from_the_previous_voucher(masked):
    df, meta = masked
    first = df.groupby("voucher_id").first().reset_index()
    shown = [d.day in make_native_daybook.SHOWN_DAYS for d, *_ in EXPECTED]
    assert meta["undated"] == shown.count(False) and meta["date_label"] == "Educational"
    for ok, (d, *_), got in zip(shown, EXPECTED, first["date"]):
        if ok:
            assert got.date() == d
        else:
            assert pd.isna(got), f"a hidden date was filled in as {got}"
    assert 3 <= shown.count(True) <= 12                    # the fixture really mixes shown and hidden dates


def test_when_dates_are_shown_nothing_is_undated(open_dates):
    df, meta = open_dates
    assert meta["undated"] == 0 and df["date"].notna().all()
    first = df.groupby("voucher_id").first()
    assert [x.date() for x in first["date"]] == [d for d, *_ in EXPECTED]


# ------------------------------------------------------------------ the tests behave honestly with hidden dates
def findings(pair):
    df, meta = pair
    return rules.run_rules(df, CFG, meta["ledger_level"])


def test_hidden_dates_are_one_finding_not_hundreds(masked):
    f = findings(masked)
    assert (f["rule"] == rules.R_UNDATED).sum() == 1
    assert not (f["detail"] == "Voucher has no valid date.").any()


def test_negative_cash_is_not_reported_from_a_partial_picture(masked, open_dates):
    assert rules.R_NEG_CASH not in set(findings(masked)["rule"])
    assert rules.R_NEG_CASH in set(findings(open_dates)["rule"])              # with dates, the seeded overdraw is found


def test_cash_split_is_aggregated_by_day_only_when_the_day_is_known(masked, open_dates):
    split_masked = findings(masked)
    assert not (split_masked["ledger"] == "Verma Transport").any() or \
        split_masked[split_masked["ledger"] == "Verma Transport"]["rule"].eq(rules.R_CASH_NEAR).all()
    near = split_masked[(split_masked["rule"] == rules.R_CASH_NEAR) & (split_masked["ledger"] == "Verma Transport")]
    assert len(near) == 3                                                       # three 9,500 payments, each tested alone
    agg = findings(open_dates)
    row = agg[(agg["rule"] == rules.R_CASH_PAY) & (agg["ledger"] == "Verma Transport")]
    assert len(row) == 1 and row.iloc[0]["amount"] == 28_500                    # one day's total once dates are visible


def test_a_big_cash_payment_is_still_caught_without_dates(masked):
    f = findings(masked)
    row = f[(f["rule"] == rules.R_CASH_PAY) & (f["ledger"] == "Sharma Traders")]
    assert len(row) >= 1 and (row["amount"] >= 45_000).any()


def test_the_date_independent_tests_all_still_run(masked):
    got = set(findings(masked)["rule"])
    assert {rules.R_IMBAL, rules.R_TDS, rules.R_GST, rules.R_SUSP, N.R_NEAR} <= got
    assert N.R_REPEAT not in got                     # needs real dates, so it correctly does not run on hidden ones
    for label in ("Fraud or misappropriation wording", "Bribe or illegal payment wording", "Gift or hospitality",
                  "Penalty, fine or late fee", "Donation, charity, CSR or political contribution", "Entry made on instruction"):
        assert N.R_NARR_PREFIX + label in got, label


def test_weekend_test_only_looks_at_dated_vouchers(masked):
    f = findings(masked)
    sunday = f[f["rule"] == rules.R_SUNDAY]
    assert sunday["date"].notna().all()


def test_repeated_amounts_are_found_once_dates_are_visible(open_dates):
    assert N.R_REPEAT in set(findings(open_dates)["rule"])


def test_the_seeded_payment_number_gap_is_still_found(masked):
    f = findings(masked)
    gap = f[(f["rule"] == rules.R_GAP) & (f["vch_type"] == "Payment")]
    assert len(gap) == 1 and "2 number(s) missing" in gap.iloc[0]["detail"]


# ------------------------------------------------------------------ voucher gaps on real-world numbering
def run_condensed(rows):
    """rows: (voucher type, number) or (voucher type, number, date text)."""
    csv = "Date,Particulars,Vch Type,Vch No.,Debit Amount,Credit Amount\n" + "\n".join(
        f"{r[2] if len(r) > 2 else '1-May-25'},P{i},{r[0]},{r[1]},6000," for i, r in enumerate(rows))
    df, meta = load_daybook("d.csv", csv.encode())
    return rules.run_rules(df, CFG, meta["ledger_level"])


def gaps(f):
    return f[f["rule"] == rules.R_GAP]


def test_interleaved_batches_with_every_number_present_are_not_gaps():
    nums = [1, 2, 9, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15, 8, 16]             # numbers 1-8 and 9-16 entered side by side
    assert gaps(run_condensed([("Payment", n) for n in nums])).empty


def test_real_gaps_are_reported_compactly_even_when_entered_out_of_order():
    nums = [1, 2, 3, 4, 5, 6, 7, 8, 16, 17, 18, 30, 31, 32, 33]                 # 9-15 and 19-29 are missing
    f = gaps(run_condensed([("Payment", n) for n in nums]))
    assert len(f) == 1 and "18 number(s) missing" in f.iloc[0]["detail"] and "9-15, 19-29" in f.iloc[0]["detail"]


def test_a_series_that_restarts_each_month_is_judged_within_each_run():
    nums = [1, 2, 3, 5, 6, 1, 2, 3, 4, 5]                                       # 4 missing in the first month only
    months = ["1-May-25"] * 5 + ["1-Jun-25"] * 5
    f = gaps(run_condensed([("Payment", n, m) for n, m in zip(nums, months)]))
    assert len(f) == 1 and "1 number(s) missing" in f.iloc[0]["detail"] and "4" in f.iloc[0]["detail"]


def test_a_complete_series_has_no_gap():
    assert gaps(run_condensed([("Sales", n) for n in range(1, 21)])).empty


# ------------------------------------------------------------------ the first row of a voucher is a real line
def detailed(rows):
    wb = Workbook()
    ws = wb.active
    for r in [["Date", "Particulars", "Vch Type", "Vch No.", "Debit", "Credit"]] + rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return load_daybook("d.xlsx", buf.getvalue())[0]


def test_an_unbalanced_voucher_is_reported_not_quietly_repaired():
    rows = []
    for n in range(1, 12):     # ten balanced vouchers, so the file clearly does not repeat totals on the first row
        rows += [["1-Apr-25", "A", "Journal", str(n), 100, None], [None, "B", None, None, 50, None], [None, "C", None, None, None, 150]]
    rows += [["1-Apr-25", "X", "Journal", "99", 500, None], [None, "Y", None, None, 500, None], [None, "Z", None, None, None, 1000 - 500 - 200]]
    df = detailed(rows)
    assert len(df[df["vch_no"] == "99"]) == 3                                   # nothing dropped
    f = rules.run_rules(df, CFG, True)
    assert (f["rule"] == rules.R_IMBAL).sum() == 1


def test_exports_that_repeat_the_total_on_the_first_row_are_still_corrected():
    rows = []
    for n in range(1, 6):      # every voucher shows its total first, then the lines
        rows += [["1-Apr-25", "Party", "Purchase", str(n), None, 150], [None, "Purchase", None, None, 100, None],
                 [None, "GST", None, None, 50, None], [None, "Party", None, None, None, 150]]
    df = detailed(rows)
    assert all(len(df[df["vch_no"] == str(n)]) == 3 for n in range(1, 6))
    assert rules.run_rules(df, CFG, True)["rule"].eq(rules.R_IMBAL).sum() == 0


# ------------------------------------------------------------------ the page
def test_the_page_explains_hidden_dates(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    f = tmp_path / "DayBook.xlsx"
    make_native_daybook.build().save(f)
    monkeypatch.setenv("DB_UPLOAD", str(f))
    monkeypatch.setenv("DB_PAGE", str(ROOT / "ui" / "day_book.py"))

    def page():
        import io
        import os
        from pathlib import Path

        import streamlit as st

        class Upload(io.BytesIO):
            name = "DayBook.xlsx"
        original = st.file_uploader
        st.file_uploader = lambda *a, **k: Upload(Path(os.environ["DB_UPLOAD"]).read_bytes())
        try:
            p = Path(os.environ["DB_PAGE"])
            exec(compile(p.read_text(encoding="utf-8"), "page", "exec"), {"__name__": "__main__", "__file__": str(p)})
        finally:
            st.file_uploader = original
    at = AppTest.from_function(page, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert any("date is hidden on" in w.value and "Educational" in w.value for w in at.warning)
    assert {m.label: m.value for m in at.metric}["Vouchers"] == str(len(EXPECTED))
