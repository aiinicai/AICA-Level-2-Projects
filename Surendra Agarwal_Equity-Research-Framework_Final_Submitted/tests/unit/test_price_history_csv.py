"""Tests for app/data/market_data.py's CSVPriceProvider / load_nse_csv_price_history."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.core.enums import ExchangeCode
from app.core.models import Company
from app.data.market_data import (
    CSVPriceProvider,
    MarketDataError,
    get_market_data_provider,
    load_nse_csv_price_history,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_CSV = PROJECT_ROOT / "data" / "sample" / "SONACOMS_NSE_price_history.csv"


@pytest.fixture(scope="module")
def real_price_df():
    return load_nse_csv_price_history(SAMPLE_CSV)


class TestLoadNseCsvRealData:
    def test_loads_expected_row_count(self, real_price_df):
        assert len(real_price_df) == 1267

    def test_date_range_matches_source(self, real_price_df):
        assert real_price_df.index.min().date() == date(2021, 7, 1)
        assert real_price_df.index.max().date() == date(2026, 8, 10)

    def test_sorted_ascending(self, real_price_df):
        assert list(real_price_df.index) == sorted(real_price_df.index)

    def test_expected_columns_present(self, real_price_df):
        assert set(real_price_df.columns) == {"open", "high", "low", "close", "volume"}

    def test_no_missing_values(self, real_price_df):
        assert not real_price_df.isna().any().any()

    def test_block_deal_row_excluded(self, real_price_df):
        row = real_price_df.loc["2024-11-07"]
        assert row["close"] == 704.65

    def test_indian_comma_formatted_volume_parsed_correctly(self, real_price_df):
        row = real_price_df.loc["2026-08-10"]
        assert row["volume"] == 2407579.0

    def test_known_close_price_matches_source(self, real_price_df):
        row = real_price_df.loc["2021-07-01"]
        assert row["close"] == 344.95

    def test_high_greater_than_or_equal_low_every_row(self, real_price_df):
        assert (real_price_df["high"] >= real_price_df["low"]).all()


class TestLoadNseCsvEdgeCases:
    def test_missing_file_raises(self):
        with pytest.raises(MarketDataError):
            load_nse_csv_price_history(Path("/nonexistent/fake.csv"))

    def test_missing_required_column_raises(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("Symbol,Series,Date\nSONACOMS,EQ,1-Jul-21\n")
        with pytest.raises(MarketDataError, match="missing expected column"):
            load_nse_csv_price_history(bad_csv)

    def test_genuine_duplicate_date_within_eq_series_raises(self, tmp_path):
        content = (
            "Symbol,Series,Date,Prev Close,Open Price,High Price,Low Price,"
            "Last Price,Close Price,Average Price,Total Traded Quantity,"
            "Turnover,No. of Trades,Deliverable Qty,% Dly Qt\n"
            "SONACOMS,EQ,1-Jul-21,340,342,350,333,345,344.95,343,\"17,40,419\",1,1,1,1\n"
            "SONACOMS,EQ,1-Jul-21,340,342,350,333,345,344.95,343,\"17,40,419\",1,1,1,1\n"
        )
        dup_csv = tmp_path / "dup.csv"
        dup_csv.write_text(content)
        with pytest.raises(MarketDataError, match="duplicate date"):
            load_nse_csv_price_history(dup_csv)

    def test_block_deal_row_correctly_excluded_synthetic(self, tmp_path):
        content = (
            "Symbol,Series,Date,Prev Close,Open Price,High Price,Low Price,"
            "Last Price,Close Price,Average Price,Total Traded Quantity,"
            "Turnover,No. of Trades,Deliverable Qty,% Dly Qt\n"
            "SONACOMS,EQ,7-Nov-24,709.35,709.7,720.9,703.3,704.85,704.65,709.98,\"9,55,455\",1,1,1,1\n"
            "SONACOMS,BL,7-Nov-24,291.00,709.0,709.0,709.0,709.00,709.00,709.00,\"4,32,682\",1,1,1,1\n"
        )
        csv_path = tmp_path / "block_deal.csv"
        csv_path.write_text(content)
        df = load_nse_csv_price_history(csv_path)
        assert len(df) == 1
        assert df.iloc[0]["close"] == 704.65

    def test_utf8_bom_handled(self, tmp_path):
        content = (
            "\ufeffSymbol,Series,Date,Prev Close,Open Price,High Price,Low Price,"
            "Last Price,Close Price,Average Price,Total Traded Quantity,"
            "Turnover,No. of Trades,Deliverable Qty,% Dly Qt\n"
            "SONACOMS,EQ,1-Jul-21,340,342,350,333,345,344.95,343,\"17,40,419\",1,1,1,1\n"
        )
        csv_path = tmp_path / "bom.csv"
        csv_path.write_bytes(content.encode("utf-8-sig"))
        df = load_nse_csv_price_history(csv_path)
        assert len(df) == 1
        assert df.iloc[0]["close"] == 344.95


class TestCsvPriceProvider:
    def test_get_price_history_filters_by_date_range(self):
        provider = CSVPriceProvider(SAMPLE_CSV)
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
        result = provider.get_price_history(company, date(2025, 1, 1), date(2025, 12, 31))
        assert result.index.min() >= pd.Timestamp(2025, 1, 1)
        assert result.index.max() <= pd.Timestamp(2025, 12, 31)

    def test_get_price_history_out_of_range_raises(self):
        provider = CSVPriceProvider(SAMPLE_CSV)
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
        with pytest.raises(MarketDataError):
            provider.get_price_history(company, date(2000, 1, 1), date(2000, 12, 31))

    def test_get_current_price_returns_latest_close(self):
        provider = CSVPriceProvider(SAMPLE_CSV)
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
        price = provider.get_current_price(company)
        assert price == 812.5

    def test_lazy_loading_caches_after_first_call(self):
        provider = CSVPriceProvider(SAMPLE_CSV)
        assert provider._df is None
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
        provider.get_current_price(company)
        assert provider._df is not None


class TestProviderFactoryWithCsv:
    def test_csv_provider_resolved_with_path(self):
        provider = get_market_data_provider("csv", csv_path=SAMPLE_CSV)
        assert isinstance(provider, CSVPriceProvider)

    def test_csv_provider_without_path_raises(self):
        with pytest.raises(ValueError, match="csv_path is required"):
            get_market_data_provider("csv")


class TestTechnicalIndicatorsAgainstRealPriceHistory:
    """Closes the gap flagged after Milestone 7: Technical scoring is now
    genuinely computable against real multi-year daily data."""

    def test_sma200_computable_with_real_history(self, real_price_df):
        from app.analysis.technical import compute_sma
        from app.core.enums import DataStatus

        result = compute_sma(real_price_df["close"], window=200)
        assert result.status == DataStatus.OK

    def test_rsi_computable_and_in_valid_range(self, real_price_df):
        from app.analysis.technical import compute_rsi
        from app.core.enums import DataStatus

        result = compute_rsi(real_price_df["close"])
        assert result.status == DataStatus.OK
        assert 0.0 <= result.value <= 100.0

    def test_technical_score_no_longer_unavailable(self, real_price_df):
        from app.analysis.technical import compute_all_smas, compute_rsi
        from app.scoring.investment_score import score_technical
        from app.core.enums import DataStatus

        metrics = compute_all_smas(real_price_df["close"]) + [compute_rsi(real_price_df["close"])]
        result = score_technical(metrics)
        assert result.status == DataStatus.OK
        assert result.score is not None
