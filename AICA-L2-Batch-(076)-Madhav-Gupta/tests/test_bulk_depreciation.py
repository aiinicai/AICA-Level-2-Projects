from decimal import Decimal
from repositories import category_repository, depreciation_repository as dep_repo, settings_repository
from services import asset_service, depreciation_service, disposal_service


def _setup_block(conn, name="Computers", code="ITB40", rate=40):
    settings_repository.create_tax_block(conn, name, code, "", rate)
    row = conn.execute("SELECT block_id FROM tax_blocks WHERE block_code=?", (code,)).fetchone()
    return row["block_id"]


def _create_sample_asset(conn, category_id, block_id, name, cost=100000, residual=10000, life=5):
    data = {
        "asset_name": name, "category_id": category_id, "purchase_date": "2026-04-01",
        "date_put_to_use": "2026-04-01", "original_cost": cost, "residual_value": residual,
        "useful_life_years": life, "companies_act_method": "SLM",
        "income_tax_block_id": block_id, "opening_accum_dep": 0,
    }
    return asset_service.create_asset(conn, data)


def test_bulk_depreciation_run(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    block_id = _setup_block(conn)
    for i in range(1, 6):
        _create_sample_asset(conn, cat_id, block_id, f"Computer {i}")

    eligible = depreciation_service.load_eligible_assets(conn, "FY 2026-27")
    assert len(eligible) == 5

    valid, exceptions = depreciation_service.validate_depreciation_run(conn, eligible, "FY 2026-27")
    assert len(valid) == 5
    assert len(exceptions) == 0

    output = depreciation_service.calculate_depreciation_run(
        conn, valid, "2026-04-01", "2027-03-31", "DAYS", "FY 2026-27")
    asset_results = output["asset_results"]
    block_results = output["block_results"]
    assert len(asset_results) == 5
    assert all(r["status"] == "OK" for r in asset_results)
    assert len(block_results) == 1

    run_id = depreciation_service.create_depreciation_run(
        conn, "FY 2026-27", "2026-04-01", "2027-03-31", "DAYS")
    totals = depreciation_service.post_depreciation_run(
        conn, run_id, output, "FY 2026-27", "2026-04-01", "2027-03-31")
    assert totals["total_assets"] == 5

    manual_total = sum(Decimal(str(r["companies_act_depreciation"])) for r in asset_results)
    assert Decimal(totals["total_ca_dep"]) == manual_total


def test_duplicate_bulk_run_prevention(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    block_id = _setup_block(conn)
    _create_sample_asset(conn, cat_id, block_id, "Computer A")

    eligible = depreciation_service.load_eligible_assets(conn, "FY 2026-27")
    output = depreciation_service.calculate_depreciation_run(
        conn, eligible, "2026-04-01", "2027-03-31", "DAYS", "FY 2026-27")
    run_id = depreciation_service.create_depreciation_run(
        conn, "FY 2026-27", "2026-04-01", "2027-03-31", "DAYS")
    depreciation_service.post_depreciation_run(
        conn, run_id, output, "FY 2026-27", "2026-04-01", "2027-03-31")

    eligible_again = depreciation_service.load_eligible_assets(conn, "FY 2026-27")
    valid, exceptions = depreciation_service.validate_depreciation_run(conn, eligible_again, "FY 2026-27")
    assert len(valid) == 0
    assert len(exceptions) == 1


def test_reversal_keeps_history(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    block_id = _setup_block(conn)
    _create_sample_asset(conn, cat_id, block_id, "Computer A")

    eligible = depreciation_service.load_eligible_assets(conn, "FY 2026-27")
    output = depreciation_service.calculate_depreciation_run(
        conn, eligible, "2026-04-01", "2027-03-31", "DAYS", "FY 2026-27")
    run_id = depreciation_service.create_depreciation_run(
        conn, "FY 2026-27", "2026-04-01", "2027-03-31", "DAYS")
    depreciation_service.post_depreciation_run(
        conn, run_id, output, "FY 2026-27", "2026-04-01", "2027-03-31")

    reversal_id = depreciation_service.reverse_depreciation_run(conn, run_id)

    original = dep_repo.get_run(conn, run_id)
    reversal = dep_repo.get_run(conn, reversal_id)
    assert original["status"] == "REVERSED"
    assert reversal["status"] == "POSTED"


def test_no_depreciation_on_sold_asset_within_block(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    block_id = _setup_block(conn)
    keep_id = _create_sample_asset(conn, cat_id, block_id, "Computer Kept", cost=100000)
    sell_id = _create_sample_asset(conn, cat_id, block_id, "Computer Sold", cost=50000)

    disposal_service.create_disposal(conn, sell_id, "2026-06-01", 40000, 0)

    eligible = depreciation_service.load_eligible_assets(conn, "FY 2026-27")
    asset_ids = [a["asset_id"] for a in eligible]
    assert sell_id not in asset_ids
    assert keep_id in asset_ids

    output = depreciation_service.calculate_depreciation_run(
        conn, eligible, "2026-04-01", "2027-03-31", "DAYS", "FY 2026-27")
    block_results = output["block_results"]
    assert len(block_results) == 1
    assert block_results[0]["disposals"] == Decimal("40000.00")