from decimal import Decimal
from utils.formatting import to_decimal


def get_dashboard_summary(conn, financial_year=None, category_id=None):
    q = "SELECT a.*, c.category_name FROM assets a JOIN asset_categories c ON a.category_id=c.category_id"
    conditions, params = [], []
    if category_id:
        conditions.append("a.category_id=?")
        params.append(category_id)
    if conditions:
        q += " WHERE " + " AND ".join(conditions)
    assets = conn.execute(q, params).fetchall()

    total_assets = len(assets)
    total_cost = sum((to_decimal(a["original_cost"]) for a in assets), Decimal("0"))
    disposed = [a for a in assets if a["status"] == "DISPOSED"]
    active = [a for a in assets if a["status"] == "ACTIVE"]

    rec_q = """SELECT dr.* FROM depreciation_records dr JOIN depreciation_runs r ON dr.run_id=r.run_id
               WHERE r.status='POSTED'"""
    rec_params = []
    if financial_year:
        rec_q += " AND dr.financial_year=?"
        rec_params.append(financial_year)
    records = conn.execute(rec_q, rec_params).fetchall()
    total_ca_dep = sum((to_decimal(r["companies_act_depreciation"]) for r in records), Decimal("0"))

    block_q = """SELECT br.* FROM tax_block_records br JOIN depreciation_runs r ON br.run_id=r.run_id
                 WHERE r.status='POSTED'"""
    block_params = []
    if financial_year:
        block_q += " AND br.financial_year=?"
        block_params.append(financial_year)
    block_records = conn.execute(block_q, block_params).fetchall()

    total_it_dep = sum((to_decimal(b["depreciation"]) for b in block_records), Decimal("0"))
    total_dtl = sum((to_decimal(b["deferred_tax"]) for b in block_records
                     if b["deferred_tax_type"] == "Deferred Tax Liability"), Decimal("0"))
    total_dta = sum((to_decimal(b["deferred_tax"]) for b in block_records
                     if b["deferred_tax_type"] == "Deferred Tax Asset"), Decimal("0"))

    latest_carrying = {r["asset_id"]: to_decimal(r["closing_carrying_amount"]) for r in records}
    total_carrying_amount = sum(
        (latest_carrying.get(a["asset_id"], to_decimal(a["opening_wdv"])) for a in active), Decimal("0"))
    total_accum_dep = total_cost - total_carrying_amount

    disposals = conn.execute("SELECT * FROM disposal_records").fetchall()
    profit_on_sale = sum((to_decimal(d["profit_loss"]) for d in disposals
                          if d["profit_loss_type"] == "PROFIT ON SALE"), Decimal("0"))
    loss_on_sale = sum((to_decimal(d["profit_loss"]) for d in disposals
                        if d["profit_loss_type"] == "LOSS ON SALE"), Decimal("0"))

    return {
        "total_assets": total_assets, "total_cost": total_cost, "total_accum_dep": total_accum_dep,
        "total_carrying_amount": total_carrying_amount, "total_ca_dep": total_ca_dep,
        "total_it_dep": total_it_dep, "total_dtl": total_dtl, "total_dta": total_dta,
        "assets_disposed": len(disposed), "profit_on_sale": profit_on_sale, "loss_on_sale": loss_on_sale,
    }