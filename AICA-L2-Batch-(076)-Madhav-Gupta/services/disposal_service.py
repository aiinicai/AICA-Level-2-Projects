from datetime import timedelta
from repositories import disposal_repository, asset_repository, depreciation_repository as dep_repo, settings_repository
from calculations.companies_act import calculate_slm_depreciation, calculate_wdv_depreciation
from calculations.disposal import calculate_disposal_profit_loss, calculate_block_disposal_impact
from utils.validation import require
from utils.date_utils import parse_date, to_iso, get_financial_year, financial_year_bounds
from utils.formatting import to_decimal


def create_disposal(conn, asset_id, disposal_date, sale_consideration, selling_expenses=0,
                     buyer_name="", invoice_number="", remarks=""):
    asset = asset_repository.get_asset(conn, asset_id)
    require(asset is not None, "Asset not found.")
    require(asset["status"] != "DISPOSED",
            f"Asset already disposed on {asset['disposal_date']}. "
            "A second disposal transaction is not permitted.")
    require(not disposal_repository.has_existing_disposal(conn, asset_id),
            "This asset already has a disposal record.")

    disposal_date_parsed = parse_date(disposal_date)
    require(disposal_date_parsed is not None, "Disposal date is required.")
    purchase_date_parsed = parse_date(asset["purchase_date"])
    require(disposal_date_parsed >= purchase_date_parsed,
            "Disposal date cannot be earlier than the purchase date.")
    require(to_decimal(sale_consideration) >= 0, "Sale consideration cannot be negative.")
    require(to_decimal(selling_expenses) >= 0, "Selling expenses cannot be negative.")

    # ---- Companies Act: bring depreciation up to the ACTUAL disposal date ----
    history = dep_repo.get_history_for_asset(conn, asset_id)
    posted = [h for h in history if h["run_status"] == "POSTED"]
    financial_year = get_financial_year(disposal_date_parsed)
    fy_start, fy_end = financial_year_bounds(financial_year)
    year_days = (fy_end - fy_start).days + 1

    if posted:
        latest = posted[-1]
        stub_opening_ca = to_decimal(latest["closing_carrying_amount"])
        stub_start = parse_date(latest["period_end"]) + timedelta(days=1)
    else:
        stub_opening_ca = to_decimal(asset["opening_wdv"])
        stub_start = parse_date(asset["date_put_to_use"] or asset["purchase_date"])

    if stub_start > disposal_date_parsed:
        stub_depreciation = to_decimal(0)
    else:
        method = (asset["companies_act_method"] or "SLM").upper()
        if method == "SLM":
            stub_result = calculate_slm_depreciation(
                cost=asset["original_cost"], residual_value=asset["residual_value"],
                useful_life_years=asset["useful_life_years"], period_start=stub_start,
                period_end=disposal_date_parsed, basis="DAYS", year_days=year_days,
                opening_accum_dep=to_decimal(asset["original_cost"]) - stub_opening_ca,
            )
        else:
            stub_result = calculate_wdv_depreciation(
                opening_wdv=stub_opening_ca, rate=asset["companies_act_rate"],
                residual_value=asset["residual_value"], period_start=stub_start,
                period_end=disposal_date_parsed, basis="DAYS", year_days=year_days,
            )
        stub_depreciation = stub_result["period_depreciation"]

    carrying_amount_before_disposal = stub_opening_ca - stub_depreciation
    accumulated_depreciation = to_decimal(asset["original_cost"]) - carrying_amount_before_disposal

    ca_result = calculate_disposal_profit_loss(asset["original_cost"], accumulated_depreciation,
                                                sale_consideration, selling_expenses)

    # ---- Income-tax: Block of Assets concept - NO individual depreciation is
    # computed on this disposed asset. The sale consideration only reduces the WDV
    # of its Income-tax Block; the tax effect is finalised in the next Depreciation Run. ----
    block_impact = calculate_block_disposal_impact(sale_consideration)
    latest_block_wdv = None
    if asset["income_tax_block_id"]:
        latest_block_record = dep_repo.get_latest_posted_block_record(conn, asset["income_tax_block_id"])
        if latest_block_record:
            latest_block_wdv = latest_block_record["closing_wdv"]

    data = {
        "asset_id": asset_id, "disposal_date": to_iso(disposal_date_parsed),
        "sale_consideration": str(to_decimal(sale_consideration)),
        "selling_expenses": str(to_decimal(selling_expenses)),
        "buyer_name": buyer_name, "invoice_number": invoice_number, "remarks": remarks,
        "original_cost": str(to_decimal(asset["original_cost"])),
        "accumulated_depreciation": str(accumulated_depreciation),
        "net_book_value": str(ca_result["net_book_value"]),
        "net_sale_proceeds": str(ca_result["net_sale_proceeds"]),
        "profit_loss": str(ca_result["profit_loss"]), "profit_loss_type": ca_result["profit_loss_type"],
        "tax_opening_wdv": str(latest_block_wdv) if latest_block_wdv is not None else None,
        "tax_closing_wdv": None,
        "tax_impact": str(block_impact["block_wdv_reduction"]),
        "tax_impact_type": "BLOCK WDV REDUCTION - finalised at next Depreciation Run",
        "carrying_amount_before": str(carrying_amount_before_disposal),
        "tax_base_before": str(latest_block_wdv) if latest_block_wdv is not None else None,
        "temporary_difference_before": None,
        "deferred_tax_before": None,
    }

    try:
        disposal_repository.insert_disposal(conn, data)
        asset_repository.update_asset(conn, asset_id, {
            "status": "DISPOSED", "disposal_date": to_iso(disposal_date_parsed),
            "disposal_value": str(to_decimal(sale_consideration)), "buyer_name": buyer_name,
        })
        settings_repository.log_audit(conn, "Disposal Created", "disposal_records", asset_id, "", remarks)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return data

def delete_disposal(conn, asset_id):
    """Reverts a disposal: deletes record and sets asset back to ACTIVE."""
    asset = asset_repository.get_asset(conn, asset_id)
    require(asset is not None, "Asset not found.")
    require(asset["status"] == "DISPOSED", "Asset is not currently marked as disposed.")

    try:
        # 1. Remove the disposal history
        disposal_repository.delete_disposal_record(conn, asset_id)
        
        # 2. Revert Asset Status and clear disposal fields
        asset_repository.update_asset(conn, asset_id, {
            "status": "ACTIVE",
            "disposal_date": None,
            "disposal_value": None,
            "buyer_name": None
        })
        settings_repository.log_audit(conn, "Disposal Deleted (Reverted)", "disposal_records", asset_id, "DISPOSED", "ACTIVE")
        conn.commit()
    except Exception:
        conn.rollback()
        raise