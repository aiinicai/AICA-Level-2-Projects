import pytest
from decimal import Decimal
from calculations.disposal import calculate_disposal_profit_loss
from repositories import category_repository, settings_repository
from services import asset_service, disposal_service
from utils.validation import ValidationError


def _make_block(conn, code="ITB15", rate=15):
    settings_repository.create_tax_block(conn, f"Block {code}", code, "", rate)
    return conn.execute("SELECT block_id FROM tax_blocks WHERE block_code=?", (code,)).fetchone()["block_id"]


def test_profit_on_sale():
    result = calculate_disposal_profit_loss(100000, 40000, 75000, 0)
    assert result["net_book_value"] == Decimal("60000.00")
    assert result["profit_loss_type"] == "PROFIT ON SALE"
    assert result["profit_loss"] == Decimal("15000.00")


def test_loss_on_sale():
    result = calculate_disposal_profit_loss(100000, 40000, 50000, 0)
    assert result["net_book_value"] == Decimal("60000.00")
    assert result["profit_loss_type"] == "LOSS ON SALE"
    assert result["profit_loss"] == Decimal("10000.00")


def test_duplicate_disposal_rejected(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    block_id = _make_block(conn)
    asset_id = asset_service.create_asset(conn, {
        "asset_name": "Laptop", "category_id": cat_id, "purchase_date": "2025-04-01",
        "original_cost": 50000, "residual_value": 5000, "useful_life_years": 3,
        "companies_act_method": "SLM", "income_tax_block_id": block_id, "opening_accum_dep": 0,
    })
    disposal_service.create_disposal(conn, asset_id, "2026-04-01", 30000, 0)
    with pytest.raises(ValidationError):
        disposal_service.create_disposal(conn, asset_id, "2026-05-01", 20000, 0)


def test_invalid_disposal_date_before_purchase(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    block_id = _make_block(conn)
    asset_id = asset_service.create_asset(conn, {
        "asset_name": "Laptop", "category_id": cat_id, "purchase_date": "2026-04-01",
        "original_cost": 50000, "residual_value": 5000, "useful_life_years": 3,
        "companies_act_method": "SLM", "income_tax_block_id": block_id, "opening_accum_dep": 0,
    })
    with pytest.raises(ValidationError):
        disposal_service.create_disposal(conn, asset_id, "2025-01-01", 30000, 0)


def test_disposal_uses_actual_dates_for_companies_act(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    block_id = _make_block(conn)
    asset_id = asset_service.create_asset(conn, {
        "asset_name": "Laptop", "category_id": cat_id, "purchase_date": "2026-04-01",
        "date_put_to_use": "2026-04-01", "original_cost": 100000, "residual_value": 10000,
        "useful_life_years": 5, "companies_act_method": "SLM",
        "income_tax_block_id": block_id, "opening_accum_dep": 0,
    })
    data = disposal_service.create_disposal(conn, asset_id, "2026-09-30", 90000, 0)
    assert Decimal(data["accumulated_depreciation"]) < Decimal("18000.00")
    assert Decimal(data["accumulated_depreciation"]) > Decimal("6000.00")