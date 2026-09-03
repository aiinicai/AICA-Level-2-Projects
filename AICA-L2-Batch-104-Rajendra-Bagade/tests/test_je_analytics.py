"""Journal entry testing under SA 240."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from auditlens.je_analytics import (
    BENFORD_EXPECTED,
    benford_first_digit,
    run_all_tests,
    test_backdated_entries as backdated,
    test_period_end_concentration as period_end,
    test_round_amounts as round_amounts,
    test_seldom_used_combinations as seldom_used,
    test_unusual_users as unusual_users,
    test_weekend_and_holiday as weekend_holiday,
)


def make_gl(rows: list[dict]) -> pd.DataFrame:
    """Build a two-line journal for each supplied entry."""
    lines = []
    for r in rows:
        for dr, cr, acct in (
            (r["amount"], 0.0, r.get("debit_account", "Other expenses")),
            (0.0, r["amount"], r.get("credit_account", "Bank")),
        ):
            lines.append(
                {
                    "entry_id": r["entry_id"],
                    "posting_date": pd.Timestamp(r["posting_date"]),
                    "entry_date": pd.Timestamp(r.get("entry_date", r["posting_date"])),
                    "account_code": "9000",
                    "account_name": acct,
                    "debit": dr,
                    "credit": cr,
                    "narration": r.get("narration", "Test entry"),
                    "posted_by": r.get("posted_by", "priya.sharma"),
                }
            )
    return pd.DataFrame(lines)


# --------------------------------------------------------------------------
# Individual routines
# --------------------------------------------------------------------------

def test_round_sum_entries_are_selected():
    gl = make_gl([
        {"entry_id": "J1", "amount": 500000.00, "posting_date": "2024-06-11"},   # round
        {"entry_id": "J2", "amount": 487613.42, "posting_date": "2024-06-11"},   # not round
        {"entry_id": "J3", "amount": 2500000.00, "posting_date": "2024-06-11"},  # round
        {"entry_id": "J4", "amount": 50000.00, "posting_date": "2024-06-11"},    # below threshold
    ])
    flagged = {f.entry_id for f in round_amounts(gl).flags}
    assert flagged == {"J1", "J3"}


def test_weekend_and_holiday_postings_are_selected():
    gl = make_gl([
        {"entry_id": "J1", "amount": 100000, "posting_date": "2024-06-15"},  # Saturday
        {"entry_id": "J2", "amount": 100000, "posting_date": "2024-06-16"},  # Sunday
        {"entry_id": "J3", "amount": 100000, "posting_date": "2024-06-18"},  # Tuesday
        {"entry_id": "J4", "amount": 100000, "posting_date": "2024-08-15"},  # holiday
    ])
    result = weekend_holiday(gl, holidays={date(2024, 8, 15)})
    flagged = {f.entry_id for f in result.flags}
    assert flagged == {"J1", "J2", "J4"}
    assert any("holiday" in f.reason for f in result.flags)


def test_period_end_material_entries_are_selected():
    gl = make_gl([
        {"entry_id": "J1", "amount": 5000000, "posting_date": "2025-03-29"},  # material, in window
        {"entry_id": "J2", "amount": 10000, "posting_date": "2025-03-29"},    # in window, immaterial
        {"entry_id": "J3", "amount": 5000000, "posting_date": "2024-11-15"},  # material, outside
    ])
    result = period_end(gl, date(2025, 3, 31), window_days=7, materiality=1000000)
    assert {f.entry_id for f in result.flags} == {"J1"}
    assert result.flags[0].severity == "elevated"


def test_backdated_entries_are_selected():
    gl = make_gl([
        {"entry_id": "J1", "amount": 100000, "posting_date": "2024-12-20", "entry_date": "2025-03-05"},
        {"entry_id": "J2", "amount": 100000, "posting_date": "2024-12-20", "entry_date": "2024-12-22"},
    ])
    result = backdated(gl, tolerance_days=30)
    assert {f.entry_id for f in result.flags} == {"J1"}


def test_backdated_test_is_skipped_without_a_timestamp():
    gl = make_gl([{"entry_id": "J1", "amount": 100000, "posting_date": "2024-12-20"}])
    result = backdated(gl.drop(columns=["entry_date"]))
    assert result.flags == []
    assert "Not performed" in result.description


def test_seldom_used_combinations_are_selected():
    rows = [
        {"entry_id": f"J{i}", "amount": 100000, "posting_date": "2024-06-11",
         "debit_account": "Purchases", "credit_account": "Trade payables"}
        for i in range(10)
    ]
    rows.append({
        "entry_id": "JX", "amount": 3800000, "posting_date": "2025-03-29",
        "debit_account": "Surplus in Statement of Profit and Loss",
        "credit_account": "Provision for doubtful debts",
    })
    result = seldom_used(make_gl(rows), max_occurrences=2)
    assert {f.entry_id for f in result.flags} == {"JX"}


def test_infrequent_users_are_selected():
    rows = [
        {"entry_id": f"J{i}", "amount": 100000, "posting_date": "2024-06-11",
         "posted_by": "priya.sharma"}
        for i in range(99)
    ]
    rows.append({"entry_id": "JX", "amount": 900000, "posting_date": "2025-03-20",
                 "posted_by": "s.venkatesh"})
    result = unusual_users(make_gl(rows), min_share=0.02)
    assert {f.entry_id for f in result.flags} == {"JX"}


# --------------------------------------------------------------------------
# Benford
# --------------------------------------------------------------------------

def test_benford_expected_frequencies():
    assert BENFORD_EXPECTED[1] == pytest.approx(0.30103, abs=1e-5)
    assert BENFORD_EXPECTED[9] == pytest.approx(0.04576, abs=1e-5)
    assert sum(BENFORD_EXPECTED.values()) == pytest.approx(1.0, abs=1e-9)


def test_benford_detects_a_manipulated_population():
    """A population where every value begins with 9 must not pass."""
    rows = [
        {"entry_id": f"J{i}", "amount": 900000 + i, "posting_date": "2024-06-11"}
        for i in range(200)
    ]
    result = benford_first_digit(make_gl(rows))
    assert result.observed[9] == 200
    assert not result.conforms
    assert "Non-conforming" in result.conclusion


def test_benford_accepts_a_clean_population(gl):
    """The synthetic population is drawn log-uniformly and should conform."""
    result = benford_first_digit(gl.df)
    assert result.total > 800
    assert result.conforms, f"MAD {result.mad}: {result.conclusion}"


def test_benford_reports_an_insufficient_population():
    gl = make_gl([{"entry_id": "J1", "amount": 50, "posting_date": "2024-06-11"}])
    result = benford_first_digit(gl, min_amount=100)
    assert result.total == 0
    assert "too small" in result.conclusion


# --------------------------------------------------------------------------
# The suite as a whole
# --------------------------------------------------------------------------

def test_every_seeded_defect_is_found(engagement):
    analysis = engagement.je_analysis
    by_name = {t.name: t for t in analysis.tests}
    assert by_name["Round-sum entries"].flagged >= 4
    assert by_name["Non-working day postings"].flagged >= 4
    assert by_name["Period-end material entries"].flagged >= 3
    assert by_name["Back-dated entries"].flagged == 2
    assert by_name["Seldom-used account combinations"].flagged >= 2

    # Two users post rarely: the seeded 's.venkatesh', and 'nisha.patel',
    # who exists only to make the two rare-combination entries. Both are
    # correctly selected, so the test asserts the users rather than a count.
    infrequent = by_name["Infrequent posting users"]
    assert {f.posted_by for f in infrequent.flags} == {"s.venkatesh", "nisha.patel"}
    assert sum(1 for f in infrequent.flags if f.posted_by == "s.venkatesh") == 3


def test_flag_rate_stays_proportionate(engagement):
    """A test that flags most of the population is useless to an auditor."""
    for t in engagement.je_analysis.tests:
        if t.population:
            assert t.rate < 0.10, f"{t.name} flagged {t.rate:.1%} of the population"


def test_flags_frame_is_complete(engagement):
    df = engagement.je_analysis.flags_frame()
    assert not df.empty
    assert set(df.columns) == {
        "Entry ID", "Test", "Reason", "Amount (Rs)", "Posting date", "Posted by", "Severity"
    }
    assert df["Reason"].str.len().gt(0).all()


def test_run_all_tests_covers_every_routine(gl):
    analysis = run_all_tests(gl.df, date(2025, 3, 31), 965250.0)
    assert len(analysis.tests) == 6
    assert analysis.benford is not None
    assert analysis.total_entries == gl.entry_count
