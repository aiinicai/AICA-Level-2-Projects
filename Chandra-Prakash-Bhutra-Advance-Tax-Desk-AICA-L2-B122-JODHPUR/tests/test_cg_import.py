"""Capital gains import: column guessing, holding period, heads and loss set-off."""
import pandas as pd
import pytest

from advtax import cg_import as cg


def frame(rows):
    return pd.DataFrame(rows, columns=["Scrip Name", "Asset Type", "Buy Date", "Sell Date", "Buy Value", "Sell Value", "Realised P&L"])


MAP = {"asset": "Scrip Name", "type": "Asset Type", "buy_date": "Buy Date", "sell_date": "Sell Date",
       "buy_value": "Buy Value", "sell_value": "Sell Value", "gain": None, "expenses": None, "term": None}


def test_guess_columns_on_a_broker_style_header():
    g = cg.guess_columns(frame([]))
    assert g["asset"] == "Scrip Name" and g["type"] == "Asset Type"
    assert g["buy_date"] == "Buy Date" and g["sell_date"] == "Sell Date"
    assert g["buy_value"] == "Buy Value" and g["sell_value"] == "Sell Value" and g["gain"] == "Realised P&L"


def test_holding_period_boundaries():
    b = pd.Timestamp("2025-04-10")
    assert cg.term_for(cg.EQUITY, b, pd.Timestamp("2026-04-10")) == ("Short", False)   # exactly 12 months
    assert cg.term_for(cg.EQUITY, b, pd.Timestamp("2026-04-11")) == ("Long", False)    # more than 12 months
    assert cg.term_for(cg.OTHER, b, pd.Timestamp("2027-04-10")) == ("Short", False)    # exactly 24 months
    assert cg.term_for(cg.OTHER, b, pd.Timestamp("2027-04-11")) == ("Long", False)
    assert cg.term_for(cg.DEBT, b, pd.Timestamp("2030-01-01")) == ("Short", False)     # always short-term
    assert cg.term_for(cg.EQUITY, pd.NaT, pd.NaT, "LTCG") == ("Long", False)
    assert cg.term_for(cg.EQUITY, pd.NaT, pd.NaT, "") == ("Short", True)               # flagged for checking


def test_classify_asset():
    assert cg.classify_asset("Equity", "") == cg.EQUITY
    assert cg.classify_asset("Debt Mutual Fund", "") == cg.DEBT
    assert cg.classify_asset("Immovable property", "") == cg.OTHER
    assert cg.classify_asset("Equity - Intraday", "") == cg.IGNORE
    assert cg.classify_asset("F&O", "") == cg.IGNORE
    assert cg.classify_asset("", "ABC Liquid Fund Direct") == cg.DEBT
    assert cg.classify_asset("", "Some Scrip", cg.OTHER) == cg.OTHER


def test_normalise_and_summarise_hand_worked():
    df = frame([
        ["Alpha Ltd", "Equity", "10-04-2025", "15-06-2026", 100000, 160000, None],        # long equity  +60,000
        ["Beta Ltd", "Equity", "01-05-2026", "20-08-2026", 200000, 170000, None],         # short equity -30,000
        ["Gamma Equity Fund", "Equity MF", "05-01-2026", "10-09-2026", 50000, 62000, None],  # short equity +12,000
        ["Plot at Pali", "Land", "01-01-2020", "01-07-2026", 1000000, 1900000, None],     # long other  +9,00,000
        ["Delta Liquid Fund", "Debt MF", "01-01-2022", "01-06-2026", 300000, 345000, None],  # debt -> slab +45,000
        ["Nifty Fut", "F&O", "01-06-2026", "02-06-2026", 0, 0, 5000],                     # ignored
        ["Total", "", None, None, 1650000, 2637000, None],                                # total row dropped
    ])
    rows = cg.normalise(df, MAP)
    assert len(rows) == 6
    s = cg.summarise(rows)
    assert s["buckets"] == {"stcg_equity": -18000, "ltcg_equity": 60000, "ltcg_other": 900000, "stcg_other": 45000}
    assert s["ignored"] == 0 and s["to_check"] == 0
    after = cg.set_off(s["buckets"])
    # short-term equity loss 18,000 goes first against the slab-rate gain of 45,000
    assert after["buckets"] == {"stcg_equity": 0, "ltcg_equity": 60000, "ltcg_other": 900000, "stcg_other": 27000}
    assert after["short_term_loss_carried"] == 0 and after["long_term_loss_carried"] == 0


def test_gain_column_wins_and_expenses_reduce_computed_gain():
    df = pd.DataFrame({"Name": ["A", "B"], "Buy Value": [100, 100], "Sell Value": [150, 150], "Charges": [10, 10], "P&L": [45, None]})
    rows = cg.normalise(df, {"asset": "Name", "buy_value": "Buy Value", "sell_value": "Sell Value", "expenses": "Charges", "gain": "P&L"})
    assert list(rows["gain"]) == [45, 40]


def test_set_off_rules():
    # long-term loss only against long-term gain; the rest is carried forward, never against short-term gain
    a = cg.set_off({"stcg_equity": 100000, "ltcg_equity": -80000, "ltcg_other": 30000, "stcg_other": 0})
    assert a["buckets"] == {"stcg_equity": 100000, "ltcg_equity": 0, "ltcg_other": 0, "stcg_other": 0}
    assert a["long_term_loss_carried"] == 50000 and a["short_term_loss_carried"] == 0
    # short-term loss: slab-rate gain first, then short-term equity, then long-term
    b = cg.set_off({"stcg_equity": 20000, "ltcg_equity": 50000, "ltcg_other": 0, "stcg_other": -90000})
    assert b["buckets"] == {"stcg_equity": 0, "ltcg_equity": 0, "ltcg_other": 0, "stcg_other": 0}
    assert b["short_term_loss_carried"] == 20000
    # nothing negative: unchanged
    c = cg.set_off({"stcg_equity": 1, "ltcg_equity": 2, "ltcg_other": 3, "stcg_other": 4})
    assert c["buckets"] == {"stcg_equity": 1, "ltcg_equity": 2, "ltcg_other": 3, "stcg_other": 4}


def test_normalise_needs_enough_columns():
    df = pd.DataFrame({"Name": ["A"], "Buy Value": [1]})
    with pytest.raises(ValueError):
        cg.normalise(df, {"asset": "Name", "buy_value": "Buy Value"})
    with pytest.raises(ValueError):
        cg.normalise(df, {"buy_value": "Buy Value"})
