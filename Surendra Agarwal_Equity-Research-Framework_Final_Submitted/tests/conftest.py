"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.enums import Currency, DataSourceType, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.data.financial_data import build_canonical_statements
from app.data.loaders import load_screener_excel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_XLSX = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_Precis_screener_export.xlsx"


@pytest.fixture(scope="session")
def sona_blw_raw_records():
    """Real, unmodified Sona BLW data parsed from the sample Screener export."""
    return load_screener_excel(SAMPLE_XLSX, company_name="Sona BLW Precision Forgings Ltd")


@pytest.fixture(scope="session")
def sona_blw_statements(sona_blw_raw_records):
    """Real Sona BLW canonical annual FinancialStatement objects, FY2017-FY2026."""
    return build_canonical_statements(sona_blw_raw_records)


def _make_source(period: str, unit: UnitOfMeasure = UnitOfMeasure.INR_CRORE) -> SourceMetadata:
    return SourceMetadata(
        company="Test Co",
        source="synthetic_test_fixture",
        source_type=DataSourceType.MANUAL_ENTRY,
        reporting_period=period,
        currency=Currency.INR,
        unit=unit,
    )


@pytest.fixture
def clean_statement_pair():
    """Two consecutive, internally-consistent synthetic statements."""
    s1 = FinancialStatement(
        company="Test Co", period="FY2024", period_end_date=date(2024, 3, 31),
        sales=1000.0, net_profit=100.0, total_assets=2000.0, total_liabilities=2000.0,
        profit_before_tax=130.0, tax=30.0, face_value=10.0, num_equity_shares=1_000_000.0,
        source=_make_source("FY2024"),
    )
    s2 = FinancialStatement(
        company="Test Co", period="FY2025", period_end_date=date(2025, 3, 31),
        sales=1200.0, net_profit=130.0, total_assets=2300.0, total_liabilities=2300.0,
        profit_before_tax=165.0, tax=35.0, face_value=10.0, num_equity_shares=1_000_000.0,
        source=_make_source("FY2025"),
    )
    return [s1, s2]
