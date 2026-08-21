from decimal import Decimal
from repositories import asset_repository, category_repository, settings_repository
from utils.validation import ValidationError, require, validate_positive, validate_useful_life, validate_date
from utils.date_utils import to_iso

def _prepare_record(data):
    orig_cost = validate_positive(data.get("original_cost"), "Original cost")
    accum_dep = validate_positive(data.get("opening_accum_dep", 0) or 0, "Opening Accumulated Depreciation")
    res_val = validate_positive(data.get("residual_value", 0) or 0, "Residual value")
    p_date = validate_date(data.get("purchase_date"), "Purchase date")
    require(p_date is not None, "Purchase date is required.")
    
    u_date = validate_date(data.get("date_put_to_use"), "Date put to use")
    if not u_date: u_date = p_date
    if u_date < p_date: raise ValidationError("Date put to use cannot be earlier than purchase date.")

    record = dict(data)
    record["purchase_date"] = to_iso(p_date)
    record["date_put_to_use"] = to_iso(u_date)
    record["original_cost"] = str(orig_cost)
    record["opening_accum_dep"] = str(accum_dep)
    record["residual_value"] = str(res_val)
    record["opening_wdv"] = str(orig_cost - accum_dep)
    return record

def create_asset(conn, data):
    cat_id = data.get("category_id")
    require(cat_id is not None, "Category is required.")
    category = category_repository.get_category(conn, cat_id)
    require(category and category["active"] == 1, "Inactive category.")
    require(bool(data.get("asset_name")), "Name is required.")
    
    record = _prepare_record(data)
    id_mode = settings_repository.get_setting(conn, "asset_id_mode", "CATEGORY")
    asset_id = asset_repository.generate_next_asset_id(conn, cat_id, category["category_code"], id_mode)
    asset_repository.insert_asset(conn, asset_id, record)
    return asset_id

def update_asset(conn, asset_id, data):
    record = _prepare_record(data)
    record.pop("category_id", None) 
    asset_repository.update_asset(conn, asset_id, record)

# --- MISSING FUNCTION ADDED BELOW ---
def delete_asset(conn, asset_id):
    """
    Checks if the asset can be deleted and then removes it.
    If it has posted depreciation history, deletion is blocked for data integrity.
    """
    # 1. Check if the asset has any posted depreciation records
    query = "SELECT COUNT(*) as c FROM depreciation_records WHERE asset_id = ?"
    row = conn.execute(query, (asset_id,)).fetchone()
    
    if row and row["c"] > 0:
        raise ValidationError("Cannot delete asset. It has posted depreciation history.")
    
    # 2. Proceed to delete
    asset_repository.delete_asset(conn, asset_id)