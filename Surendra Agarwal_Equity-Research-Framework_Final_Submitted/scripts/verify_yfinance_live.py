"""One-time live verification script for YFinanceProvider.

Run with:  python scripts/verify_yfinance_live.py

This makes REAL network calls to Yahoo Finance - it is deliberately
NOT part of the pytest suite (which never makes live network calls).
Run this once to confirm YFinanceProvider actually works end-to-end on
your machine; the automated test suite has only ever verified its
import correctness and interface conformance, never a live call.

No API key required.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.enums import ExchangeCode
from app.core.models import Company
from app.data.market_data import MarketDataError, YFinanceProvider


def main() -> None:
    print("=" * 70)
    print("LIVE VERIFICATION: YFinanceProvider")
    print("=" * 70)

    company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
    print(f"\nCompany: {company.name}")
    print(f"Resolved Yahoo Finance symbol: {company.market_data_symbol}")

    provider = YFinanceProvider()

    print("\n--- Test 1: get_current_price() ---")
    try:
        price = provider.get_current_price(company)
        if price is None:
            print("Result: None (no error, but no price returned - check symbol coverage)")
        else:
            print(f"SUCCESS: Current price = Rs {price:,.2f}")
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")

    print("\n--- Test 2: get_price_history() - last 30 days ---")
    end = date.today()
    start = end - timedelta(days=30)
    try:
        df = provider.get_price_history(company, start, end)
        print(f"SUCCESS: {len(df)} rows returned")
        print(f"Date range: {df.index.min().date()} to {df.index.max().date()}")
        print(f"Columns: {list(df.columns)}")
        print("\nLast 5 rows:")
        print(df.tail())
    except MarketDataError as exc:
        print(f"FAILED (MarketDataError): {exc}")
    except Exception as exc:
        print(f"FAILED ({type(exc).__name__}): {exc}")

    print("\n--- Test 3: get_price_history() - last 5 years (matches CSV provider's range) ---")
    start_5y = end - timedelta(days=5 * 365)
    try:
        df_5y = provider.get_price_history(company, start_5y, end)
        print(f"SUCCESS: {len(df_5y)} rows returned")
        print(f"Date range: {df_5y.index.min().date()} to {df_5y.index.max().date()}")
    except MarketDataError as exc:
        print(f"FAILED (MarketDataError): {exc}")
    except Exception as exc:
        print(f"FAILED ({type(exc).__name__}): {exc}")

    print("\n" + "=" * 70)
    print("Copy this entire output and share it back for review.")
    print("=" * 70)


if __name__ == "__main__":
    main()
