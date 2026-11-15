"""In-memory tables (DuckDB). Same shapes and sign rules as the Node project's SQLite model.

Conventions: amounts are whole paise, debit positive (Dr +, Cr -); quantities are x10^4; dates are 'YYYY-MM-DD' text;
flags are 0/1. There are deliberately no foreign keys or unique constraints: DuckDB bulk-loads far faster without
them and the importer keeps names and ids unique itself.
"""
from __future__ import annotations

B, V, D = "BIGINT", "VARCHAR", "DOUBLE"

TABLES: dict[str, list[tuple[str, str]]] = {
    "companies": [("id", B), ("name", V), ("source_name", V), ("source_guid", V), ("is_demo", B),
                  ("fy_start_month", B), ("books_from", V), ("base_currency", V), ("industry_profile", V),
                  ("inventory_mode", V), ("settings_json", V), ("created_at", V)],
    "ledger_groups": [("id", B), ("company_id", B), ("name", V), ("parent_name", V), ("primary_group", V),
                      ("is_revenue", B), ("affects_gross_profit", B), ("is_deemed_positive", B), ("is_reserved", B),
                      ("guid", V), ("alter_id", B)],
    "ledgers": [("id", B), ("company_id", B), ("name", V), ("group_name", V), ("group_id", B), ("guid", V),
                ("master_id", B), ("alter_id", B), ("opening_paise", B), ("is_billwise", B),
                ("credit_period_days", B), ("credit_limit_paise", B), ("gstin", V), ("state", V), ("currency", V)],
    "source_balances": [("company_id", B), ("ledger_id", B), ("as_of", V), ("closing_paise", B), ("run_id", B)],
    "voucher_types": [("id", B), ("company_id", B), ("name", V), ("parent", V), ("base_type", V),
                      ("affects_accounts", B), ("affects_inventory", B), ("is_known", B)],
    "cost_centres": [("id", B), ("company_id", B), ("name", V), ("parent", V), ("category", V), ("guid", V)],
    "stock_groups": [("id", B), ("company_id", B), ("name", V), ("parent", V), ("guid", V)],
    "units": [("id", B), ("company_id", B), ("name", V), ("is_simple", B), ("base_unit", V), ("additional_unit", V),
              ("conversion", V), ("decimals", B)],
    "godowns": [("id", B), ("company_id", B), ("name", V), ("parent", V)],
    "stock_items": [("id", B), ("company_id", B), ("name", V), ("group_name", V), ("base_unit", V), ("guid", V),
                    ("master_id", B), ("alter_id", B), ("opening_qty_e4", B), ("opening_value_paise", B),
                    ("costing_method", V), ("hsn", V)],
    "stock_snapshots": [("company_id", B), ("stock_item_id", B), ("as_of", V), ("qty_e4", B), ("value_paise", B),
                        ("source", V), ("run_id", B)],
    "vouchers": [("id", B), ("company_id", B), ("source_key", V), ("guid", V), ("master_id", B), ("alter_id", B),
                 ("date", V), ("voucher_type", V), ("base_type", V), ("number", V), ("reference", V),
                 ("party_name", V), ("party_ledger_id", B), ("narration", V), ("is_cancelled", B),
                 ("is_optional", B), ("is_postdated", B), ("is_invoice", B), ("is_accounting", B),
                 ("is_inventory", B), ("line_total_paise", B), ("run_id", B)],
    "voucher_lines": [("id", B), ("voucher_id", B), ("company_id", B), ("line_no", B), ("ledger_id", B),
                      ("amount_paise", B)],
    "cost_allocations": [("id", B), ("voucher_id", B), ("company_id", B), ("ledger_id", B),
                         ("cost_centre_id", B), ("amount_paise", B)],
    "bill_allocations": [("id", B), ("company_id", B), ("voucher_id", B), ("ledger_id", B), ("bill_name", V),
                         ("bill_type", V), ("amount_paise", B), ("date", V), ("credit_days", B), ("due_date", V),
                         ("is_opening", B)],
    "inventory_lines": [("id", B), ("voucher_id", B), ("company_id", B), ("line_no", B), ("stock_item_id", B),
                        ("direction", V), ("qty_e4", B), ("billed_qty_e4", B), ("unit", V), ("value_paise", B),
                        ("godown", V), ("batch", V), ("mfg_date", V), ("expiry_date", V), ("ledger_id", B)],
    "ledger_closing_values": [("company_id", B), ("ledger_id", B), ("as_of", V), ("amount_paise", B)],
    "classifications": [("id", B), ("company_id", B), ("target_type", V), ("target_name", V), ("class_code", V),
                        ("attrs_json", V), ("status", V), ("confidence", D), ("rationale", V), ("updated_at", V)],
    "collection_notes": [("id", B), ("company_id", B), ("ledger_id", B), ("bill_name", V), ("status", V),
                         ("note", V), ("created_at", V)],
}

COLUMNS: dict[str, list[str]] = {t: [c for c, _ in cols] for t, cols in TABLES.items()}


def create_sql() -> list[str]:
    return [f"CREATE TABLE {t} ({', '.join(f'{c} {ty}' for c, ty in cols)})" for t, cols in TABLES.items()]
