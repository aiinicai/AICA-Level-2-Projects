"""Ingestion and validation."""

from __future__ import annotations

import io

import pandas as pd
import pytest

from auditlens.ingest import IngestError, load_trial_balance


def test_trial_balance_tallies(tb):
    assert tb.balances
    assert tb.difference == 0.0
    assert tb.total_debit == tb.total_credit


def test_every_ledger_survives_ingestion(tb):
    assert len(tb.df) == 61
    assert tb.df["account_name"].str.len().gt(0).all()


def test_headers_are_normalised(tmp_path):
    """A client template using 'Ledger Code' / 'Particulars' / 'Dr' / 'Cr'."""
    path = tmp_path / "tb.csv"
    path.write_text(
        "Ledger Code,Particulars,Dr,Cr\n"
        "1001,Equity share capital,0,1000000\n"
        "2281,Cash in hand,1000000,0\n"
    )
    tb = load_trial_balance(path, "2024-25")
    assert list(tb.df.columns[:4]) == ["account_code", "account_name", "debit", "credit"]
    assert tb.balances


def test_indian_number_formats_are_parsed(tmp_path):
    """Commas, rupee signs, brackets and blanks all appear in real exports."""
    path = tmp_path / "tb.csv"
    path.write_text(
        "account_code,account_name,debit,credit\n"
        '1001,Equity share capital,,"12,50,000"\n'
        '2281,Cash in hand,"₹ 12,50,000",\n'
    )
    tb = load_trial_balance(path, "2024-25")
    assert tb.total_debit == 1250000.0
    assert tb.total_credit == 1250000.0
    assert tb.balances


def test_unbalanced_trial_balance_is_reported_not_corrected(tmp_path):
    path = tmp_path / "tb.csv"
    path.write_text(
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,1000000\n"
        "2281,Cash in hand,940000,0\n"
    )
    tb = load_trial_balance(path, "2024-25")
    assert not tb.balances
    assert tb.difference == -60000.0


def test_missing_column_raises(tmp_path):
    path = tmp_path / "tb.csv"
    path.write_text("account_code,account_name,debit\n1001,Share capital,100\n")
    with pytest.raises(IngestError, match="credit"):
        load_trial_balance(path, "2024-25")


def test_duplicate_codes_are_aggregated(tmp_path):
    path = tmp_path / "tb.csv"
    path.write_text(
        "account_code,account_name,debit,credit\n"
        "4410,Miscellaneous expenses,50000,0\n"
        "4410,Miscellaneous expenses,30000,0\n"
        "1001,Equity share capital,0,80000\n"
    )
    tb = load_trial_balance(path, "2024-25")
    assert tb.net_balance("4410") == 80000.0
    assert any("share an account code" in w for w in tb.warnings)


def test_general_ledger_entries_balance(gl):
    assert gl.entry_count > 900
    assert len(gl.unbalanced_entries()) == 0


def test_general_ledger_dates_are_parsed(gl):
    assert gl.df["posting_date"].notna().all()
    assert gl.df["posting_date"].min().year == 2024
    assert gl.df["posting_date"].max().year == 2025
