from repositories import category_repository, settings_repository
from services import asset_service

SAMPLE_CATEGORIES = [
    ("Computers", "COM", "SLM", 5, 0),
    ("Furniture & Fixtures", "FNF", "SLM", 10, 0),
    ("Plant & Machinery", "PNM", "WDV", 15, 5),
    ("Building", "BLD", "SLM", 30, 0),
    ("Vehicles", "VEH", "WDV", 8, 5),
]

SAMPLE_TAX_BLOCKS = [
    ("Computers & Software", "ITB40", 40),
    ("Furniture & Fittings", "ITB10", 10),
    ("Plant & Machinery - General", "ITB15", 15),
    ("Buildings - Factory", "ITB10B", 10),
]

SAMPLE_ASSETS = [
    {"name": "Desktop Computer - Set 1", "category_code": "COM", "block_code": "ITB40",
     "cost": 100000, "residual": 10000, "life": 5, "method": "SLM", "purchase_date": "2026-04-01"},
    {"name": "Office Chairs (Lot)", "category_code": "FNF", "block_code": "ITB10",
     "cost": 50000, "residual": 5000, "life": 10, "method": "SLM", "purchase_date": "2026-04-15"},
    {"name": "CNC Machine", "category_code": "PNM", "block_code": "ITB15",
     "cost": 500000, "residual": 25000, "life": 15, "method": "WDV", "rate": 15,
     "purchase_date": "2026-05-01"},
    {"name": "Factory Building", "category_code": "BLD", "block_code": "ITB10B",
     "cost": 2000000, "residual": 0, "life": 30, "method": "SLM", "purchase_date": "2020-04-01"},
    {"name": "Delivery Van", "category_code": "VEH", "block_code": "ITB15",
     "cost": 800000, "residual": 40000, "life": 8, "method": "WDV", "rate": 15,
     "purchase_date": "2026-06-01"},
]


def load_sample_data(conn):
    existing_codes = category_repository.existing_codes(conn)
    category_ids = {}
    for name, code, method, life, residual in SAMPLE_CATEGORIES:
        if code in existing_codes:
            row = category_repository.get_category_by_code(conn, code)
            category_ids[code] = row["category_id"]
            continue
        cat_id = category_repository.create_category(conn, name, code, "", method, life, residual, None, None)
        category_ids[code] = cat_id

    existing_block_codes = {b["block_code"] for b in settings_repository.list_tax_blocks(conn)}
    block_ids = {}
    for name, code, rate in SAMPLE_TAX_BLOCKS:
        if code not in existing_block_codes:
            settings_repository.create_tax_block(conn, name, code, "", rate)
        row = conn.execute("SELECT block_id FROM tax_blocks WHERE block_code=?", (code,)).fetchone()
        block_ids[code] = row["block_id"]

    created_assets = []
    for item in SAMPLE_ASSETS:
        data = {
            "asset_name": item["name"], "category_id": category_ids[item["category_code"]],
            "purchase_date": item["purchase_date"], "date_put_to_use": item["purchase_date"],
            "original_cost": item["cost"], "residual_value": item["residual"],
            "useful_life_years": item.get("life"), "companies_act_method": item["method"],
            "companies_act_rate": item.get("rate"),
            "income_tax_block_id": block_ids[item["block_code"]],
            "opening_accum_dep": 0,
        }
        created_assets.append(asset_service.create_asset(conn, data))
    return created_assets