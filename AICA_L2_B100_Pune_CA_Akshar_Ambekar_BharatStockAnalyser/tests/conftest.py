"""Test setup: make the skill's `bsa` package importable and provide a synthetic company.

All tests run offline. The synthetic company has round-number financials so that results can
be checked by hand.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bharat-stock-analyser" / "scripts"))

from bsa.data import RawData  # noqa: E402

CR = 1e7


def _statement(rows: dict, dates: list[str]) -> pd.DataFrame:
    """Yahoo layout: index = line items, columns = period dates (newest first)."""
    cols = [pd.Timestamp(d) for d in dates]
    return pd.DataFrame({c: {k: v[i] for k, v in rows.items()} for i, c in enumerate(cols)})


@pytest.fixture
def synthetic_raw() -> RawData:
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2021-11-01", "2026-10-30")
    drift = np.linspace(0, 0.9, len(idx))
    close = 100 * np.exp(drift + rng.normal(0, 0.012, len(idx)).cumsum() * 0.3)
    ohlc = pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                         "Adj Close": close, "Volume": 1_000_000.0}, index=idx)
    bench = pd.Series(20000 * np.exp(np.linspace(0, 0.4, len(idx))), index=idx)

    years = ["2026-03-31", "2025-03-31", "2024-03-31", "2023-03-31"]
    # Revenue 1,000 -> 1,331 crore (10% CAGR); PAT 100 -> 133.1 crore; 10 crore shares.
    income = _statement({
        "Total Revenue": [1331 * CR, 1210 * CR, 1100 * CR, 1000 * CR],
        "EBITDA": [266.2 * CR, 242 * CR, 220 * CR, 200 * CR],
        "EBIT": [226.2 * CR, 205 * CR, 186 * CR, 170 * CR],
        "Interest Expense": [20 * CR, 20 * CR, 20 * CR, 20 * CR],
        "Pretax Income": [177.5 * CR, 161.3 * CR, 146.7 * CR, 133.3 * CR],
        "Tax Provision": [44.4 * CR, 40.3 * CR, 36.7 * CR, 33.3 * CR],
        "Net Income Common Stockholders": [133.1 * CR, 121 * CR, 110 * CR, 100 * CR],
    }, years)
    balance = _statement({
        "Stockholders Equity": [800 * CR, 700 * CR, 600 * CR, 500 * CR],
        "Total Debt": [200 * CR, 200 * CR, 200 * CR, 200 * CR],
        "Cash And Cash Equivalents": [100 * CR, 80 * CR, 60 * CR, 40 * CR],
        "Total Assets": [1400 * CR, 1300 * CR, 1200 * CR, 1100 * CR],
        "Current Liabilities": [300 * CR, 300 * CR, 300 * CR, 300 * CR],
    }, years)
    cashflow = _statement({
        "Operating Cash Flow": [150 * CR, 130 * CR, 120 * CR, 105 * CR],
        "Capital Expenditure": [-50 * CR, -50 * CR, -50 * CR, -50 * CR],
        "Cash Dividends Paid": [-30 * CR, -25 * CR, -20 * CR, -20 * CR],
    }, years)
    qdates = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"]
    q_income = _statement({
        "Total Revenue": [360 * CR, 340 * CR, 335 * CR, 330 * CR, 320 * CR],
        "EBITDA": [72 * CR, 68 * CR, 67 * CR, 66 * CR, 64 * CR],
        "Net Income Common Stockholders": [36 * CR, 34 * CR, 33.5 * CR, 33 * CR, 32 * CR],
    }, qdates)
    info = {"longName": "Demo Industries Limited", "sector": "Industrials", "industry": "Demo",
            "currentPrice": float(close[-1]), "previousClose": float(close[-2]),
            "sharesOutstanding": 10 * CR, "marketCap": float(close[-1]) * 10 * CR,
            "trailingEps": 13.31, "forwardEps": 14.6, "bookValue": 80.0,
            "targetMeanPrice": float(close[-1]) * 1.2, "targetLowPrice": float(close[-1]),
            "targetHighPrice": float(close[-1]) * 1.4, "numberOfAnalystOpinions": 12,
            "recommendationKey": "buy", "heldPercentInsiders": 0.55, "heldPercentInstitutions": 0.30,
            "financialCurrency": "INR"}
    return RawData(symbol="DEMO.NS", exchange="NSE", info=info, ohlc=ohlc, bench=bench, sensex_last=75000.0,
                   income=income, balance=balance, cashflow=cashflow, q_income=q_income, news=[],
                   fetched_at="01-Nov-2026 10:00 IST", warnings=[])
