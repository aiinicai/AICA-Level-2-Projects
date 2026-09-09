from decimal import Decimal
from calculations.companies_act import calculate_slm_depreciation, calculate_wdv_depreciation
from calculations.bulk_depreciation import calculate_asset_companies_act


def test_slm_annual_depreciation():
    result = calculate_slm_depreciation(
        cost=100000, residual_value=10000, useful_life_years=5,
        period_start="2026-04-01", period_end="2027-03-31", basis="DAYS", year_days=365,
    )
    assert result["annual_depreciation"] == Decimal("18000.00")
    assert result["period_depreciation"] == Decimal("18000.00")


def test_wdv_depreciation():
    result = calculate_wdv_depreciation(
        opening_wdv=100000, rate=15, residual_value=0,
        period_start="2026-04-01", period_end="2027-03-31", basis="DAYS", year_days=365,
    )
    assert result["period_depreciation"] == Decimal("15000.00")
    assert result["closing_wdv"] == Decimal("85000.00")


def test_slm_actual_dates_mid_year_addition():
    """Companies Act depreciation must use the ACTUAL date put to use, not assume
    the asset was in use for the whole period."""
    asset = {
        "asset_id": "COM-000001", "asset_name": "Laptop", "companies_act_method": "SLM",
        "useful_life_years": 5, "original_cost": 100000, "residual_value": 10000,
        "opening_carrying_amount": 100000, "opening_accum_dep": 0,
        "date_put_to_use": "2026-10-01",
    }
    result = calculate_asset_companies_act(asset, "2026-04-01", "2027-03-31", "DAYS", 365)
    assert result["status"] == "OK"
    assert result["companies_act_depreciation"] < Decimal("18000.00")
    assert result["companies_act_depreciation"] > Decimal("8000.00")


def test_slm_full_year_when_put_to_use_before_period():
    asset = {
        "asset_id": "COM-000002", "asset_name": "Desktop", "companies_act_method": "SLM",
        "useful_life_years": 5, "original_cost": 100000, "residual_value": 10000,
        "opening_carrying_amount": 100000, "opening_accum_dep": 0,
        "date_put_to_use": "2025-04-01",
    }
    result = calculate_asset_companies_act(asset, "2026-04-01", "2027-03-31", "DAYS", 365)
    assert result["companies_act_depreciation"] == Decimal("18000.00")


def test_asset_not_yet_put_to_use_gets_zero_depreciation():
    asset = {
        "asset_id": "COM-000003", "asset_name": "Server", "companies_act_method": "SLM",
        "useful_life_years": 5, "original_cost": 100000, "residual_value": 10000,
        "opening_carrying_amount": 100000, "opening_accum_dep": 0,
        "date_put_to_use": "2027-04-15",
    }
    result = calculate_asset_companies_act(asset, "2026-04-01", "2027-03-31", "DAYS", 365)
    assert result["companies_act_depreciation"] == Decimal("0")